BASE_ITEMS = [
    {"key": "inicio", "label": "Início", "path": "/inicio", "icon": "home"},
    {"key": "elenco", "label": "Central do Elenco", "path": "/elenco", "icon": "users"},
    {"key": "adversario", "label": "Adversário", "path": "/adversario", "icon": "target"},
    {"key": "tempo_real", "label": "Tempo Real", "path": "/tempo-real", "icon": "activity"},
    {"key": "clube", "label": "Clube", "path": "/clube", "icon": "building"},
]

SUPERUSER_ONLY = [
    {"key": "registro", "label": "Registro", "path": "/registro", "icon": "shield"},
]


COACH_ITEMS = [
    {"key": "listar_jogadores", "label": "Listar Jogadores", "path": "/listar-jogadores", "icon": "users"},
]

def build_navigation_for_user(user):
    items = list(BASE_ITEMS)

    if user.is_superuser:
        items.extend(SUPERUSER_ONLY)
    
    if user.user_type == 'TREINADOR':
        items.extend(COACH_ITEMS)

    return items