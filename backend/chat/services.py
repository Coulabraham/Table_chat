from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone

from accounts.models import User, UserBlock
from .models import Conversation, ConversationMembership, DeliveryOutbox, GroupInvitation, Message
from .serializers import MessageSerializer


class MessagingBlockedError(Exception):
    pass


class GroupActionError(Exception):
    pass


def conversation_group_name(conversation_id):
    return f"conversation_{conversation_id}"


def active_membership(conversation, user, *, for_update=False):
    queryset = ConversationMembership.objects.filter(
        conversation=conversation, user=user, left_at__isnull=True
    )
    if for_update:
        queryset = queryset.select_for_update()
    return queryset.first()


def current_message_bound(conversation):
    return conversation.messages.aggregate(last=Max("id"))["last"] or 0


def notify_conversation_event(conversation_id, event_type, **payload):
    async_to_sync(get_channel_layer().group_send)(
        conversation_group_name(conversation_id),
        {"type": "conversation.event", "event_type": event_type, "payload": payload},
    )


def get_or_create_private_conversation(user, contact):
    low, high = sorted((user, contact), key=lambda item: item.pk)
    try:
        with transaction.atomic():
            conversation, _ = Conversation.objects.get_or_create(
                kind=Conversation.Kind.PRIVATE, user_low=low, user_high=high
            )
            for participant in (low, high):
                ConversationMembership.objects.get_or_create(
                    conversation=conversation,
                    user=participant,
                    left_at__isnull=True,
                    defaults={"role": ConversationMembership.Role.MEMBER},
                )
            return conversation
    except IntegrityError:
        return Conversation.objects.get(kind=Conversation.Kind.PRIVATE, user_low=low, user_high=high)


@transaction.atomic
def create_group(owner, *, name, description=""):
    conversation = Conversation.objects.create(
        kind=Conversation.Kind.GROUP,
        name=name.strip(),
        description=description.strip(),
        owner=owner,
    )
    ConversationMembership.objects.create(
        conversation=conversation,
        user=owner,
        role=ConversationMembership.Role.OWNER,
        joined_after_message_id=0,
    )
    return conversation


@transaction.atomic
def create_group_invitation(conversation, inviter, invitee):
    conversation = Conversation.objects.select_for_update().get(pk=conversation.pk)
    membership = active_membership(conversation, inviter, for_update=True)
    if conversation.kind != Conversation.Kind.GROUP or not membership or membership.role not in (
        ConversationMembership.Role.OWNER,
        ConversationMembership.Role.ADMIN,
    ):
        raise GroupActionError("Vous n’avez pas le droit d’inviter dans ce groupe.")
    if invitee.pk == inviter.pk or active_membership(conversation, invitee):
        raise GroupActionError("Cette personne fait déjà partie du groupe.")
    if UserBlock.objects.filter(
        Q(blocker=inviter, blocked=invitee) | Q(blocker=invitee, blocked=inviter)
    ).exists():
        # Le texte ne révèle pas qui a bloqué qui.
        raise GroupActionError("Cette invitation ne peut pas être envoyée.")
    if conversation.memberships.filter(left_at__isnull=True).count() >= settings.GROUP_MAX_MEMBERS:
        raise GroupActionError("Le groupe a atteint sa limite de membres.")
    now = timezone.now()
    conversation.invitations.filter(
        invitee=invitee, status=GroupInvitation.Status.PENDING, expires_at__lte=now
    ).update(status=GroupInvitation.Status.EXPIRED, responded_at=now)
    invitation, created = GroupInvitation.objects.get_or_create(
        conversation=conversation,
        invitee=invitee,
        status=GroupInvitation.Status.PENDING,
        defaults={
            "inviter": inviter,
            "expires_at": now + timezone.timedelta(seconds=settings.GROUP_INVITATION_TTL_SECONDS),
        },
    )
    if not created:
        raise GroupActionError("Une invitation est déjà en attente pour cette personne.")
    return invitation


