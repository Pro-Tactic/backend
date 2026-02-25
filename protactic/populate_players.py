import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protactic.settings')
django.setup()

from backend.models import Clube, Jogador

def run():
    # 1. Ensure we have a club
    clube, created = Clube.objects.get_or_create(
        nome="Protactic FC",
        defaults={
            "pais": "Brasil",
            "data_criacao": "2024-01-01"
        }
    )
    if created:
        print(f"Clube '{clube.nome}' criado.")
    else:
        print(f"Usando clube existente: '{clube.nome}'")

    # 2. List of players to add
    names = [
        "Rodrigo", "Sukar", "Rose Paul", "Caminha", "Suado", 
        "Becker", "Gabi Campello", "Ned", "Anderson", "Tonho", 
        "Saulo", "Belliato", "Maju D", "Tomaz", "Sophia"
    ]

    positions = [
        'Goleiro', 'Zagueiro', 'Lateral Esquerdo', 'Lateral Direito', 
        'Volante', 'Meio-campista', 'Meia Atacante', 'Ponta Esquerda', 
        'Ponta Direita', 'Centroavante'
    ]
    
    legs = ['Destro', 'Canhoto', 'Ambidestro']

    print("Adicionando jogadores...")
    for name in names:
        # Check if exists to avoid duplicates (optional, based on name/cpf)
        # Generating a fake unique CPF based on hash of name for simplicity in this dev script
        fake_cpf = str(abs(hash(name)))[:11].ljust(11, '0')
        
        jogador, created = Jogador.objects.get_or_create(
            nome=name,
            defaults={
                "cpf": fake_cpf,
                "idade": random.randint(18, 35),
                "peso": random.randint(60, 90),
                "altura": round(random.uniform(1.65, 1.95), 2),
                "nacionalidade": "Brasil",
                "posicao": random.choice(positions),
                "perna": random.choice(legs),
                "clube": clube
            }
        )
        if created:
            print(f"+ {name} ({jogador.posicao})")
        else:
            print(f". {name} já existe")

if __name__ == '__main__':
    run()
