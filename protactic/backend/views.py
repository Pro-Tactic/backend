from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from django.http import Http404
from .models import Clube, Desempenho, Jogador, Competicao, Partida, Gol, Escalacao
from .serializers import ClubeSerializer,ArtilheiroSerializer, DesempenhoSerializer, JogadorSerializer, CompeticaoSerializer, PartidaSerializer, GolSerializer, EscalacaoSerializer, TecnicoCreateSerializer
from django.db.models import Q, F, Count, Case, When, IntegerField
from django.utils import timezone
from collections import defaultdict
from .navigation import build_navigation_for_user

class CustomTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        data['user_type'] = self.user.user_type
        data['username'] = self.user.username

        return data


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer


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

        return Response({
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
        })

class ClubeViewSet(viewsets.ModelViewSet):
    queryset = Clube.objects.all()
    serializer_class = ClubeSerializer
    permission_classes = [IsAuthenticated]

class ClubeDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            clube = Clube.objects.get(pk=pk)
        except Clube.DoesNotExist:
            return Response({"error": "Clube não encontrado"}, status=404)

        ultimos_jogos_param = (request.query_params.get('ultimos_jogos') or '5').strip().lower()

        # 1. Dados Estatísticos Gerais (Aggregation)
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

        # 2. Histórico Geral (Últimas 5 Partidas)
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
        return Response({
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
        })

class JogadorViewSet(viewsets.ModelViewSet):
    serializer_class = JogadorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'TREINADOR' and user.clube:
            return Jogador.objects.filter(clube=user.clube)
        return Jogador.objects.all()


class CompeticaoViewSet(viewsets.ModelViewSet):
    queryset = Competicao.objects.all()
    serializer_class = CompeticaoSerializer
    permission_classes = [IsAuthenticated]

class CompeticaoTimesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            Competicao.objects.get(pk=pk)
        except Competicao.DoesNotExist:
            return Response({"error": "Competição não encontrada"}, status=404)

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

        return Response({
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
        })

class BuscaGlobalView(APIView):
    permission_classes = [IsAuthenticated] # Aberto para o autocomplete funcionar livremente

    def get(self, request):
        termo = request.query_params.get('q', '')
        
        if not termo or len(termo) < 2:
            return Response([])

        resultados = []

        # 1. Busca Jogadores
        jogadores = Jogador.objects.filter(nome__icontains=termo)[:3] # Pega top 3
        s_jogadores = JogadorSerializer(jogadores, many=True).data
        for item in s_jogadores:
            item['tipo'] = 'JOGADOR' # Etiqueta para o Front saber a cor/ícone
            resultados.append(item)

        # 2. Busca Competições
        competicoes = Competicao.objects.filter(nome__icontains=termo)[:3]
        s_competicoes = CompeticaoSerializer(competicoes, many=True).data
        for item in s_competicoes:
            item['tipo'] = 'COMPETICAO'
            resultados.append(item)

        # 3. Busca Clubes (Adicionei esse bônus já que vi o model ali)
        clubes = Clube.objects.filter(nome__icontains=termo)[:3]
        s_clubes = ClubeSerializer(clubes, many=True).data
        for item in s_clubes:
            item['tipo'] = 'CLUBE'
            resultados.append(item)

        return Response(resultados)
    

class PartidaViewSet(viewsets.ModelViewSet):
    queryset = Partida.objects.all().order_by('-data_hora') 
    serializer_class = PartidaSerializer
    permission_classes = [IsAuthenticated]

class GolViewSet(viewsets.ModelViewSet):
    queryset = Gol.objects.all()
    serializer_class = GolSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        lookup = self.kwargs.get(self.lookup_field)
        try:
            autor_id, partida_id, minuto = lookup.split(':', 2)
        except ValueError:
            raise Http404
        try:
            obj = Gol.objects.get(autor_id=autor_id, partida_id=partida_id, minuto=minuto)
        except Gol.DoesNotExist:
            raise Http404
        self.check_object_permissions(self.request, obj)
        return obj


class EscalacaoViewSet(viewsets.ModelViewSet):
    queryset = Escalacao.objects.all()
    serializer_class = EscalacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        lookup = self.kwargs.get(self.lookup_field)
        try:
            partida_id, jogador_id = lookup.split(':', 1)
        except ValueError:
            raise Http404
        try:
            obj = Escalacao.objects.get(partida_id=partida_id, jogador_id=jogador_id)
        except Escalacao.DoesNotExist:
            raise Http404
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        queryset = super().get_queryset()
        partida = self.request.query_params.get('partida', None)
        if partida:
            queryset = queryset.filter(partida=partida)
        return queryset
    
class DesempenhoViewSet(viewsets.ModelViewSet):
    queryset = Desempenho.objects.all()
    serializer_class = DesempenhoSerializer

    def get_object(self):
        lookup = self.kwargs.get(self.lookup_field)
        try:
            partida_id, jogador_id = lookup.split(':', 1)
        except ValueError:
            raise Http404
        try:
            obj = Desempenho.objects.get(partida_id=partida_id, jogador_id=jogador_id)
        except Desempenho.DoesNotExist:
            raise Http404
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        queryset = Desempenho.objects.all()
        
        partida_id = self.request.query_params.get('partida')
        if partida_id:
            queryset = queryset.filter(partida_id=partida_id)
        
        jogador_id = self.request.query_params.get('jogador')
        if jogador_id:
            queryset = queryset.filter(jogador_id=jogador_id)
        
        return queryset