@transaction.atomic
def respond_to_invitation(invitation_id, invitee, *, accept):
    invitation = GroupInvitation.objects.select_for_update().select_related("conversation", "inviter").get(
        pk=invitation_id, invitee=invitee
    )
    now = timezone.now()
    if invitation.status != GroupInvitation.Status.PENDING:
        raise GroupActionError("Cette invitation n’est plus disponible.")
    if invitation.expires_at <= now:
        invitation.status = GroupInvitation.Status.EXPIRED
        invitation.responded_at = now
        invitation.save(update_fields=("status", "responded_at"))
        return invitation, None
    conversation = Conversation.objects.select_for_update().get(pk=invitation.conversation_id)
    inviter_membership = active_membership(conversation, invitation.inviter, for_update=True)
    if not inviter_membership or inviter_membership.role not in (
        ConversationMembership.Role.OWNER,
        ConversationMembership.Role.ADMIN,
    ):
        raise GroupActionError("Cette invitation n’est plus disponible.")
    if not accept:
        invitation.status = GroupInvitation.Status.DECLINED
        invitation.responded_at = now
        invitation.save(update_fields=("status", "responded_at"))
        return invitation, None
    if UserBlock.objects.filter(
        Q(blocker=invitation.inviter, blocked=invitee) | Q(blocker=invitee, blocked=invitation.inviter)
    ).exists():
        raise GroupActionError("Cette invitation ne peut pas être acceptée.")
    if active_membership(conversation, invitee, for_update=True):
        raise GroupActionError("Vous faites déjà partie de ce groupe.")
    if conversation.memberships.filter(left_at__isnull=True).count() >= settings.GROUP_MAX_MEMBERS:
        raise GroupActionError("Le groupe a atteint sa limite de membres.")
    membership = ConversationMembership.objects.create(
        conversation=conversation,
        user=invitee,
        role=ConversationMembership.Role.MEMBER,
        joined_after_message_id=current_message_bound(conversation),
    )
    invitation.status = GroupInvitation.Status.ACCEPTED
    invitation.responded_at = now
    invitation.save(update_fields=("status", "responded_at"))
    transaction.on_commit(
        lambda: notify_conversation_event(
            conversation.pk,
            "member.joined",
            user_id=invitee.pk,
            public_id=invitee.public_id,
            display_name=invitee.display_name,
            role=membership.role,
        )
    )
    return invitation, membership


@transaction.atomic
def cancel_invitation(invitation_id, actor):
    invitation = GroupInvitation.objects.select_for_update().select_related("conversation").get(pk=invitation_id)
    membership = active_membership(invitation.conversation, actor, for_update=True)
    if not membership or membership.role not in (
        ConversationMembership.Role.OWNER,
        ConversationMembership.Role.ADMIN,
    ):
        raise GroupActionError("Vous n’avez pas le droit d’annuler cette invitation.")
    if invitation.status != GroupInvitation.Status.PENDING:
        raise GroupActionError("Cette invitation n’est plus en attente.")
    invitation.status = GroupInvitation.Status.CANCELLED
    invitation.responded_at = timezone.now()
    invitation.save(update_fields=("status", "responded_at"))
    return invitation


def _lock_group_and_actor(conversation_id, actor):
    conversation = Conversation.objects.select_for_update().get(pk=conversation_id, kind=Conversation.Kind.GROUP)
    membership = active_membership(conversation, actor, for_update=True)
    if not membership:
        raise GroupActionError("Vous n’avez plus accès à ce groupe.")
    return conversation, membership


@transaction.atomic
def update_group(conversation_id, actor, **changes):
    conversation, membership = _lock_group_and_actor(conversation_id, actor)
    if membership.role not in (ConversationMembership.Role.OWNER, ConversationMembership.Role.ADMIN):
        raise GroupActionError("Vous n’avez pas le droit de modifier ce groupe.")
    changed = []
    for field in ("name", "description"):
        if field in changes:
            setattr(conversation, field, changes[field].strip())
            changed.append(field)
    if changed:
        conversation.save(update_fields=changed)
        event_payload = {field: getattr(conversation, field) for field in changed}
        transaction.on_commit(
            lambda: notify_conversation_event(conversation.pk, "group.updated", **event_payload)
        )
    return conversation


@transaction.atomic
def change_member_role(conversation_id, actor, target_user_id, role):
    conversation, actor_membership = _lock_group_and_actor(conversation_id, actor)
    if actor_membership.role != ConversationMembership.Role.OWNER:
        raise GroupActionError("Seul le propriétaire peut modifier les rôles.")
    target = ConversationMembership.objects.select_for_update().select_related("user").filter(
        conversation=conversation, user_id=target_user_id, left_at__isnull=True
    ).first()
    if not target or target.role == ConversationMembership.Role.OWNER:
        raise GroupActionError("Ce rôle ne peut pas être modifié.")
    target.role = role
    target.save(update_fields=("role", "updated_at"))
    transaction.on_commit(
        lambda: notify_conversation_event(
            conversation.pk, "member.role_changed", user_id=target.user_id, role=target.role
        )
    )
    return target


