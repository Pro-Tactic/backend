from django.contrib.auth.models import AbstractUser
from django.db import models
from uuid import uuid4


def generate_entity_id(prefix):
    return f"{prefix}_{uuid4().hex[:18]}"


def generate_clube_id():
    return generate_entity_id('clb')


def generate_competicao_id():
    return generate_entity_id('cmp')


def generate_jogador_id():
    return generate_entity_id('jgd')


def generate_partida_id():
    return generate_entity_id('prt')

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('ADMIN', 'Administrador'),
        ('TREINADOR', 'Treinador'),
    )

    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='ADMIN'
    )

    clube = models.ForeignKey(
        'Clube',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        if self.user_type != 'TREINADOR':
            self.user_type = 'ADMIN'
        super().save(*args, **kwargs)

class Clube(models.Model):
    id = models.CharField(max_length=50, primary_key=True, db_column='id_clube', default=generate_clube_id)
    nome = models.CharField(max_length=100, db_column='nome_clube')
    pais = models.CharField(max_length=100, db_column='pais_clube')
    data_criacao = models.DateField(blank=True, null=True, db_column='data_fundacao_clube')
    escudo = models.ImageField(upload_to='escudos/', blank=True, null=True, db_column='escudo_clube')

    class Meta:
        db_table = 'clube'

    def __str__(self):
        return self.nome
    
class Competicao(models.Model):
    id = models.CharField(max_length=50, primary_key=True, db_column='id_competicao', default=generate_competicao_id)
    nome = models.CharField(max_length=100, db_column='nome_competicao')
    tamanho = models.CharField(max_length=100, db_column='abrangencia_competicao')
    localidade = models.CharField(max_length=100, blank=True, null=True, db_column='localidade_competicao')
    tipo_participantes = models.CharField(max_length=100, db_column='tipo_participantes_competicao')
    divisao = models.CharField(max_length=100, blank=True, null=True, db_column='divisao_competicao')
    tipo_formato = models.CharField(max_length=100, blank=True, null=True, db_column='tipo_formato_competicao')
    qtd_participantes = models.IntegerField(default=0, db_column='qtd_participantes_competicao')

    class Meta:
        db_table = 'competicao'

    def __str__(self):
        return self.nome

class Jogador(models.Model):
    POSICOES_CHOICES = (
        ('Goleiro', 'Goleiro'),
        ('Zagueiro', 'Zagueiro'),
        ('Lateral Esquerdo', 'Lateral Esquerdo'),
        ('Lateral Direito', 'Lateral Direito'),
        ('Volante', 'Volante'),
        ('Meio-campista', 'Meio-campista'),
        ('Meia Atacante', 'Meia Atacante'),
        ('Ponta Esquerda', 'Ponta Esquerda'),
        ('Ponta Direita', 'Ponta Direita'),
        ('Centroavante', 'Centroavante'),
    )

    PERNAS_CHOICES = (
        ('Destro', 'Destro'),
        ('Canhoto', 'Canhoto'),
        ('Ambidestro', 'Ambidestro'),
    )

    id = models.CharField(max_length=50, primary_key=True, db_column='id_jogador', default=generate_jogador_id)
    nome = models.CharField(max_length=100, db_column='nome_jogador')
    cpf = models.CharField(max_length=14, unique=True, db_column='cpf_jogador')
    data_nascimento = models.DateField(null=True, blank=True, db_column='data_nascimento_jogador')
    peso = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='peso_jogador')
    altura = models.IntegerField(blank=True, null=True, db_column='altura_jogador')
    nacionalidade = models.CharField(max_length=100, db_column='nacionalidade_jogador')
    posicao = models.CharField(max_length=50, choices=POSICOES_CHOICES, db_column='posicao_jogador')
    perna = models.CharField(max_length=20, choices=PERNAS_CHOICES, db_column='perna_jogador')
    foto = models.ImageField(upload_to='jogadores/', blank=True, null=True, db_column='foto_jogador')
    
    clube = models.ForeignKey(Clube, on_delete=models.SET_NULL, related_name='jogadores', blank=True, null=True, db_column='id_clube')

    class Meta:
        db_table = 'jogador'

    def __str__(self):
        if self.clube:
            return f"{self.nome} ({self.clube.nome})"
        return self.nome
    
