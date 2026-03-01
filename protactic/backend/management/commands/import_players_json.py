import json
import re
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from backend.models import Clube, Jogador


POSITION_MAP = {
    'Goalkeeper': 'Goleiro',
    'Defender': 'Zagueiro',
    'Midfielder': 'Meio-campista',
    'Attacker': 'Centroavante',
}


def extract_int(value):
    if value is None:
        return None
    digits = re.sub(r'[^0-9]', '', str(value))
    return int(digits) if digits else None


def extract_decimal(value):
    if value is None:
        return None
    cleaned = re.sub(r'[^0-9.,-]', '', str(value)).replace(',', '.')
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def format_cpf_from_external_id(external_id):
    base = f"{int(external_id):011d}"[-11:]
    return f"{base[:3]}.{base[3:6]}.{base[6:9]}-{base[9:]}"


def parse_birth_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def best_position_from_statistics(statistics):
    if not statistics:
        return 'Meio-campista'

    def score(item):
        games = item.get('games') or {}
        minutes = games.get('minutes')
        appearances = games.get('appearences')
        return (minutes or 0, appearances or 0)

    best = max(statistics, key=score)
    raw_position = (best.get('games') or {}).get('position')
    return POSITION_MAP.get(raw_position, 'Meio-campista')


class Command(BaseCommand):
    help = 'Importa jogadores a partir de um JSON no formato da API-Football (players).'

    def add_arguments(self, parser):
        parser.add_argument('--json-path', required=True, help='Caminho do arquivo JSON')
        parser.add_argument('--clube-id', required=False, help='ID interno do clube (id_clube no sistema)')
        parser.add_argument('--clube-nome', required=False, help='Nome do clube no sistema (fallback)')
        parser.add_argument('--dry-run', action='store_true', help='Mostra o que faria sem gravar no banco')

    def handle(self, *args, **options):
        json_path = Path(options['json_path'])
        clube_id = options.get('clube_id')
        clube_nome = options.get('clube_nome')
        dry_run = options.get('dry_run', False)

        if not json_path.exists():
            raise CommandError(f'Arquivo não encontrado: {json_path}')

        if not clube_id and not clube_nome:
            raise CommandError('Informe --clube-id ou --clube-nome para vincular os jogadores.')

        if clube_id:
            try:
                clube = Clube.objects.get(pk=clube_id)
            except Clube.DoesNotExist as exc:
                raise CommandError(f'Clube não encontrado para --clube-id={clube_id}') from exc
        else:
            try:
                clube = Clube.objects.get(nome__iexact=clube_nome)
            except Clube.DoesNotExist as exc:
                raise CommandError(f'Clube não encontrado para --clube-nome="{clube_nome}"') from exc

        with json_path.open('r', encoding='utf-8') as file:
            payload = json.load(file)

        players = payload.get('response') or []
        if not players:
            self.stdout.write(self.style.WARNING('Nenhum jogador encontrado no JSON (response vazio).'))
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for item in players:
            player_info = item.get('player') or {}
            if not player_info:
                skipped_count += 1
                continue

            external_id = player_info.get('id')
            name = (player_info.get('name') or '').strip()
            if not external_id or not name:
                skipped_count += 1
                continue

            cpf = format_cpf_from_external_id(external_id)
            birth_date = parse_birth_date((player_info.get('birth') or {}).get('date'))
            position = best_position_from_statistics(item.get('statistics') or [])

            defaults = {
                'nome': name,
                'data_nascimento': birth_date,
                'peso': extract_decimal(player_info.get('weight')),
                'altura': extract_int(player_info.get('height')),
                'nacionalidade': player_info.get('nationality') or 'Não informado',
                'posicao': position,
                'perna': 'Destro',
                'foto': player_info.get('photo') or None,
                'clube': clube,
            }

            if dry_run:
                self.stdout.write(f'[DRY-RUN] {name} | CPF {cpf} | {position}')
                continue

            jogador, created = Jogador.objects.update_or_create(
                cpf=cpf,
                defaults=defaults,
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'+ Criado: {jogador.nome}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'~ Atualizado: {jogador.nome}'))

        if dry_run:
            self.stdout.write(self.style.SUCCESS('Dry-run concluído. Nenhuma alteração foi gravada.'))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'Importação concluída | criados={created_count} atualizados={updated_count} ignorados={skipped_count}'
            )
        )
