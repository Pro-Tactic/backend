from rest_framework import serializers
from django.db.models import Q

class NavItemSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    path = serializers.CharField()
    icon = serializers.CharField()

class NavResponseSerializer(serializers.Serializer):
    user = serializers.DictField()
    items = NavItemSerializer(many=True)

from .models import Clube

class ClubeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clube
        fields = '__all__'
    
    def validate_nome(self, value):
        # Verifica se já existe um clube com este nome (excluindo o próprio em caso de update)
        queryset = Clube.objects.filter(nome__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe um clube com este nome.")
        return value

class ArtilheiroSerializer(serializers.Serializer):
    nome = serializers.CharField()
    gols = serializers.IntegerField()
    posicao = serializers.CharField()

class ClubeDashboardSerializer(serializers.Serializer):
    perfil = serializers.DictField()
    estatisticas = serializers.DictField()
    artilheiros = ArtilheiroSerializer(many=True)

from .models import Jogador

class JogadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jogador
        fields = '__all__'
    
    def validate_nome(self, value):
        # Verifica se já existe um jogador com este nome (excluindo o próprio em caso de update)
        queryset = Jogador.objects.filter(nome__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe um jogador com este nome.")
        return value
    
from .models import Competicao

class CompeticaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competicao
        fields = '__all__'
    
    def validate_nome(self, value):
        # Verifica se já existe uma competição com este nome (excluindo a própria em caso de update)
        queryset = Competicao.objects.filter(nome__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe uma competição com este nome.")
        return value

from .models import Partida, Gol

class GolSerializer(serializers.ModelSerializer):
    nome_autor = serializers.ReadOnlyField(source='autor.nome')
    nome_assistencia = serializers.ReadOnlyField(source='assistencia.nome')

    class Meta:
        model = Gol
        fields = '__all__'

class PartidaSerializer(serializers.ModelSerializer):
    gols = GolSerializer(many=True, read_only=True)
    nome_mandante = serializers.ReadOnlyField(source='mandante.nome')
    nome_visitante = serializers.ReadOnlyField(source='visitante.nome')

    class Meta:
        model = Partida
        fields = '__all__'
    
    def validate(self, data):
        # Verifica se já existe uma partida na mesma data entre os mesmos times
        mandante = data.get('mandante')
        visitante = data.get('visitante')
        data_hora = data.get('data_hora')
        
        if mandante and visitante and data_hora:
            # Converte data_hora para apenas data (sem hora)
            from datetime import datetime
            if isinstance(data_hora, datetime):
                data_partida = data_hora.date()
            else:
                data_partida = data_hora
            
            # Busca partidas na mesma data com os mesmos times (em qualquer ordem)
            queryset = Partida.objects.filter(
                data_hora__date=data_partida
            ).filter(
                (Q(mandante=mandante, visitante=visitante)) |
                (Q(mandante=visitante, visitante=mandante))
            )
            
            # Exclui a própria partida em caso de update
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError(
                    "Já existe uma partida entre estes times nesta data."
                )
        
        # Valida que mandante e visitante são diferentes
        if mandante and visitante and mandante == visitante:
            raise serializers.ValidationError(
                "O time mandante e visitante não podem ser o mesmo."
            )
        
        return data

from .models import Escalacao

class EscalacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Escalacao
        fields = '__all__'

from .models import Desempenho

class DesempenhoSerializer(serializers.ModelSerializer):
    nome_jogador = serializers.ReadOnlyField(source='jogador.nome')
    posicao_jogador = serializers.ReadOnlyField(source='jogador.posicao')

    class Meta:
        model = Desempenho
        fields = ['id', 'partida', 'jogador', 'nome_jogador', 'posicao_jogador', 'nota', 'gols', 'assistencias']