@transaction.atomic
def remove_group_member(conversation_id, actor, target_user_id):
    conversation, actor_membership = _lock_group_and_actor(conversation_id, actor)
    target = ConversationMembership.objects.select_for_update().select_related("user").filter(
        conversation=conversation, user_id=target_user_id, left_at__isnull=True
    ).first()
    if not target or target.role == ConversationMembership.Role.OWNER:
        raise GroupActionError("Cette personne ne peut pas être retirée.")
    if actor_membership.role == ConversationMembership.Role.ADMIN and target.role != ConversationMembership.Role.MEMBER:
        raise GroupActionError("Un administrateur ne peut retirer que des membres.")
    if actor_membership.role not in (ConversationMembership.Role.OWNER, ConversationMembership.Role.ADMIN):
        raise GroupActionError("Vous n’avez pas le droit de retirer un membre.")
    now = timezone.now()
    target.left_at = now
    target.left_after_message_id = current_message_bound(conversation)
    target.save(update_fields=("left_at", "left_after_message_id", "updated_at"))
    event_payload = {
        "user_id": target.user_id,
        "public_id": target.user.public_id,
        "display_name": target.user.display_name,
    }
    # L'événement est envoyé au groupe encore rejoint par le socket retiré.
    transaction.on_commit(
        lambda: (
            notify_conversation_event(conversation.pk, "member.removed", **event_payload),
            async_to_sync(get_channel_layer().group_send)(
                conversation_group_name(conversation.pk), {"type": "access.changed"}
            ),
        )
    )
    return target


@transaction.atomic
def transfer_group_ownership(conversation_id, actor, target_user_id):
    conversation, owner_membership = _lock_group_and_actor(conversation_id, actor)
    if owner_membership.role != ConversationMembership.Role.OWNER:
        raise GroupActionError("Seul le propriétaire peut transférer le groupe.")
    target = ConversationMembership.objects.select_for_update().select_related("user").filter(
        conversation=conversation, user_id=target_user_id, left_at__isnull=True
    ).first()
    if not target or target.pk == owner_membership.pk:
        raise GroupActionError("Choisissez un autre membre actif.")
    # Déclasser d'abord respecte l'unicité du propriétaire actif.
    owner_membership.role = ConversationMembership.Role.ADMIN
    owner_membership.save(update_fields=("role", "updated_at"))
    target.role = ConversationMembership.Role.OWNER
    target.save(update_fields=("role", "updated_at"))
    conversation.owner = target.user
    conversation.save(update_fields=("owner",))
    transaction.on_commit(
        lambda: notify_conversation_event(
            conversation.pk, "ownership.transferred", user_id=target.user_id, role=target.role
        )
    )
    return conversation


@transaction.atomic
def leave_group(conversation_id, actor, *, confirm_archive=False):
    conversation, membership = _lock_group_and_actor(conversation_id, actor)
    if membership.role == ConversationMembership.Role.OWNER:
        other_count = conversation.memberships.filter(left_at__isnull=True).exclude(pk=membership.pk).count()
        if other_count:
            raise GroupActionError("Transférez d’abord la propriété du groupe.")
        if not confirm_archive:
            raise GroupActionError("Confirmez l’archivage du groupe vide.")
        conversation.archived_at = timezone.now()
        conversation.save(update_fields=("archived_at",))
    membership.left_at = timezone.now()
    membership.left_after_message_id = current_message_bound(conversation)
    membership.save(update_fields=("left_at", "left_after_message_id", "updated_at"))
    payload = {"user_id": actor.pk, "public_id": actor.public_id, "display_name": actor.display_name}
    transaction.on_commit(
        lambda: (
            notify_conversation_event(conversation.pk, "member.left", **payload),
            async_to_sync(get_channel_layer().group_send)(
                conversation_group_name(conversation.pk), {"type": "access.changed"}
            ),
        )
    )
    return conversation


