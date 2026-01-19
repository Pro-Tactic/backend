
import sqlite3
from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.apps import apps
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protactic.settings')
django.setup()

from backend.models import User, Jogador, Clube

try:
    # Set password for tecnico
    u = User.objects.get(username='tecnico')
    u.set_password('123')
    u.save()
    print(f"Password for {u.username} set to '123'")
    
    # Check players for club 1
    c = Clube.objects.get(id=1)
    players = Jogador.objects.filter(clube=c)
    print(f"Club {c.nome} (id=1) has {players.count()} players.")
    for p in players:
        print(f"- {p.nome}")

except Exception as e:
    print(f"Error: {e}")
