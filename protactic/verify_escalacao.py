import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protactic.settings')
django.setup()

from backend.models import Clube, Jogador, Competicao, Partida, Escalacao
from django.utils import timezone
from django.contrib.auth import get_user_model

def run():
    print("Setting up test data...")
    # Create Clubes
    clube1, _ = Clube.objects.get_or_create(nome="Clube A", pais="Brasil", ano_fundacao=1900)
    clube2, _ = Clube.objects.get_or_create(nome="Clube B", pais="Brasil", ano_fundacao=1910)

    # Create Players
    player1, _ = Jogador.objects.get_or_create(
        nome="Player 1", cpf="11111111111", idade=20, peso=70, altura=1.75,
        nacionalidade="BR", posicao="Atacante", perna="Direita",
        clube=clube1
    )

    # Create Match
    competicao, _ = Competicao.objects.get_or_create(nome="Liga Teste", tamanho="Pequeno", tipo_participantes="Clubes", divisao="1", tipo_formato="Liga", qtd_participantes=10)
    
    partida, _ = Partida.objects.get_or_create(
        competicao=competicao,
        mandante=clube1,
        visitante=clube2,
        data_hora=timezone.now()
    )

    print("Creating Escalacao entry...")
    # Create Lineup
    try:
        escalacao = Escalacao.objects.create(
            partida=partida,
            clube=clube1,
            jogador=player1,
            status='TITULAR'
        )
        print(f"Success: {escalacao}")
    except Exception as e:
        print(f"Error creating escalacao: {e}")

    # Test constraint (Uniqueness)
    print("Testing uniqueness constraint...")
    try:
        Escalacao.objects.create(
            partida=partida,
            clube=clube1,
            jogador=player1,
            status='RESERVA'
        )
        print("Error: Constraint check failed (Should have raised error)")
    except Exception as e:
        print(f"Success: Caught expected error: {e}")

if __name__ == '__main__':
    run()
