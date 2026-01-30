from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from .models import Clube, Desempenho, Jogador, Competicao, Partida, Gol, Escalacao
from .serializers import ClubeSerializer, DesempenhoSerializer, JogadorSerializer, CompeticaoSerializer, PartidaSerializer, GolSerializer, EscalacaoSerializer

from .navigation import build_navigation_for_user

class CustomTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        data['user_type'] = self.user.user_type
        data['username'] = self.user.username

        return data


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer

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

class ClubeViewSet(viewsets.ModelViewSet):
    queryset = Clube.objects.all()
    serializer_class = ClubeSerializer
    permission_classes = [IsAuthenticated]


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


class EscalacaoViewSet(viewsets.ModelViewSet):
    queryset = Escalacao.objects.all()
    serializer_class = EscalacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        partida = self.request.query_params.get('partida', None)
        if partida:
            queryset = queryset.filter(partida=partida)
        return queryset
    
class DesempenhoViewSet(viewsets.ModelViewSet):
    queryset = Desempenho.objects.all()
    serializer_class = DesempenhoSerializer

    def get_queryset(self):
        queryset = Desempenho.objects.all()
        
        partida_id = self.request.query_params.get('partida')
        if partida_id:
            queryset = queryset.filter(partida_id=partida_id)
        
        jogador_id = self.request.query_params.get('jogador')
        if jogador_id:
            queryset = queryset.filter(jogador_id=jogador_id)
        
        return queryset