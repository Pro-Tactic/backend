from rest_framework import serializers
from django.db.models import Q
from .models import Jogador
from .models import Clube, User
from .models import Competicao
from .models import Partida, Gol
from datetime import datetime
from .models import Desempenho

class NavItemSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    path = serializers.CharField()
    icon = serializers.CharField()

class NavResponseSerializer(serializers.Serializer):
    user = serializers.DictField()
    items = NavItemSerializer(many=True)

class TecnicoCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'clube', 'user_type']
        read_only_fields = ['id', 'user_type']

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Já existe um usuário com esse login.")
        return value

    def validate_clube(self, value):
        if not value:
            raise serializers.ValidationError("É obrigatório vincular o técnico a um clube.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['user_type'] = 'TREINADOR'
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

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

class JogadorSerializer(serializers.ModelSerializer):
    nome_clube = serializers.ReadOnlyField(source='clube.nome')
    foto = serializers.SerializerMethodField()

    class Meta:
        model = Jogador
        fields = '__all__'

    def get_foto(self, obj):
        """
        Retorna a URL da foto do jogador.
        - Se for uma URL externa (http/https), retorna direto.
        - Se for um path interno (upload local), constrói a URL absoluta via request.
        - Se estiver vazio, retorna None.
        """
        valor = obj.foto.name if obj.foto else None
        if not valor:
            return None
        # URL externa (Wikipedia, ui-avatars, etc.) — retorna sem alteração
        if valor.startswith("http://") or valor.startswith("https://"):
            return valor
        # Path interno — constrói URL absoluta usando o request
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(f"/media/{valor.lstrip('/')}")
        return f"/media/{valor.lstrip('/')}"

    def validate_nome(self, value):
        queryset = Jogador.objects.filter(nome__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe um jogador com este nome.")
        return value

class CompeticaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competicao
        fields = '__all__'
    
    def validate_nome(self, value):
        queryset = Competicao.objects.filter(nome__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe uma competição com este nome.")
        return value


class GolSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(read_only=True)
    nome_autor = serializers.ReadOnlyField(source='autor.nome')
    nome_assistencia = serializers.ReadOnlyField(source='assistencia.nome')

    class Meta:
        model = Gol
        fields = ['id', 'partida', 'autor', 'assistencia', 'minuto', 'nome_autor', 'nome_assistencia']

    def get_id(self, obj):
        return f"{obj.autor_id}:{obj.partida_id}:{obj.minuto}"

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


class PartidaListSerializer(serializers.ModelSerializer):
    nome_mandante = serializers.ReadOnlyField(source='mandante.nome')
    nome_visitante = serializers.ReadOnlyField(source='visitante.nome')

    class Meta:
        model = Partida
        fields = [
            'id',
            'competicao',
            'mandante',
            'visitante',
            'data_hora',
            'local',
            'placar_mandante',
            'placar_visitante',
            'nome_mandante',
            'nome_visitante',
        ]

from .models import Escalacao

class EscalacaoSerializer(serializers.ModelSerializer):
    GOLEIRO_LINHA_Y_MIN = 90.0
    id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Escalacao
        fields = ['id', 'partida', 'jogador', 'tipo', 'status', 'x', 'y']

    def get_id(self, obj):
        return f"{obj.partida_id}:{obj.jogador_id}:{obj.tipo}"

    def validate(self, data):
        jogador = data.get('jogador', getattr(self.instance, 'jogador', None))
        status = data.get('status', getattr(self.instance, 'status', None))
        y = data.get('y', getattr(self.instance, 'y', None))

        if not jogador or status != 'TITULAR' or y is None:
            return data

        is_goleiro = (jogador.posicao or '').strip() == 'Goleiro'
        esta_na_linha_do_goleiro = float(y) >= self.GOLEIRO_LINHA_Y_MIN

        if not is_goleiro and esta_na_linha_do_goleiro:
            raise serializers.ValidationError({
                'y': 'A linha do goleiro permite apenas jogadores da posição Goleiro.'
            })

        if is_goleiro and not esta_na_linha_do_goleiro:
            raise serializers.ValidationError({
                'y': 'O goleiro deve ser posicionado na linha do goleiro.'
            })

        return data

class DesempenhoSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(read_only=True)
    nome_jogador = serializers.ReadOnlyField(source='jogador.nome')
    posicao_jogador = serializers.ReadOnlyField(source='jogador.posicao')

    class Meta:
        model = Desempenho
        fields = ['id', 'partida', 'jogador', 'nome_jogador', 'posicao_jogador', 'nota', 'gols', 'gols_contra', 'assistencias']

    def get_id(self, obj):
        return f"{obj.partida_id}:{obj.jogador_id}"

    def validate_gols(self, value):
        if value < 0:
            raise serializers.ValidationError('Gols nao pode ser negativo.')
        return value

    def validate_gols_contra(self, value):
        if value < 0:
            raise serializers.ValidationError('Gols contra nao pode ser negativo.')
        return value

    def validate_assistencias(self, value):
        if value < 0:
            raise serializers.ValidationError('Assistencias nao pode ser negativo.')
        return value