class Partida(models.Model):
    id = models.CharField(max_length=50, primary_key=True, db_column='id_partida', default=generate_partida_id)
    competicao = models.ForeignKey(Competicao, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_competicao')
    mandante = models.ForeignKey(Clube, on_delete=models.CASCADE, related_name='partidas_mandante', db_column='id_clube_mandante')
    visitante = models.ForeignKey(Clube, on_delete=models.CASCADE, related_name='partidas_visitante', db_column='id_clube_visitante')
    data_hora = models.DateTimeField(db_column='data_hora_partida')
    local = models.CharField(max_length=150, blank=True, null=True, db_column='local_partida')
    placar_mandante = models.IntegerField(default=0, db_column='placar_mandante_partida')
    placar_visitante = models.IntegerField(default=0, db_column='placar_visitante_partida')

    class Meta:
        db_table = 'partida'

    def __str__(self):
        return f"{self.mandante} {self.placar_mandante}x{self.placar_visitante} {self.visitante} ({self.data_hora.strftime('%d/%m/%Y')})"

class Gol(models.Model):
    autor = models.ForeignKey(Jogador, on_delete=models.CASCADE, related_name='gols_marcados', db_column='id_jogador')
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name='gols', db_column='id_partida')
    minuto = models.IntegerField(default=0, help_text="Minuto do gol", db_column='minuto_gol')
    assistencia = models.ForeignKey(Jogador, on_delete=models.SET_NULL, null=True, blank=True, related_name='assistencias_feitas', db_column='id_jogador_assistencia_gol')
    pk = models.CompositePrimaryKey('autor', 'partida', 'minuto')

    class Meta:
        db_table = 'gol'

    def __str__(self):
        desc = f"Gol de {self.autor.nome}"
        if self.assistencia:
            desc += f" (Ass: {self.assistencia.nome})"
        return desc

class Escalacao(models.Model):
    STATUS_CHOICES = (
        ('TITULAR', 'Titular'),
        ('RESERVA', 'Reserva'),
    )

    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name='escalacoes', db_column='id_partida')
    jogador = models.ForeignKey(Jogador, on_delete=models.CASCADE, related_name='escalacoes', db_column='id_jogador')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, db_column='status_escalacao')
    
    # Coordenadas (porcentagem 0-100)
    x = models.FloatField(null=True, blank=True, db_column='coord_x_escalacao')
    y = models.FloatField(null=True, blank=True, db_column='coord_y_escalacao')
    pk = models.CompositePrimaryKey('partida', 'jogador')
    
    class Meta:
        db_table = 'escalacao'

    def __str__(self):
        return f"{self.jogador.nome} - {self.status} ({self.partida})"

class Desempenho(models.Model):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name='desempenhos', db_column='id_partida')
    jogador = models.ForeignKey(Jogador, on_delete=models.CASCADE, related_name='desempenhos', db_column='id_jogador')
    gols = models.IntegerField(default=0, db_column='gol_desempenho')
    assistencias = models.IntegerField(default=0, db_column='assistencia_desempenho')
    nota = models.DecimalField(max_digits=4, decimal_places=2, default=0, db_column='nota_desempenho')
    cartao_amarelo = models.IntegerField(default=0, db_column='cartao_amarelo_desempenho')
    cartao_vermelho = models.IntegerField(default=0, db_column='cartao_vermelho_desempenho')
    minutos_jogados = models.IntegerField(null=True, blank=True, db_column='minutos_jogados_desempenho')
    pk = models.CompositePrimaryKey('partida', 'jogador')

    class Meta:
        db_table = 'desempenho'
        verbose_name = "Desempenho"

    def __str__(self):
        return f"{self.jogador.nome} - {self.nota}"