
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protactic.settings')
django.setup()

from backend.models import User, Jogador, Clube

def run():
    try:
        tecnico = User.objects.get(username='tecnico')
        print(f"User 'tecnico' found. Type: {tecnico.user_type}")
        
        if not tecnico.clube:
            print("User 'tecnico' has no club assigned! Creating or assigning one.")
            # If no club, maybe assign to Protactic FC?
            # But user said they see "caio lima", so they MIGHT have a club.
            # Let's check who 'caio lima' belongs to.
            caio = Jogador.objects.filter(nome__icontains='caio lima').first()
            if caio:
                print(f"Found 'caio lima' in club: {caio.clube.nome}")
                target_club = caio.clube
                tecnico.clube = target_club
                tecnico.save()
                print(f"Assigned 'tecnico' to club: {target_club.nome}")
            else:
                # Fallback to Protactic FC
                target_club = Clube.objects.get(nome="Protactic FC")
                tecnico.clube = target_club
                tecnico.save()
                print(f"Assigned 'tecnico' to 'Protactic FC'")
        else:
            target_club = tecnico.clube
            print(f"User 'tecnico' is in club: {target_club.nome}")

        # Now update the players requested
        player_names = [
            "Rodrigo", "Sukar", "Rose Paul", "Caminha", "Suado", "Becker",
            "Gabi Campello", "Ned", "Anderson", "Tonho", "Saulo", "Belliato",
            "Maju D", "Tomaz", "Sophia", "Breno", "Gheyson E", "Cahu"
        ]
        
        updated_count = 0
        for name in player_names:
            players = Jogador.objects.filter(nome=name)
            for p in players:
                p.clube = target_club
                p.save()
                updated_count += 1
        
        print(f"Updated {updated_count} players to belong to {target_club.nome}")

    except User.DoesNotExist:
        print("User 'tecnico' does not exist! Please create it.")
        # Create user tecnico if missing (user implies it exists, but safe to handle)
        pass

if __name__ == '__main__':
    run()
