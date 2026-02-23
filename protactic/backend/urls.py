from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView, NavigationView, CoachHomeView, ClubeViewSet, JogadorViewSet, CompeticaoViewSet, BuscaGlobalView, PartidaViewSet, GolViewSet, EscalacaoViewSet, DesempenhoViewSet, ClubeDashboardView, CompeticaoTimesView, CompeticaoClubeStatsView

router = DefaultRouter()
router.register(r'clubes', ClubeViewSet)
router.register(r'jogadores', JogadorViewSet, basename='jogador')
router.register(r'competicoes', CompeticaoViewSet)
router.register(r'partidas', PartidaViewSet)
router.register(r'gols', GolViewSet)
router.register(r'escalacoes', EscalacaoViewSet)
router.register(r'desempenhos', DesempenhoViewSet)

urlpatterns = [
    path('', LoginView.as_view(), name='login'),
    path("navigation/", NavigationView.as_view(), name="navigation"),
    path("inicio/", CoachHomeView.as_view(), name="coach_home"),
    path('competicoes/<int:pk>/times/', CompeticaoTimesView.as_view(), name='competicao_times'),
    path('competicoes/<int:competicao_id>/clubes/<int:clube_id>/estatisticas/', CompeticaoClubeStatsView.as_view(), name='competicao_clube_stats'),
    path('', include(router.urls)),
    path('busca/', BuscaGlobalView.as_view(), name='busca_global'),
    path('clubes/<int:pk>/dashboard/', ClubeDashboardView.as_view())
]