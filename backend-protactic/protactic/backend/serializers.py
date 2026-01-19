from rest_framework import serializers

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

from .models import Jogador

class JogadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jogador
        fields = '__all__'
    
from .models import Competicao

class CompeticaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competicao
        fields = '__all__'

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