@transaction.atomic
def advance_read_cursor(conversation_id, user, message_id):
    conversation = Conversation.objects.select_for_update().get(pk=conversation_id)
    membership = active_membership(conversation, user, for_update=True)
    if not membership:
        raise GroupActionError("Conversation inaccessible.")
    message = Message.objects.filter(pk=message_id, conversation=conversation).first()
    if not message or message.id <= membership.joined_after_message_id:
        raise GroupActionError("Curseur de lecture invalide.")
    if message.id > (membership.last_read_message_id or 0):
        membership.last_read_message = message
        membership.save(update_fields=("last_read_message", "updated_at"))
        transaction.on_commit(
            lambda: notify_conversation_event(
                conversation.pk, "read.updated", user_id=user.pk, message_id=message.id
            )
        )
    return membership


def publish_message(message_id):
    message = Message.objects.select_related("conversation").get(pk=message_id)
    payload = MessageSerializer(message).data
    # DRF's HTTP renderer knows how to encode UUID values, while Channels'
    # JSON consumer deliberately uses the standard encoder.
    payload["conversation_id"] = str(message.conversation_id)
    outbox, _ = DeliveryOutbox.objects.get_or_create(message=message)
    try:
        async_to_sync(get_channel_layer().group_send)(
            conversation_group_name(message.conversation_id),
            {"type": "chat.message", "message": payload},
        )
    except Exception as exc:
        outbox.attempts += 1
        outbox.last_error = type(exc).__name__[:200]
        outbox.next_attempt_at = timezone.now() + timezone.timedelta(seconds=min(300, 2 ** min(outbox.attempts, 8)))
        outbox.save(update_fields=("attempts", "last_error", "next_attempt_at"))
        return False
    outbox.attempts += 1
    outbox.delivered_at = timezone.now()
    outbox.last_error = ""
    outbox.save(update_fields=("attempts", "delivered_at", "last_error"))
    return True


def publish_pending_events(*, conversation_id=None, limit=100):
    pending = DeliveryOutbox.objects.filter(
        delivered_at__isnull=True,
        next_attempt_at__lte=timezone.now(),
    )
    if conversation_id is not None:
        pending = pending.filter(message__conversation_id=conversation_id)
    message_ids = list(pending.order_by("message_id").values_list("message_id", flat=True)[:limit])
    delivered = 0
    for message_id in message_ids:
        delivered += int(publish_message(message_id))
    return {"attempted": len(message_ids), "delivered": delivered}


def create_message(conversation, author, *, client_id, content):
    with transaction.atomic():
        conversation = Conversation.objects.select_for_update().get(pk=conversation.pk)
        if not active_membership(conversation, author, for_update=True):
            raise GroupActionError("Vous n’avez plus accès à cette conversation.")
        if conversation.kind == Conversation.Kind.PRIVATE:
            participant_ids = sorted((conversation.user_low_id, conversation.user_high_id))
            list(User.objects.select_for_update().filter(pk__in=participant_ids).order_by("pk"))
            if UserBlock.objects.filter(
                Q(blocker_id=participant_ids[0], blocked_id=participant_ids[1])
                | Q(blocker_id=participant_ids[1], blocked_id=participant_ids[0])
            ).exists():
                raise MessagingBlockedError
        existing = Message.objects.filter(author=author, client_id=client_id).first()
        if existing is not None:
            if existing.conversation_id != conversation.pk:
                raise IntegrityError("client_id already used in another conversation")
            return existing, False
        try:
            # The inner savepoint lets a simultaneous unique-key conflict roll
            # back cleanly before the winning row is read below.
            with transaction.atomic():
                message = Message.objects.create(
                    conversation=conversation,
                    author=author,
                    client_id=client_id,
                    content=content,
                )
        except IntegrityError:
            message = Message.objects.get(author=author, client_id=client_id)
            if message.conversation_id != conversation.pk:
                raise
            return message, False
        Conversation.objects.filter(pk=conversation.pk).update(updated_at=message.created_at)
        DeliveryOutbox.objects.create(message=message)
        # La tentative immédiate conserve le temps réel. En cas de coupure Redis,
        # le prochain envoi ou la prochaine connexion rejoue aussi les événements
        # précédents, ce qui évite de dépendre d'un worker permanent sur Vercel.
        transaction.on_commit(lambda: publish_pending_events(conversation_id=conversation.pk))
    return message, True
