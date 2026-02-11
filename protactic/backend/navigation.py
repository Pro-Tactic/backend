BASE_ITEMS = [
    {"key": "inicio", "label": "Início", "path": "/inicio", "icon": "home"},
    {"key": "elenco", "label": "Central do Elenco", "path": "/elenco", "icon": "users"},
    {"key": "adversario", "label": "Adversário", "path": "/adversario", "icon": "target"},
    {"key": "tempo_real", "label": "Tempo Real", "path": "/tempo-real", "icon": "activity"},
    {"key": "competicoes", "label": "Competições", "path": "/competicoes", "icon": "trophy"},
    {"key": "clube", "label": "Clube", "path": "/clube", "icon": "building"},
]

SUPERUSER_ONLY = [
    {"key": "registro", "label": "Registro", "path": "/registro", "icon": "shield"},
]


COACH_ITEMS = [
    {"key": "listar_jogadores", "label": "Listar Jogadores", "path": "/listar-jogadores", "icon": "users"},
    {"key": "notas", "label": "Avaliação", "path": "/notas", "icon": "notas"},
]

def build_navigation_for_user(user):
    if user.is_superuser:
        return list(SUPERUSER_ONLY)

    items = list(BASE_ITEMS)

    if user.user_type == 'TREINADOR':
        items.extend(COACH_ITEMS)

    return items