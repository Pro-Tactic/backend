# ProTactic Backend

Uma API REST completa desenvolvida com **Django REST Framework** para gerenciamento de times de futebol, jogadores, competições e escalações em tempo real.

## 📋 Tabela de Conteúdos

- [Visão Geral](#visão-geral)
- [Stack Tecnológico](#stack-tecnológico)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Como Rodar](#como-rodar)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [API Endpoints](#api-endpoints)
- [Modelos de Dados](#modelos-de-dados)
- [Autenticação](#autenticação)
- [CORS](#cors)
- [Contribuição](#contribuição)
- [Licença](#licença)

## 🎯 Visão Geral

O **ProTactic** é uma plataforma robusta de gestão tática de futebol que permite:

- ✅ Gerenciamento de usuários (Administradores e Treinadores)
- ✅ Cadastro de times e suas informações
- ✅ Registro completo de jogadores (incluindo fotos)
- ✅ Criação e gerenciamento de competições
- ✅ Gerenciamento de escalações e posicionamento tático
- ✅ Registro de gols e eventos em tempo real
- ✅ Sistema de navegação personalizado por tipo de usuário

## 🛠 Stack Tecnológico

| Tecnologia | Versão | Uso |
|---|---|---|
| **Python** | 3.8+ | Linguagem principal |
| **Django** | 6.0 | Framework web |
| **Django REST Framework** | - | API REST |
| **Django CORS Headers** | - | Gerenciamento de CORS |
| **Simplejwt** | - | Autenticação JWT |
| **Pillow** | - | Processamento de imagens |

## 📦 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Python 3.8+** [Download aqui](https://www.python.org/downloads/)
- **pip** (gerenciador de pacotes Python)
- **Git** (controle de versão)
- **MySQL** ou **SQLite** (banco de dados)

### Verificar instalação

```bash
python --version
pip --version
```

## 💾 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/Pro-Tactic/backend.git
cd backend
```

### 2. Crie um ambiente virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Aplique as migrações

```bash
cd protactic
python manage.py migrate
```

### 5. Crie um superusuário

```bash
python manage.py createsuperuser
```

Responda às perguntas:
- **Username**: seu_usuario
- **Email**: seu_email@example.com
- **Password**: sua_senha

## ⚙️ Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto (pasta `protactic`):

```env
# Django Settings
DEBUG=True
SECRET_KEY=seu-secret-key-aqui
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# JWT
JWT_SECRET_KEY=seu-jwt-secret-aqui
JWT_ALGORITHM=HS256
```

### Configurações Django

As configurações principais estão em `protactic/settings.py`:

- **DEBUG**: Modo desenvolvimento (True) / produção (False)
- **ALLOWED_HOSTS**: Hosts permitidos
- **INSTALLED_APPS**: Aplicações registradas
- **CORS**: Configuração de requisições cross-origin
- **JWT**: Autenticação por token JWT

## 🚀 Como Rodar

### Modo Desenvolvimento

```bash
cd protactic
python manage.py runserver
```

A API estará disponível em: `http://localhost:8000`

### Painel Admin

Acesse o painel administrativo em: `http://localhost:8000/admin`
- Use as credenciais do superusuário criado

### Criar Dados de Teste (Fixtures)

```bash
# Populate players
python populate_players.py

# Reset lineups
python reset_lineups.py

# Fix player club relations
python fix_player_club.py
```

## 📁 Estrutura do Projeto

```
backend/
├── protactic/                   # Projeto Django principal
│   ├── protactic/              # Configurações globais
│   │   ├── settings.py         # Configurações Django
│   │   ├── urls.py             # URLs principais
│   │   ├── asgi.py             # ASGI config
│   │   └── wsgi.py             # WSGI config
│   │
│   ├── backend/                # App principal
│   │   ├── models.py           # Modelos de dados
│   │   ├── views.py            # Viewsets e views
│   │   ├── serializers.py      # Serializers DRF
│   │   ├── urls.py             # URLs da app
│   │   ├── admin.py            # Configuração do admin
│   │   └── migrations/         # Migrações de banco
│   │
│   ├── media/                  # Arquivos de mídia
│   │   ├── escudos/            # Logos dos times
│   │   └── jogadores/          # Fotos dos jogadores
│   │
│   ├── db.sqlite3              # Banco de dados local
│   └── manage.py               # CLI Django
│
├── requirements.txt            # Dependências Python
└── README.md                   # Este arquivo
```

## 🔌 API Endpoints

### Autenticação

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/token/` | Obter token JWT |
| POST | `/api/token/refresh/` | Renovar token JWT |
| POST | `/api/register/` | Registrar novo usuário |

### Usuários

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/users/` | Listar usuários |
| POST | `/api/users/` | Criar usuário |
| GET | `/api/users/{id}/` | Obter detalhes do usuário |
| PUT | `/api/users/{id}/` | Atualizar usuário |
| DELETE | `/api/users/{id}/` | Deletar usuário |

### Times (Clubes)

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/clubes/` | Listar times |
| POST | `/api/clubes/` | Criar time |
| GET | `/api/clubes/{id}/` | Obter detalhes do time |
| PUT | `/api/clubes/{id}/` | Atualizar time |
| DELETE | `/api/clubes/{id}/` | Deletar time |

### Jogadores

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/jogadores/` | Listar jogadores |
| POST | `/api/jogadores/` | Criar jogador |
| GET | `/api/jogadores/{id}/` | Obter detalhes |
| PUT | `/api/jogadores/{id}/` | Atualizar jogador |
| DELETE | `/api/jogadores/{id}/` | Deletar jogador |

### Competições

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/competicoes/` | Listar competições |
| POST | `/api/competicoes/` | Criar competição |
| GET | `/api/competicoes/{id}/` | Obter detalhes |

### Escalações

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/escalacoes/` | Listar escalações |
| POST | `/api/escalacoes/` | Criar escalação |
| GET | `/api/escalacoes/{id}/` | Obter detalhes |

### Gols e Eventos

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/gols/` | Listar gols |
| POST | `/api/gols/` | Registrar gol |

## 📊 Modelos de Dados

### User
Usuário do sistema com dois tipos: **Administrador** e **Treinador**

```python
- id: UUID
- username: string (único)
- email: string (único)
- password: string (hash)
- user_type: choice (ADMIN | TREINADOR)
- clube: ForeignKey(Clube)
- created_at: datetime
```

### Clube
Informações do time/clube

```python
- id: UUID
- nome: string (máx 100)
- pais: string (máx 50)
- ano_fundacao: integer
- escudo: ImageField (opcional)
```

### Jogador
Dados do jogador

```python
- id: UUID
- nome: string (máx 100)
- numero: integer
- posicao: choice
- clube: ForeignKey(Clube)
- foto: ImageField (opcional)
```

### Competição
Detalhes da competição

```python
- id: UUID
- nome: string (máx 200)
- tamanho: choice
- localidade: string (opcional)
- tipo_participantes: string
- divisao: string
- tipo_formato: string
- qtd_participantes: integer
- tem_trofeu: boolean
- tem_premiacao_financeira: boolean
- valor_premiacao: decimal (opcional)
```

### Escalação
Lineup/formação tática

```python
- id: UUID
- jogador: ForeignKey(Jogador)
- posicao_x: float
- posicao_y: float
- criada_em: datetime
```

## 🔐 Autenticação

O backend usa **JWT (JSON Web Tokens)** para autenticação segura.

### Fluxo de Login

1. Envie credenciais para `/api/token/`:
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

2. Receba o token:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

3. Use o token em requisições:
```bash
curl -H "Authorization: Bearer {seu_token}" \
  http://localhost:8000/api/users/
```

## 🌐 CORS

A configuração CORS permite requisições do frontend. Configure em `settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",      # Vite dev server
    "http://localhost:3000",      # React dev server
    "https://seu-dominio.com",    # Produção
]
```

## 🧪 Testes

```bash
python manage.py test
```

## 📝 Exemplos de Uso

### Criar um novo jogador

```bash
curl -X POST http://localhost:8000/api/jogadores/ \
  -H "Authorization: Bearer seu_token" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Pelé",
    "numero": 10,
    "posicao": "Meia",
    "clube": 1
  }'
```

### Obter lista de jogadores

```bash
curl -H "Authorization: Bearer seu_token" \
  http://localhost:8000/api/jogadores/
```

## 🚨 Troubleshooting

### Erro de Migração
```bash
python manage.py migrate --fake initial
python manage.py migrate
```

### Erro de CORS
Certifique-se de que a URL do frontend está em `CORS_ALLOWED_ORIGINS`

### Erro de Banco de Dados
```bash
# Limpar banco
rm db.sqlite3
python manage.py migrate
```

## 📚 Documentação Oficial

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/)

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

**Desenvolvido com ❤️ pelo time ProTactic**

Para dúvidas ou sugestões, abra uma [issue](https://github.com/Pro-Tactic/backend/issues).
