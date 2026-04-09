from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.http import Http404
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import User, Clube, Desempenho, Jogador, Competicao, Partida, Gol, Escalacao
from .serializers import ClubeSerializer,ArtilheiroSerializer, DesempenhoSerializer, JogadorSerializer, CompeticaoSerializer, PartidaSerializer, PartidaListSerializer, GolSerializer, EscalacaoSerializer, TecnicoCreateSerializer
from django.db.models import Q, F, Count
from django.db import transaction
from django.utils import timezone
from collections import defaultdict
from .navigation import build_navigation_for_user
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import AllowAny
from .pagination import ClubePagination, JogadorPagination, PartidaPagination
from django.core.cache import cache


CACHE_TTL_DASHBOARD = 60
CACHE_TTL_PREVISOES = 45


def build_cache_key(prefix, *parts):
    normalized = [prefix]
    for part in parts:
        normalized.append(str(part).strip().replace(' ', '_'))
    return ':'.join(normalized)

class CustomTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        data['user_type'] = self.user.user_type
        data['username'] = self.user.username
        data['first_name'] = self.user.first_name
        data['last_name'] = self.user.last_name
        data['clube_nome'] = self.user.clube.nome if self.user.clube else None

        return data


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({'detail': 'Logout realizado com sucesso.'}, status=status.HTTP_205_RESET_CONTENT)
            return Response({'detail': 'Token de refresh não fornecido.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"detail": "E-mail é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            reset_link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            
            subject = "Redefinição de Senha - Protactic"
            message = f"Olá {user.username},\n\nVocê solicitou a redefinição de sua senha no Protactic. Clique no link abaixo para prosseguir:\n\n{reset_link}\n\nSe você não solicitou isso, ignore este e-mail."
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            return Response({"detail": "Link de redefinição enviado para o seu e-mail."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            # Por segurança, mesmo que o usuário não exista, podemos retornar a mesma mensagem
            # ou uma mensagem genérica para evitar enumeração de usuários.
            return Response({"detail": "Se este e-mail estiver cadastrado, um link de redefinição será enviado."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": f"Erro ao enviar e-mail: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not all([uid, token, new_password]):
            return Response({"detail": "Todos os campos (uid, token, nova senha) são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid_decoded = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid_decoded)
            
            if default_token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save()
                return Response({"detail": "Senha alterada com sucesso!"}, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "Link inválido ou expirado."}, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Link inválido ou expirado."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TecnicoCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not (user.is_superuser or user.user_type == 'ADMIN'):
            return Response({"detail": "Apenas administradores podem cadastrar técnicos."}, status=403)

        serializer = TecnicoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tecnico = serializer.save()

        return Response(
            {
                "id": tecnico.id,
                "username": tecnico.username,
                "email": tecnico.email,
                "user_type": tecnico.user_type,
                "clube": tecnico.clube_id,
            },
            status=201,
        )

class NavigationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        data = {
            "user": {
                "username": u.username,
                "user_type": getattr(u, "user_type", None),
                "is_superuser": u.is_superuser,
            },
            "items": build_navigation_for_user(u),
        }
        return Response(data)


class CoachHomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.user_type != 'TREINADOR' or not user.clube:
            return Response({
                "detail": "Conteúdo disponível apenas para treinador com clube associado."
            }, status=403)

        clube = user.clube
        cache_key = build_cache_key('coach_home', request.get_host(), user.id, clube.id)
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return Response(cached_payload)

        stats = Partida.objects.filter(
            Q(mandante=clube) | Q(visitante=clube)
        ).aggregate(
            total=Count('id'),
            vitorias=Count('id', filter=Q(
                (Q(mandante=clube) & Q(placar_mandante__gt=F('placar_visitante'))) |
                (Q(visitante=clube) & Q(placar_visitante__gt=F('placar_mandante')))
            )),
            derrotas=Count('id', filter=Q(
                (Q(mandante=clube) & Q(placar_mandante__lt=F('placar_visitante'))) |
                (Q(visitante=clube) & Q(placar_visitante__lt=F('placar_mandante')))
            )),
        )

        total = stats['total']
        vitorias = stats['vitorias']
        derrotas = stats['derrotas']
        empates = total - (vitorias + derrotas)

        proxima_partida = Partida.objects.filter(
            Q(mandante=clube) | Q(visitante=clube),
            data_hora__gte=timezone.now()
        ).select_related('mandante', 'visitante', 'competicao').order_by('data_hora').first()

        provavel_escalacao = []
        origem_escalacao = None

        if proxima_partida:
            titulares = Escalacao.objects.filter(
                partida=proxima_partida,
                jogador__clube=clube,
                tipo='PADRAO',
                status='TITULAR'
            ).select_related('jogador').order_by('jogador__posicao', 'jogador__nome')

            provavel_escalacao = [
                {
                    "jogador_id": item.jogador_id,
                    "nome": item.jogador.nome,
                    "posicao": item.jogador.posicao,
                    "x": item.x,
                    "y": item.y,
                }
                for item in titulares
            ]

            if provavel_escalacao:
                origem_escalacao = "partida"

        if not provavel_escalacao:
            fallback_titulares = Escalacao.objects.filter(
                jogador__clube=clube,
                tipo='PADRAO',
                status='TITULAR'
            ).values(
                'jogador_id',
                'jogador__nome',
                'jogador__posicao'
            ).annotate(
                qtd=Count('jogador')
            ).order_by('-qtd', 'jogador__nome')[:11]

            provavel_escalacao = [
                {
                    "jogador_id": item['jogador_id'],
                    "nome": item['jogador__nome'],
                    "posicao": item['jogador__posicao'],
                    "x": None,
                    "y": None,
                    "frequencia_titular": item['qtd'],
                }
                for item in fallback_titulares
            ]

            if provavel_escalacao:
                origem_escalacao = "historico"

        proximo_jogo_data = None
        if proxima_partida:
            if proxima_partida.mandante_id == clube.id:
                adversario = proxima_partida.visitante.nome
                local = "Casa"
            else:
                adversario = proxima_partida.mandante.nome
                local = "Fora"

            proximo_jogo_data = {
                "id": proxima_partida.id,
                "data_hora": proxima_partida.data_hora.isoformat(),
                "competicao": proxima_partida.competicao.nome if proxima_partida.competicao else None,
                "adversario": adversario,
                "local": local,
                "estadio": proxima_partida.local,
            }

        payload = {
            "clube": {
                "id": clube.id,
                "nome": clube.nome,
                "pais": clube.pais,
                "data_criacao": clube.data_criacao.isoformat() if clube.data_criacao else None,
                "escudo": request.build_absolute_uri(clube.escudo.url) if clube.escudo else None,
            },
            "estatisticas": {
                "total_jogos": total,
                "vitorias": vitorias,
                "derrotas": derrotas,
                "empates": empates,
                "aproveitamento": round(((vitorias * 3 + empates) / (total * 3) * 100), 1) if total > 0 else 0,
            },
            "proximo_jogo": proximo_jogo_data,
            "provavel_escalacao": provavel_escalacao,
            "origem_escalacao": origem_escalacao,
        }

        cache.set(cache_key, payload, CACHE_TTL_DASHBOARD)
        return Response(payload)

class ClubeViewSet(viewsets.ModelViewSet):
    queryset = Clube.objects.all().order_by('nome')
    serializer_class = ClubeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ClubePagination

class ClubeDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            clube = Clube.objects.get(pk=pk)
        except Clube.DoesNotExist:
            return Response({"error": "Clube não encontrado"}, status=404)

        ultimos_jogos_param = (request.query_params.get('ultimos_jogos') or '5').strip().lower()
        cache_key = build_cache_key('clube_dashboard', request.get_host(), pk, ultimos_jogos_param)
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return Response(cached_payload)

        stats = Partida.objects.filter(Q(mandante=clube) | Q(visitante=clube)).aggregate(
            total=Count('id'),
            vitorias=Count('id', filter=Q(
                (Q(mandante=clube) & Q(placar_mandante__gt=F('placar_visitante'))) |
                (Q(visitante=clube) & Q(placar_visitante__gt=F('placar_mandante')))
            )),
            derrotas=Count('id', filter=Q(
                (Q(mandante=clube) & Q(placar_mandante__lt=F('placar_visitante'))) |
                (Q(visitante=clube) & Q(placar_visitante__lt=F('placar_mandante')))
            )),
        )

        total = stats['total']
        vitorias = stats['vitorias']
        derrotas = stats['derrotas']
        empates = total - (vitorias + derrotas)

        historico_query = Partida.objects.filter(
            Q(mandante=clube) | Q(visitante=clube)
        ).order_by('-data_hora')[:5]

        historico_partidas = []
        for p in historico_query:
            if p.mandante == clube:
                adversario = p.visitante.nome
                placar = f"{p.placar_mandante} - {p.placar_visitante}"
                res = 'V' if p.placar_mandante > p.placar_visitante else ('D' if p.placar_mandante < p.placar_visitante else 'E')
            else:
                adversario = p.mandante.nome
                placar = f"{p.placar_visitante} - {p.placar_mandante}"
                res = 'V' if p.placar_visitante > p.placar_mandante else ('D' if p.placar_visitante < p.placar_mandante else 'E')
            
            historico_partidas.append({
                "adversario": adversario,
                "placar": placar,
                "resultado": res,
                "data": p.data_hora.strftime('%d/%m/%Y')
            })

        # 3. Filtro de jogos para ranking
        partidas_base = Partida.objects.filter(
            Q(mandante=clube) | Q(visitante=clube)
        ).order_by('-data_hora')

        if ultimos_jogos_param == 'all':
            partidas_filtradas = partidas_base
            ultimos_jogos_usado = 'all'
        else:
            try:
                limite_jogos = int(ultimos_jogos_param)
            except ValueError:
                limite_jogos = 5
            if limite_jogos <= 0:
                limite_jogos = 5

            partidas_filtradas = partidas_base[:limite_jogos]
            ultimos_jogos_usado = limite_jogos

        partida_ids_filtradas = list(partidas_filtradas.values_list('id', flat=True))

        gols_clube_qs = Gol.objects.filter(
            partida_id__in=partida_ids_filtradas,
            autor__clube=clube
        ).select_related('autor', 'assistencia', 'partida__mandante', 'partida__visitante').order_by(
            '-partida__data_hora', '-minuto'
        )

        ranking_artilheiros = gols_clube_qs.values('autor_id', 'autor__nome').annotate(
            gols=Count('minuto')
        ).order_by('-gols', 'autor__nome')[:10]

        ranking_assistentes = gols_clube_qs.filter(
            assistencia__isnull=False,
            assistencia__clube=clube
        ).values('assistencia_id', 'assistencia__nome').annotate(
            assistencias=Count('minuto')
        ).order_by('-assistencias', 'assistencia__nome')[:10]

        participacoes_gols = []
        for gol in gols_clube_qs[:80]:
            partida = gol.partida
            if partida.mandante_id == clube.id:
                adversario = partida.visitante.nome
            else:
                adversario = partida.mandante.nome

            participacoes_gols.append({
                "partida_id": partida.id,
                "data": partida.data_hora.strftime('%d/%m/%Y'),
                "adversario": adversario,
                "autor": gol.autor.nome,
                "assistencia": gol.assistencia.nome if gol.assistencia else None,
                "minuto": gol.minuto,
            })

        # 4. Escalações mais usadas
        titulares_qs = Escalacao.objects.filter(
            jogador__clube=clube,
            tipo='PADRAO',
            status='TITULAR'
        ).select_related('jogador', 'partida__mandante', 'partida__visitante')

        por_partida = defaultdict(list)
        for item in titulares_qs:
            por_partida[item.partida_id].append(item)

        formacao_counter = defaultdict(int)
        formacoes_partida = []

        for _, itens in por_partida.items():
            if not itens:
                continue

            partida = itens[0].partida

            def_count = 0
            mid_count = 0
            att_count = 0

            for e in itens:
                pos = (e.jogador.posicao or '').strip()
                if e.y is not None and float(e.y) >= 90 and pos != 'Goleiro':
                    # Ignora legado inválido para não distorcer a formação.
                    continue
                if pos in ['Zagueiro', 'Lateral Esquerdo', 'Lateral Direito']:
                    def_count += 1
                elif pos in ['Volante', 'Meio-campista', 'Meia Atacante']:
                    mid_count += 1
                elif pos in ['Ponta Esquerda', 'Ponta Direita', 'Centroavante']:
                    att_count += 1

            formacao = f"{def_count}-{mid_count}-{att_count}"
            formacao_counter[formacao] += 1

            if partida.mandante_id == clube.id:
                adversario = partida.visitante.nome
            else:
                adversario = partida.mandante.nome

            formacoes_partida.append({
                "partida_id": partida.id,
                "data": partida.data_hora.strftime('%d/%m/%Y'),
                "data_hora": partida.data_hora.isoformat(),
                "adversario": adversario,
                "formacao": formacao,
                "titulares": [
                    {
                        "jogador_id": e.jogador_id,
                        "nome": e.jogador.nome,
                        "posicao": e.jogador.posicao,
                        "x": e.x,
                        "y": e.y,
                    }
                    for e in itens
                ]
            })

        formacoes_partida.sort(key=lambda x: x['data_hora'], reverse=True)
        for formacao in formacoes_partida:
            formacao.pop('data_hora', None)

        todas_escalacoes = [
            {"formacao": f, "vezes": qtd}
            for f, qtd in sorted(formacao_counter.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

        escalacao_mais_usada = todas_escalacoes[0] if todas_escalacoes else None

        # 5. Resposta Final Estruturada
        payload = {
            "perfil": {
                "nome": clube.nome,
                "pais": clube.pais,
                "data_criacao": clube.data_criacao.isoformat() if clube.data_criacao else None,
                "escudo": request.build_absolute_uri(clube.escudo.url) if clube.escudo else None,
                "historia": getattr(clube, 'historia', None) # Puxa se existir o campo no banco
            },
            "estatisticas": {
                "total_jogos": total,
                "vitorias": vitorias,
                "derrotas": derrotas,
                "empates": empates,
                "aproveitamento": round(((vitorias * 3 + empates) / (total * 3) * 100), 1) if total > 0 else 0
            },
            "historico_partidas": historico_partidas,
            "filtro_ranking": {
                "ultimos_jogos": ultimos_jogos_usado,
                "total_partidas_consideradas": len(partida_ids_filtradas),
            },
            "ranking_artilheiros": [
                {
                    "jogador_id": item['autor_id'],
                    "nome": item['autor__nome'],
                    "gols": item['gols'],
                }
                for item in ranking_artilheiros
            ],
            "ranking_assistentes": [
                {
                    "jogador_id": item['assistencia_id'],
                    "nome": item['assistencia__nome'],
                    "assistencias": item['assistencias'],
                }
                for item in ranking_assistentes
            ],
            "participacoes_gols": participacoes_gols,
            "escalacao_mais_usada": escalacao_mais_usada,
            "todas_escalacoes": todas_escalacoes,
            "formacoes_partida": formacoes_partida,
        }

        cache.set(cache_key, payload, CACHE_TTL_DASHBOARD)
        return Response(payload)

class JogadorViewSet(viewsets.ModelViewSet):
    serializer_class = JogadorSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = JogadorPagination

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'TREINADOR' and user.clube:
            return Jogador.objects.filter(clube=user.clube).select_related('clube').order_by('nome')
        return Jogador.objects.all().select_related('clube').order_by('nome')


class CompeticaoViewSet(viewsets.ModelViewSet):
    queryset = Competicao.objects.all()
    serializer_class = CompeticaoSerializer
    permission_classes = [IsAuthenticated]

class CompeticaoTimesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            competicao = Competicao.objects.get(pk=pk)
        except Competicao.DoesNotExist:
            return Response({"error": "Competição não encontrada"}, status=404)

        clubes = competicao.clubes_inscritos.all().order_by('nome')

        if not clubes.exists():
            partidas = Partida.objects.filter(competicao_id=pk).values_list(
                'mandante_id', 'visitante_id'
            )

            clube_ids = set()
            for mandante_id, visitante_id in partidas:
                if mandante_id:
                    clube_ids.add(mandante_id)
                if visitante_id:
                    clube_ids.add(visitante_id)

            clubes = Clube.objects.filter(id__in=clube_ids).order_by('nome')

        if request.user.user_type == 'TREINADOR' and request.user.clube_id:
            clubes = clubes.exclude(id=request.user.clube_id)

        data = ClubeSerializer(clubes, many=True).data
        return Response(data)

class CompeticaoClubeStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, competicao_id, clube_id):
        ultimos_jogos_param = (request.query_params.get('ultimos_jogos') or '5').strip().lower()
        cache_key = build_cache_key(
            'competicao_clube_stats',
            request.get_host(),
            competicao_id,
            clube_id,
            ultimos_jogos_param,
        )
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return Response(cached_payload)

        try:
            competicao = Competicao.objects.get(pk=competicao_id)
        except Competicao.DoesNotExist:
            return Response({"error": "Competição não encontrada"}, status=404)

        try:
            clube = Clube.objects.get(pk=clube_id)
        except Clube.DoesNotExist:
            return Response({"error": "Clube não encontrado"}, status=404)

        partidas_qs = Partida.objects.filter(
            competicao=competicao
        ).filter(
            Q(mandante=clube) | Q(visitante=clube)
        ).select_related('mandante', 'visitante').order_by('-data_hora')

        stats = partidas_qs.aggregate(
            total=Count('id'),
            vitorias=Count('id', filter=Q(
                (Q(mandante=clube) & Q(placar_mandante__gt=F('placar_visitante'))) |
                (Q(visitante=clube) & Q(placar_visitante__gt=F('placar_mandante')))
            )),
            derrotas=Count('id', filter=Q(
                (Q(mandante=clube) & Q(placar_mandante__lt=F('placar_visitante'))) |
                (Q(visitante=clube) & Q(placar_visitante__lt=F('placar_mandante')))
            )),
        )

        total = stats['total']
        vitorias = stats['vitorias']
        derrotas = stats['derrotas']
        empates = total - (vitorias + derrotas)

        if ultimos_jogos_param == 'all':
            partidas_ranking_qs = partidas_qs
            ultimos_jogos_usado = 'all'
        else:
            try:
                limite_jogos = int(ultimos_jogos_param)
            except ValueError:
                limite_jogos = 5
            if limite_jogos <= 0:
                limite_jogos = 5
            partidas_ranking_qs = partidas_qs[:limite_jogos]
            ultimos_jogos_usado = limite_jogos

        partida_ids_ranking = list(partidas_ranking_qs.values_list('id', flat=True))

        gols_clube_qs = Gol.objects.filter(
            partida_id__in=partida_ids_ranking,
            autor__clube=clube
        ).select_related('autor', 'assistencia', 'partida__mandante', 'partida__visitante').order_by(
            '-partida__data_hora', '-minuto'
        )

        ranking_artilheiros = gols_clube_qs.values('autor_id', 'autor__nome').annotate(
            gols=Count('minuto')
        ).order_by('-gols', 'autor__nome')[:10]

        ranking_assistentes = gols_clube_qs.filter(
            assistencia__isnull=False,
            assistencia__clube=clube
        ).values('assistencia_id', 'assistencia__nome').annotate(
            assistencias=Count('minuto')
        ).order_by('-assistencias', 'assistencia__nome')[:10]

        participacoes_gols = []
        for gol in gols_clube_qs[:80]:
            partida = gol.partida
            adversario = partida.visitante.nome if partida.mandante_id == clube.id else partida.mandante.nome

            participacoes_gols.append({
                "partida_id": partida.id,
                "data": partida.data_hora.strftime('%d/%m/%Y'),
                "adversario": adversario,
                "autor": gol.autor.nome,
                "assistencia": gol.assistencia.nome if gol.assistencia else None,
                "minuto": gol.minuto,
            })

        titulares_qs = Escalacao.objects.filter(
            jogador__clube=clube,
            partida__in=partidas_qs,
            tipo='PADRAO',
            status='TITULAR'
        ).select_related('jogador', 'partida__mandante', 'partida__visitante')

        por_partida = defaultdict(list)
        for item in titulares_qs:
            por_partida[item.partida_id].append(item)

        formacao_counter = defaultdict(int)
        formacoes_partida = []

        for _, itens in por_partida.items():
            partida = itens[0].partida

            def_count = 0
            mid_count = 0
            att_count = 0

            for e in itens:
                pos = (e.jogador.posicao or '').strip()
                if e.y is not None and float(e.y) >= 90 and pos != 'Goleiro':
                    # Ignora legado inválido para não distorcer a formação.
                    continue
                if pos in ['Zagueiro', 'Lateral Esquerdo', 'Lateral Direito']:
                    def_count += 1
                elif pos in ['Volante', 'Meio-campista', 'Meia Atacante']:
                    mid_count += 1
                elif pos in ['Ponta Esquerda', 'Ponta Direita', 'Centroavante']:
                    att_count += 1

            formacao = f"{def_count}-{mid_count}-{att_count}"
            formacao_counter[formacao] += 1

            adversario = partida.visitante.nome if partida.mandante_id == clube.id else partida.mandante.nome

            formacoes_partida.append({
                "partida_id": partida.id,
                "data": partida.data_hora.strftime('%d/%m/%Y'),
                "data_hora": partida.data_hora.isoformat(),
                "adversario": adversario,
                "formacao": formacao,
                "titulares": [
                    {
                        "jogador_id": e.jogador_id,
                        "nome": e.jogador.nome,
                        "posicao": e.jogador.posicao,
                        "x": e.x,
                        "y": e.y,
                    }
                    for e in itens
                ]
            })

        formacoes_partida.sort(key=lambda x: x['data_hora'], reverse=True)
        for formacao in formacoes_partida:
            formacao.pop('data_hora', None)

        todas_escalacoes = [
            {"formacao": f, "vezes": qtd}
            for f, qtd in sorted(formacao_counter.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

        escalacao_mais_usada = todas_escalacoes[0] if todas_escalacoes else None

        jogos = []
        for p in partidas_qs:
            if p.mandante_id == clube.id:
                resultado = 'V' if p.placar_mandante > p.placar_visitante else ('D' if p.placar_mandante < p.placar_visitante else 'E')
            else:
                resultado = 'V' if p.placar_visitante > p.placar_mandante else ('D' if p.placar_visitante < p.placar_mandante else 'E')

            jogos.append({
                "id": p.id,
                "data": p.data_hora.strftime('%d/%m/%Y'),
                "mandante": p.mandante.nome,
                "visitante": p.visitante.nome,
                "placar_mandante": p.placar_mandante,
                "placar_visitante": p.placar_visitante,
                "resultado": resultado,
            })

        payload = {
            "competicao": {"id": competicao.id, "nome": competicao.nome},
            "clube": {
                "id": clube.id,
                "nome": clube.nome,
                "escudo": request.build_absolute_uri(clube.escudo.url) if clube.escudo else None,
            },
            "estatisticas": {
                "total_jogos": total,
                "vitorias": vitorias,
                "derrotas": derrotas,
                "empates": empates,
            },
            "jogos": jogos,
            "filtro_ranking": {
                "ultimos_jogos": ultimos_jogos_usado,
                "total_partidas_consideradas": len(partida_ids_ranking),
            },
            "ranking_artilheiros": [
                {
                    "jogador_id": item['autor_id'],
                    "nome": item['autor__nome'],
                    "gols": item['gols'],
                }
                for item in ranking_artilheiros
            ],
            "ranking_assistentes": [
                {
                    "jogador_id": item['assistencia_id'],
                    "nome": item['assistencia__nome'],
                    "assistencias": item['assistencias'],
                }
                for item in ranking_assistentes
            ],
            "participacoes_gols": participacoes_gols,
            "escalacao_mais_usada": escalacao_mais_usada,
            "todas_escalacoes": todas_escalacoes,
            "formacoes_partida": formacoes_partida,
        }

        cache.set(cache_key, payload, CACHE_TTL_DASHBOARD)
        return Response(payload)

class BuscaGlobalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        termo = request.query_params.get('q', '')
        
        if not termo or len(termo) < 2:
            return Response([])

        resultados = []

        jogadores = Jogador.objects.filter(nome__icontains=termo)[:3]
        s_jogadores = JogadorSerializer(jogadores, many=True).data
        for item in s_jogadores:
            item['tipo'] = 'JOGADOR'
            resultados.append(item)

        competicoes = Competicao.objects.filter(nome__icontains=termo)[:3]
        s_competicoes = CompeticaoSerializer(competicoes, many=True).data
        for item in s_competicoes:
            item['tipo'] = 'COMPETICAO'
            resultados.append(item)

        clubes = Clube.objects.filter(nome__icontains=termo)[:3]
        s_clubes = ClubeSerializer(clubes, many=True).data
        for item in s_clubes:
            item['tipo'] = 'CLUBE'
            resultados.append(item)

        return Response(resultados)


class PrevisoesView(APIView):
    permission_classes = [IsAuthenticated]

    def _serialize_match_for_club(self, partida, clube_id):
        if partida.mandante_id == clube_id:
            adversario = partida.visitante
            local = 'CASA'
        else:
            adversario = partida.mandante
            local = 'FORA'

        return {
            'id': partida.id,
            'data_hora': partida.data_hora.isoformat(),
            'adversario_id': adversario.id,
            'adversario_nome': adversario.nome,
            'local': local,
            'competicao': partida.competicao.nome if partida.competicao else None,
            'futuro': partida.data_hora >= timezone.now(),
        }

    def _serialize_lineup(self, escalacoes, tipo_solicitado, tipo_efetivo):
        return {
            'tipo_solicitado': tipo_solicitado,
            'tipo_efetivo': tipo_efetivo,
            'jogadores': [
                {
                    'jogador_id': item.jogador_id,
                    'nome': item.jogador.nome,
                    'posicao': item.jogador.posicao,
                    'x': item.x,
                    'y': item.y,
                }
                for item in escalacoes
            ]
        }

    def _lineups_by_tipo(self, partida, clube_id):
        escalacoes = Escalacao.objects.filter(
            partida=partida,
            jogador__clube_id=clube_id,
            status='TITULAR',
        ).select_related('jogador').order_by('jogador__posicao', 'jogador__nome')

        grouped = defaultdict(list)
        for item in escalacoes:
            grouped[item.tipo].append(item)

        return grouped

    def _resolve_tipo(self, lineups_by_tipo, tipo_desejado):
        tipo_desejado = (tipo_desejado or 'PADRAO').strip().upper()
        escalacoes = lineups_by_tipo.get(tipo_desejado, [])
        tipo_efetivo = tipo_desejado

        if not escalacoes and tipo_desejado != 'PADRAO':
            escalacoes = lineups_by_tipo.get('PADRAO', [])
            tipo_efetivo = 'PADRAO'

        return self._serialize_lineup(escalacoes, tipo_desejado, tipo_efetivo)

    def _build_comparison(self, meu_jogo, meu_clube_id, jogo_adversario, adversario_id):
        if not meu_jogo or not jogo_adversario:
            return None

        meu_time_lineups = self._lineups_by_tipo(meu_jogo, meu_clube_id)
        adversario_lineups = self._lineups_by_tipo(jogo_adversario, adversario_id)

        ataque_vs_defesa = {
            'meu_time': self._resolve_tipo(meu_time_lineups, 'OFENSIVA'),
            'adversario': self._resolve_tipo(adversario_lineups, 'DEFENSIVA'),
        }

        defesa_vs_ataque = {
            'meu_time': self._resolve_tipo(meu_time_lineups, 'DEFENSIVA'),
            'adversario': self._resolve_tipo(adversario_lineups, 'OFENSIVA'),
        }

        return {
            'ataque_vs_defesa': ataque_vs_defesa,
            'defesa_vs_ataque': defesa_vs_ataque,
            'insights': {
                'status': 'PENDENTE',
                'mensagem': 'Bloco de insights reservado para implementação futura.'
            }
        }

    def _build_metadata_payload(self, request, meu_clube, adversario_id=None):
        cache_key = build_cache_key(
            'previsoes_metadata',
            request.get_host(),
            request.user.id,
            meu_clube.id,
            adversario_id or 'none',
        )
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return cached_payload

        meus_jogos_qs = Partida.objects.filter(
            Q(mandante_id=meu_clube.id) | Q(visitante_id=meu_clube.id)
        ).select_related('mandante', 'visitante', 'competicao').order_by('-data_hora')

        meus_jogos = [
            self._serialize_match_for_club(partida, meu_clube.id)
            for partida in meus_jogos_qs
        ]

        adversarios_qs = Clube.objects.filter(
            Q(partidas_mandante__visitante_id=meu_clube.id) |
            Q(partidas_visitante__mandante_id=meu_clube.id)
        ).exclude(id=meu_clube.id).distinct().order_by('nome')

        adversarios = [
            {
                'id': clube.id,
                'nome': clube.nome,
                'escudo': request.build_absolute_uri(clube.escudo.url) if clube.escudo else None,
            }
            for clube in adversarios_qs
        ]

        jogos_adversario = []
        if adversario_id:
            jogos_adversario_qs = Partida.objects.filter(
                Q(mandante_id=adversario_id) | Q(visitante_id=adversario_id),
                data_hora__lt=timezone.now(),
            ).select_related('mandante', 'visitante', 'competicao').order_by('-data_hora')

            jogos_adversario = [
                self._serialize_match_for_club(partida, adversario_id)
                for partida in jogos_adversario_qs
            ]

        payload = {
            'meu_clube': {
                'id': meu_clube.id,
                'nome': meu_clube.nome,
                'escudo': request.build_absolute_uri(meu_clube.escudo.url) if meu_clube.escudo else None,
            },
            'meus_jogos': meus_jogos,
            'adversarios': adversarios,
            'jogos_adversario': jogos_adversario,
        }

        cache.set(cache_key, payload, CACHE_TTL_PREVISOES)
        return payload

    def _build_comparativo_payload(self, request, meu_clube, meu_jogo_id, adversario_id, jogo_adversario_id):
        if not all([meu_jogo_id, adversario_id, jogo_adversario_id]):
            raise ValidationError({
                'detail': 'Informe meu_jogo_id, adversario_id e jogo_adversario_id para gerar o comparativo.'
            })

        cache_key = build_cache_key(
            'previsoes_comparativo',
            request.get_host(),
            request.user.id,
            meu_clube.id,
            meu_jogo_id,
            adversario_id,
            jogo_adversario_id,
        )
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return cached_payload

        meu_jogo = Partida.objects.filter(
            id=meu_jogo_id,
        ).filter(
            Q(mandante_id=meu_clube.id) | Q(visitante_id=meu_clube.id)
        ).select_related('mandante', 'visitante', 'competicao').first()

        if not meu_jogo:
            raise ValidationError({'meu_jogo_id': 'Partida do seu clube não encontrada.'})

        jogo_adversario = Partida.objects.filter(
            id=jogo_adversario_id,
            data_hora__lt=timezone.now(),
        ).filter(
            Q(mandante_id=adversario_id) | Q(visitante_id=adversario_id)
        ).select_related('mandante', 'visitante', 'competicao').first()

        if not jogo_adversario:
            raise ValidationError({
                'jogo_adversario_id': (
                    'Jogo adversário inválido. Só é permitido usar partidas antigas do adversário selecionado.'
                )
            })

        payload = {
            'filtros': {
                'meu_jogo_id': meu_jogo_id,
                'adversario_id': adversario_id,
                'jogo_adversario_id': jogo_adversario_id,
            },
            'comparativo': self._build_comparison(meu_jogo, meu_clube.id, jogo_adversario, adversario_id),
        }

        cache.set(cache_key, payload, CACHE_TTL_PREVISOES)
        return payload

    def get(self, request):
        user = request.user
        if user.user_type != 'TREINADOR' or not user.clube_id:
            return Response(
                {'detail': 'Recurso disponível apenas para treinador com clube associado.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        meu_clube = user.clube
        meu_jogo_id = request.query_params.get('meu_jogo_id')
        adversario_id = request.query_params.get('adversario_id')
        jogo_adversario_id = request.query_params.get('jogo_adversario_id')
        metadata_payload = self._build_metadata_payload(request, meu_clube, adversario_id)

        comparativo_payload = {
            'filtros': {
                'meu_jogo_id': meu_jogo_id,
                'adversario_id': adversario_id,
                'jogo_adversario_id': jogo_adversario_id,
            },
            'comparativo': None,
        }

        if all([meu_jogo_id, adversario_id, jogo_adversario_id]):
            comparativo_payload = self._build_comparativo_payload(
                request,
                meu_clube,
                meu_jogo_id,
                adversario_id,
                jogo_adversario_id,
            )

        return Response({
            **metadata_payload,
            **comparativo_payload,
        })


class PrevisoesMetadataView(PrevisoesView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.user_type != 'TREINADOR' or not user.clube_id:
            return Response(
                {'detail': 'Recurso disponível apenas para treinador com clube associado.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        adversario_id = request.query_params.get('adversario_id')
        return Response(self._build_metadata_payload(request, user.clube, adversario_id))


class PrevisoesComparativoView(PrevisoesView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.user_type != 'TREINADOR' or not user.clube_id:
            return Response(
                {'detail': 'Recurso disponível apenas para treinador com clube associado.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        meu_jogo_id = request.query_params.get('meu_jogo_id')
        adversario_id = request.query_params.get('adversario_id')
        jogo_adversario_id = request.query_params.get('jogo_adversario_id')

        payload = self._build_comparativo_payload(
            request,
            user.clube,
            meu_jogo_id,
            adversario_id,
            jogo_adversario_id,
        )
        return Response(payload)
    

class PartidaViewSet(viewsets.ModelViewSet):
    queryset = Partida.objects.all().select_related('mandante', 'visitante', 'competicao').order_by('-data_hora')
    serializer_class = PartidaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PartidaPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return PartidaListSerializer
        return PartidaSerializer

    def get_queryset(self):
        queryset = Partida.objects.all().select_related('mandante', 'visitante', 'competicao').order_by('-data_hora')
        user = self.request.user

        if user.user_type == 'TREINADOR' and user.clube_id:
            queryset = queryset.filter(
                Q(mandante_id=user.clube_id) | Q(visitante_id=user.clube_id)
            )

        if getattr(self, 'action', None) == 'retrieve':
            queryset = queryset.prefetch_related('gols__autor', 'gols__assistencia')

        return queryset

    def _validate_partida_do_clube(self, mandante, visitante):
        user = self.request.user
        if user.user_type == 'TREINADOR' and user.clube_id:
            if (not mandante or not visitante) or (
                mandante.id != user.clube_id and visitante.id != user.clube_id
            ):
                raise PermissionDenied('Você só pode criar/editar partidas do seu clube.')

    def perform_create(self, serializer):
        self._validate_partida_do_clube(
            serializer.validated_data.get('mandante'),
            serializer.validated_data.get('visitante'),
        )
        serializer.save()

    def perform_update(self, serializer):
        mandante = serializer.validated_data.get('mandante', serializer.instance.mandante)
        visitante = serializer.validated_data.get('visitante', serializer.instance.visitante)
        self._validate_partida_do_clube(mandante, visitante)
        serializer.save()

class GolViewSet(viewsets.ModelViewSet):
    queryset = Gol.objects.all().select_related(
        'autor',
        'assistencia',
        'partida',
        'partida__mandante',
        'partida__visitante',
    )
    serializer_class = GolSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        lookup = self.kwargs.get(self.lookup_field)
        try:
            autor_id, partida_id, minuto = lookup.split(':', 2)
        except ValueError:
            raise Http404
        try:
            obj = self.get_queryset().get(autor_id=autor_id, partida_id=partida_id, minuto=minuto)
        except Gol.DoesNotExist:
            raise Http404
        self.check_object_permissions(self.request, obj)
        return obj


class EscalacaoViewSet(viewsets.ModelViewSet):
    queryset = Escalacao.objects.all().select_related(
        'partida',
        'partida__mandante',
        'partida__visitante',
        'jogador',
        'jogador__clube',
    )
    serializer_class = EscalacaoSerializer
    permission_classes = [IsAuthenticated]
    TIPO_PADRAO = 'PADRAO'
    TIPOS_VALIDOS = {'PADRAO', 'DEFENSIVA', 'OFENSIVA'}
    TIPOS_VARIACAO = {'DEFENSIVA', 'OFENSIVA'}

    def _normalize_tipo(self, raw_tipo):
        tipo = (raw_tipo or self.TIPO_PADRAO).strip().upper()
        if tipo not in self.TIPOS_VALIDOS:
            raise ValidationError({'tipo': 'Tipo de escalação inválido. Use PADRAO, DEFENSIVA ou OFENSIVA.'})
        return tipo

    def _validate_tipo_com_padrao(self, partida, jogador, tipo):
        if tipo not in self.TIPOS_VARIACAO:
            return

        jogadores_padrao_ids = set(
            Escalacao.objects.filter(
                partida=partida,
                tipo=self.TIPO_PADRAO,
            ).values_list('jogador_id', flat=True)
        )

        if not jogadores_padrao_ids:
            raise ValidationError({
                'tipo': (
                    'A escalação padrão deve existir antes de criar '
                    'a escalação defensiva ou ofensiva.'
                )
            })

        if jogador and jogador.id not in jogadores_padrao_ids:
            raise ValidationError({
                'jogador': (
                    'Nas escalações defensiva e ofensiva, só é permitido '
                    'usar jogadores já presentes na escalação padrão.'
                )
            })

    def get_object(self):
        lookup = self.kwargs.get(self.lookup_field)
        lookup_parts = (lookup or '').split(':')

        if len(lookup_parts) == 2:
            partida_id, jogador_id = lookup_parts
            tipo = self.TIPO_PADRAO
        elif len(lookup_parts) == 3:
            partida_id, jogador_id, tipo = lookup_parts
            tipo = tipo.strip().upper()
            if tipo not in self.TIPOS_VALIDOS:
                raise Http404
        else:
            raise Http404

        try:
            obj = Escalacao.objects.get(partida_id=partida_id, jogador_id=jogador_id, tipo=tipo)
        except Escalacao.DoesNotExist:
            raise Http404

        user = self.request.user
        if user.user_type == 'TREINADOR' and user.clube_id:
            if obj.jogador.clube_id != user.clube_id:
                raise PermissionDenied('Você não pode acessar escalações de outro clube.')
            if obj.partida.mandante_id != user.clube_id and obj.partida.visitante_id != user.clube_id:
                raise PermissionDenied('Você não pode acessar escalações de partidas de outro clube.')

        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if user.user_type == 'TREINADOR' and user.clube_id:
            queryset = queryset.filter(
                jogador__clube_id=user.clube_id
            ).filter(
                Q(partida__mandante_id=user.clube_id) | Q(partida__visitante_id=user.clube_id)
            )

        partida = self.request.query_params.get('partida', None)
        if partida:
            queryset = queryset.filter(partida=partida)

        tipo = self.request.query_params.get('tipo', None)
        if tipo:
            queryset = queryset.filter(tipo=self._normalize_tipo(tipo))
        else:
            queryset = queryset.filter(tipo=self.TIPO_PADRAO)

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        jogador = serializer.validated_data.get('jogador')
        partida = serializer.validated_data.get('partida')
        tipo = self._normalize_tipo(serializer.validated_data.get('tipo'))

        if user.user_type == 'TREINADOR' and user.clube_id:
            if not jogador or jogador.clube_id != user.clube_id:
                raise PermissionDenied('Você só pode escalar jogadores do seu clube.')
            if not partida or (partida.mandante_id != user.clube_id and partida.visitante_id != user.clube_id):
                raise PermissionDenied('Você só pode escalar em partidas do seu clube.')

        self._validate_tipo_com_padrao(partida, jogador, tipo)

        serializer.save(tipo=tipo)

    def perform_update(self, serializer):
        user = self.request.user
        jogador = serializer.validated_data.get('jogador', serializer.instance.jogador)
        partida = serializer.validated_data.get('partida', serializer.instance.partida)
        tipo = self._normalize_tipo(serializer.validated_data.get('tipo', serializer.instance.tipo))

        if tipo != serializer.instance.tipo:
            raise ValidationError({'tipo': 'Não é permitido alterar o tipo de uma escalação existente.'})

        if user.user_type == 'TREINADOR' and user.clube_id:
            if jogador.clube_id != user.clube_id:
                raise PermissionDenied('Você não pode editar escalações de outro clube.')
            if partida.mandante_id != user.clube_id and partida.visitante_id != user.clube_id:
                raise PermissionDenied('Você não pode editar escalações de partidas de outro clube.')

        self._validate_tipo_com_padrao(partida, jogador, tipo)

        serializer.save()
    
class DesempenhoViewSet(viewsets.ModelViewSet):
    queryset = Desempenho.objects.all().select_related(
        'partida',
        'partida__mandante',
        'partida__visitante',
        'jogador',
        'jogador__clube',
    )
    serializer_class = DesempenhoSerializer
    permission_classes = [IsAuthenticated]

    def _titulares_ids_da_partida(self, partida, clube_id):
        return set(
            Escalacao.objects.filter(
                partida=partida,
                tipo='PADRAO',
                status='TITULAR',
                jogador__clube_id=clube_id,
            ).values_list('jogador_id', flat=True)
        )

    def _validate_jogador_titular(self, partida, jogador):
        if not partida or not jogador:
            return

        is_titular = Escalacao.objects.filter(
            partida=partida,
            jogador=jogador,
            tipo='PADRAO',
            status='TITULAR',
        ).exists()

        if not is_titular:
            raise ValidationError({'jogador': 'Somente jogadores titulares podem receber notas nesta partida.'})

    def _get_gols_do_time(self, partida, clube_id):
        if partida.mandante_id == clube_id:
            return int(partida.placar_mandante or 0)
        if partida.visitante_id == clube_id:
            return int(partida.placar_visitante or 0)
        raise ValidationError('O clube informado nao participa desta partida.')

    def _parse_non_negative_int(self, value, field_name):
        try:
            parsed = int(value or 0)
        except (TypeError, ValueError):
            raise ValidationError({field_name: f'O campo {field_name} deve ser um inteiro.'})

        if parsed < 0:
            raise ValidationError({field_name: f'O campo {field_name} nao pode ser negativo.'})

        return parsed

    @action(detail=False, methods=['post'], url_path='bulk-save')
    def bulk_save(self, request):
        desempenhos_payload = request.data.get('desempenhos')
        if not isinstance(desempenhos_payload, list) or not desempenhos_payload:
            raise ValidationError({'desempenhos': 'Informe uma lista de desempenhos para salvar.'})

        user = request.user
        normalized_items = []
        partida_ids = set()
        clube_ids = set()

        for index, raw_item in enumerate(desempenhos_payload):
            item_serializer = self.get_serializer(data=raw_item)
            item_serializer.is_valid(raise_exception=True)
            item = item_serializer.validated_data

            partida = item.get('partida')
            jogador = item.get('jogador')
            if not partida or not jogador:
                raise ValidationError({'desempenhos': f'Item {index + 1} invalido: partida e jogador sao obrigatorios.'})

            if not jogador.clube_id:
                raise ValidationError({'desempenhos': f'Item {index + 1} invalido: jogador sem clube associado.'})

            if user.user_type == 'TREINADOR' and user.clube_id and jogador.clube_id != user.clube_id:
                raise PermissionDenied('Voce so pode salvar desempenho de jogadores do seu clube.')

            partida_ids.add(partida.id)
            clube_ids.add(jogador.clube_id)

            normalized_items.append({
                'partida': partida,
                'jogador': jogador,
                'nota': item.get('nota', 0),
                'gols': self._parse_non_negative_int(item.get('gols', 0), 'gols'),
                'gols_contra': self._parse_non_negative_int(item.get('gols_contra', 0), 'gols_contra'),
                'assistencias': self._parse_non_negative_int(item.get('assistencias', 0), 'assistencias'),
            })

        if len(partida_ids) != 1:
            raise ValidationError({'desempenhos': 'Todos os desempenhos devem ser da mesma partida.'})

        if len(clube_ids) != 1:
            raise ValidationError({'desempenhos': 'Todos os desempenhos devem pertencer ao mesmo clube.'})

        partida = normalized_items[0]['partida']
        clube_id = next(iter(clube_ids))
        gols_do_time = self._get_gols_do_time(partida, clube_id)

        titulares_ids = self._titulares_ids_da_partida(partida, clube_id)
        if not titulares_ids:
            raise ValidationError({'desempenhos': 'Nao ha titulares escalados para esta partida.'})

        payload_jogadores_ids = [item['jogador'].id for item in normalized_items]
        payload_jogadores_set = set(payload_jogadores_ids)

        if len(payload_jogadores_ids) != len(payload_jogadores_set):
            raise ValidationError({'desempenhos': 'Ha jogadores repetidos no payload.'})

        jogadores_nao_titulares = payload_jogadores_set - titulares_ids
        titulares_faltando = titulares_ids - payload_jogadores_set

        if jogadores_nao_titulares:
            raise ValidationError({'desempenhos': 'Somente jogadores titulares podem receber notas nesta partida.'})

        if titulares_faltando:
            raise ValidationError({
                'desempenhos': (
                    'Envie desempenhos para todos os titulares da partida '
                    f'({len(titulares_ids)} jogadores).'
                )
            })

        total_gols = sum(item['gols'] for item in normalized_items)
        total_gols_contra = sum(item['gols_contra'] for item in normalized_items)
        total_assistencias = sum(item['assistencias'] for item in normalized_items)

        if total_gols + total_gols_contra != gols_do_time:
            raise ValidationError({
                'gols': (
                    'A soma de gols + gols contra deve ser igual aos gols marcados pelo time na partida '
                    f'({gols_do_time}).'
                )
            })

        if total_assistencias > gols_do_time:
            raise ValidationError({
                'assistencias': (
                    'A soma de assistencias deve ser menor ou igual aos gols marcados pelo time na partida '
                    f'({gols_do_time}).'
                )
            })

        with transaction.atomic():
            for item in normalized_items:
                Desempenho.objects.update_or_create(
                    partida=item['partida'],
                    jogador=item['jogador'],
                    defaults={
                        'nota': item['nota'],
                        'gols': item['gols'],
                        'gols_contra': item['gols_contra'],
                        'assistencias': item['assistencias'],
                    }
                )

        return Response({
            'detail': 'Desempenhos salvos com sucesso.',
            'resumo': {
                'gols_time_partida': gols_do_time,
                'total_gols': total_gols,
                'total_gols_contra': total_gols_contra,
                'total_assistencias': total_assistencias,
            }
        }, status=status.HTTP_200_OK)

    def get_object(self):
        lookup = self.kwargs.get(self.lookup_field)
        try:
            partida_id, jogador_id = lookup.split(':', 1)
        except ValueError:
            raise Http404
        try:
            obj = self.get_queryset().get(partida_id=partida_id, jogador_id=jogador_id)
        except Desempenho.DoesNotExist:
            raise Http404

        user = self.request.user
        if user.user_type == 'TREINADOR' and user.clube_id:
            if obj.jogador.clube_id != user.clube_id:
                raise PermissionDenied('Você não pode acessar desempenho de outro clube.')

        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user

        if user.user_type == 'TREINADOR' and user.clube_id:
            queryset = queryset.filter(jogador__clube_id=user.clube_id)
        
        partida_id = self.request.query_params.get('partida')
        if partida_id:
            queryset = queryset.filter(partida_id=partida_id)
        
        jogador_id = self.request.query_params.get('jogador')
        if jogador_id:
            queryset = queryset.filter(jogador_id=jogador_id)
        
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        partida = serializer.validated_data.get('partida')
        jogador = serializer.validated_data.get('jogador')

        if user.user_type == 'TREINADOR' and user.clube_id:
            if not jogador or jogador.clube_id != user.clube_id:
                raise PermissionDenied('Você só pode criar desempenho de jogadores do seu clube.')

        self._validate_jogador_titular(partida, jogador)

        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        partida = serializer.validated_data.get('partida', serializer.instance.partida)
        jogador = serializer.validated_data.get('jogador', serializer.instance.jogador)

        if user.user_type == 'TREINADOR' and user.clube_id:
            if jogador.clube_id != user.clube_id:
                raise PermissionDenied('Você não pode editar desempenho de outro clube.')

        self._validate_jogador_titular(partida, jogador)

        serializer.save()