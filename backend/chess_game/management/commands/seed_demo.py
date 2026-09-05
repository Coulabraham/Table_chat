from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from chat.models import Conversation, ConversationParticipant, Message
from friends.models import Friendship
from chess_game.models import Lesson


LESSONS = [
    {"title": "Le mat en un coup", "instruction": "Trouvez le coup décisif.", "initial_fen": "7k/8/5KQ1/8/8/8/8/8 w - - 0 1", "side_to_move": "white", "objective": "Mat en 1", "difficulty": "Débutant", "accepted_lines": [["g6g7"]], "hint": "La dame doit retirer toutes les cases de fuite au roi noir.", "hints": ["Commencez par chercher tous les échecs possibles.", "Votre dame peut se rapprocher tout en restant protégée par le roi.", "Placez la dame en g7."], "coach_messages": {"intro": "Prenez votre temps. Avant de jouer, repérez les cases de fuite du roi noir.", "retry": "Ce coup ne mate pas encore. Vérifiez si le roi noir conserve une case de fuite.", "complete": "Excellent ! Dg7# est protégé par votre roi et ferme toutes les sorties."}, "explanation": "Dg7# protège la dame avec le roi et ferme les dernières cases de fuite.", "order": 1},
    {"title": "Le baiser de la dame", "instruction": "Matez avec la dame protégée.", "initial_fen": "6k1/8/6K1/8/8/8/3Q4/8 w - - 0 1", "side_to_move": "white", "objective": "Mat en 1", "difficulty": "Débutant", "accepted_lines": [["d2d8"]], "hint": "Cherchez un échec sur la huitième rangée.", "hints": ["Quels échecs la dame peut-elle donner ?", "Le roi blanc contrôle déjà f7 et h7.", "Jouez la dame en d8."], "coach_messages": {"intro": "Le roi blanc est très bien placé. Utilisez cette proximité pour soutenir la dame.", "retry": "La dame donne peut-être échec, mais le roi dispose encore d’une réponse.", "complete": "Parfait. Dd8# utilise le roi blanc pour verrouiller les cases de fuite."}, "explanation": "Dd8# coupe la rangée et le roi blanc contrôle les cases de fuite.", "order": 2},
    {"title": "Protéger son roi", "instruction": "Écartez la menace immédiate.", "initial_fen": "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1", "side_to_move": "white", "objective": "Capturer la pièce menaçante", "difficulty": "Débutant", "accepted_lines": [["e1e2"]], "hint": "La tour n’est pas protégée.", "hints": ["Votre roi est en échec : il faut répondre à la menace.", "Regardez si la pièce qui donne échec est défendue.", "Le roi peut capturer la tour en e2."], "coach_messages": {"intro": "Quand votre roi est attaqué, cherchez dans l’ordre : capturer, bloquer ou fuir.", "retry": "Cette réponse ne met pas encore votre roi en sécurité.", "complete": "Bien vu. Rxe2 élimine la menace, car la tour n’était pas protégée."}, "explanation": "Rxe2 élimine la tour en restant sur une case sûre.", "order": 3},
    {"title": "Fourchette royale", "instruction": "Gagnez la dame avec une fourchette.", "initial_fen": "8/3q1k2/8/8/8/5N2/8/4K3 w - - 0 1", "side_to_move": "white", "objective": "Créer puis exploiter une fourchette", "difficulty": "Intermédiaire", "accepted_lines": [["f3e5", "f7e6", "e5d7"]], "hint": "Le cavalier peut donner échec tout en attaquant d7.", "hints": ["Cherchez un échec de cavalier.", "Depuis e5, le cavalier attaquerait deux pièces importantes.", "Jouez Ce5+, puis capturez la dame après la réponse du roi."], "coach_messages": {"intro": "Une fourchette est plus forte lorsque l’une des deux menaces est un échec.", "success": "Exactement : le roi doit répondre. Je le déplace en e6 ; quelle pièce pouvez-vous gagner maintenant ?", "retry": "Ce coup ne crée pas la double attaque recherchée. Cherchez un échec avec le cavalier.", "complete": "Très bien. Après Ce5+ et …Re6, Cxd7 gagne la dame : vous avez exploité la fourchette jusqu’au bout."}, "explanation": "Ce5+ attaque simultanément le roi et la dame ; après le déplacement du roi, Cxd7 gagne la dame.", "order": 4},
    {"title": "Promotion", "instruction": "Transformez le pion pour gagner.", "initial_fen": "7k/P7/6K1/8/8/8/8/8 w - - 0 1", "side_to_move": "white", "objective": "Promouvoir avec échec", "difficulty": "Intermédiaire", "accepted_lines": [["a7a8q"]], "hint": "Choisissez une dame à la promotion.", "hints": ["Le pion n’est plus qu’à une case de la promotion.", "La nouvelle pièce peut immédiatement donner échec.", "Avancez en a8 et choisissez une dame."], "coach_messages": {"intro": "Une promotion est encore plus forte lorsqu’elle gagne un tempo.", "retry": "Vous pouvez obtenir une pièce plus puissante tout en attaquant le roi.", "complete": "Bravo. a8=D+ crée une dame et oblige immédiatement le roi à répondre."}, "explanation": "a8=D+ obtient immédiatement une dame avec tempo.", "order": 5},
]

