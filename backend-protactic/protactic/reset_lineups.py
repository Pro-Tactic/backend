import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protactic.settings')
django.setup()

from backend.models import Escalacao

def run():
    count = Escalacao.objects.count()
    Escalacao.objects.all().delete()
    print(f"Deleted {count} escalacao entries. All players are now 'Não Relacionados'.")

if __name__ == '__main__':
    run()
