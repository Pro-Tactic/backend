from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Clube, Jogador, Competicao, Partida, Gol

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Tipo de Usuário', {'fields': ('user_type',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Tipo de Usuário', {'fields': ('user_type',)}),
    )
    list_display = ('username', 'email', 'user_type', 'is_staff', 'is_active')

@admin.register(Clube)
class ClubeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'pais', 'ano_fundacao')
    search_fields = ('nome',)

@admin.register(Jogador)
class JogadorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'posicao', 'clube', 'nacionalidade')
    list_filter = ('posicao', 'clube')
    search_fields = ('nome',)

@admin.register(Competicao)
class CompeticaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_formato', 'qtd_participantes')
    list_filter = ('tipo_formato',)

@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_hora', 'mandante', 'placar_mandante', 'placar_visitante', 'visitante')
    list_filter = ('competicao', 'data_hora')
    search_fields = ('mandante__nome', 'visitante__nome')

@admin.register(Gol)
class GolAdmin(admin.ModelAdmin):
    list_display = ('autor', 'minuto', 'partida')
    list_filter = ('partida',)
    search_fields = ('autor__nome',)
