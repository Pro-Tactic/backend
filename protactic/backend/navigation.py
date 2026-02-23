# Itens disponíveis para TREINADORES
COACH_ITEMS = [
    {"key": "inicio", "label": "Início", "path": "/inicio", "icon": "home"},
    {"key": "elenco", "label": "Central do Elenco", "path": "/elenco", "icon": "users"},
    {"key": "adversario", "label": "Previsões", "path": "/adversario", "icon": "target"},
    {"key": "tempo_real", "label": "Tempo Real", "path": "/tempo-real", "icon": "activity"},
    {"key": "competicoes", "label": "Competições & Clubes", "path": "/competicoes", "icon": "trophy"},
    {"key": "listar_jogadores", "label": "Listar Jogadores", "path": "/listar-jogadores", "icon": "users"},
    {"key": "notas", "label": "Avaliação", "path": "/notas", "icon": "notas"},
]

# Itens disponíveis para ADMIN
ADMIN_ITEMS = [
    {"key": "partidas", "label": "Partidas", "path": "/partidas", "icon": "activity"},
    {"key": "registro", "label": "Registro", "path": "/registro", "icon": "shield"},
]

def build_navigation_for_user(user):
    """
    Constrói a navegação baseada no tipo de usuário.
    - ADMIN (ou is_superuser): apenas menu de Registro
    - TREINADOR: menu completo de técnico
    """
    if user.is_superuser or user.user_type == 'ADMIN':
        return list(ADMIN_ITEMS)

    if user.user_type == 'TREINADOR':
        return list(COACH_ITEMS)

    return []