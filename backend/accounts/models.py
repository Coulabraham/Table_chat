import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.sessions.models import Session
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, public_id, display_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Une adresse email est requise.")
        user = self.model(
            email=self.normalize_email(email).lower(),
            public_id=public_id.lower(),
            display_name=display_name,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, public_id, display_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, public_id, display_name, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    public_id = models.CharField(max_length=32, unique=True, db_index=True)
    display_name = models.CharField(max_length=80)
    bio = models.CharField(max_length=160, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["public_id", "display_name"]
    objects = UserManager()

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email).lower()
        self.public_id = self.public_id.lower()
        email_changed = False
        if self.pk:
            previous_email = self.__class__.objects.filter(pk=self.pk).values_list("email", flat=True).first()
            email_changed = previous_email is not None and previous_email != self.email
            if email_changed:
                self.email_verified_at = None
        super().save(*args, **kwargs)
        if email_changed:
            self.account_tokens.filter(kind=AccountToken.Kind.EMAIL_VERIFICATION, used_at__isnull=True).update(used_at=models.functions.Now())

    @property
    def email_verified(self):
        return self.email_verified_at is not None


class AccountToken(models.Model):
    class Kind(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Vérification email"
        PASSWORD_RESET = "password_reset", "Réinitialisation du mot de passe"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="account_tokens")
    kind = models.CharField(max_length=32, choices=Kind.choices)
    token_hash = models.CharField(max_length=64)
    email_snapshot = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=("user", "kind", "used_at"), name="acct_token_lookup_idx")]


class AccountSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name="account_record")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="account_sessions")
    description = models.CharField(max_length=120)
    user_agent = models.CharField(max_length=512, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-last_activity_at",)


class UserBlock(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocks_created")
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocks_received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("blocker", "blocked"), name="unique_user_block"),
            models.CheckConstraint(condition=~models.Q(blocker=models.F("blocked")), name="cannot_block_self"),
        ]
        ordering = ("-created_at",)