AWALE_LESSONS = [
    {"title": "Semer les graines", "instruction": "Distribuez les quatre graines du premier trou.", "objective": "Comprendre le sens du semis", "difficulty": "Débutant", "order": 1, "content": {"pits": [4,4,4,4,4,4,4,4,4,4,4,4], "legal": [0], "answer": 0}},
    {"title": "Capturer", "instruction": "Terminez sur un trou adverse contenant deux ou trois graines.", "objective": "Réaliser une capture", "difficulty": "Débutant", "order": 2, "content": {"pits": [0,0,0,0,0,1,1,4,4,4,4,4], "legal": [5], "answer": 5}},
    {"title": "Nourrir l’adversaire", "instruction": "Le camp adverse est vide : rendez-lui au moins une graine.", "objective": "Respecter l’obligation de nourrir", "difficulty": "Débutant", "order": 3, "content": {"pits": [0,0,0,0,1,11,0,0,0,0,0,0], "legal": [5], "answer": 5}},
    {"title": "Capture annulée", "instruction": "Anticipez une capture qui viderait le camp adverse.", "objective": "Éviter la famine", "difficulty": "Intermédiaire", "order": 4, "content": {"pits": [9,9,9,9,9,1,1,0,0,0,0,0], "legal": [5], "answer": 5}},
]


class Command(BaseCommand):
    help = "Crée deux comptes, une amitié, une conversation et cinq leçons de démonstration."

    @transaction.atomic
    def handle(self, *args, **options):
        alice, created = User.objects.get_or_create(email="alice@tablechat.local", defaults={"display_name": "Alice", "chess_level": "beginner"})
        if created:
            alice.set_password("TableChat123!")
            alice.save()
        camille, created = User.objects.get_or_create(email="camille@tablechat.local", defaults={"display_name": "Camille", "chess_level": "intermediate"})
        if created:
            camille.set_password("TableChat123!")
            camille.save()
        Friendship.objects.get_or_create(requester=alice, addressee=camille, defaults={"status": Friendship.Status.ACCEPTED})
        conversation = Conversation.objects.filter(kind=Conversation.Kind.PRIVATE, memberships__user=alice).filter(memberships__user=camille).first()
        if not conversation:
            conversation = Conversation.objects.create(kind=Conversation.Kind.PRIVATE)
            ConversationParticipant.objects.bulk_create([ConversationParticipant(conversation=conversation, user=alice), ConversationParticipant(conversation=conversation, user=camille)])
            Message.objects.create(conversation=conversation, author=camille, client_id="00000000-0000-0000-0000-000000000001", content="On fait une partie ?")
        for data in LESSONS:
            Lesson.objects.update_or_create(game_type="chess", order=data["order"], defaults=data)
        for data in AWALE_LESSONS:
            Lesson.objects.update_or_create(
                game_type="awale",
                order=data["order"],
                defaults={**data, "initial_fen": "", "side_to_move": "white", "accepted_lines": [], "hint": "", "hints": [], "coach_messages": {}, "explanation": data["objective"]},
            )
        self.stdout.write(self.style.SUCCESS("Données de démonstration prêtes (mot de passe : TableChat123!)."))
