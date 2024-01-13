from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(max_length=254)
    nome_completo = models.CharField(max_length=100)
    endereco = models.CharField(max_length=200)
    telefone = models.CharField(max_length=20)
    cpf = models.CharField(max_length=14)

    def __str__(self):
        return self.user.username


class Muda(models.Model):
    nome = models.CharField(max_length=100)
    especie = models.CharField(max_length=100)
    descricao = models.TextField()

    def __str__(self):
        return self.nome


class SolicitacaoDoacao(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    especie = models.CharField(max_length=100)
    quantidade_solicitada = models.IntegerField()
    status = models.CharField(max_length=20, default='Pendente')
    local_de_plantio = models.CharField(max_length=200)
    data_solicitacao = models.DateTimeField(null=True, blank=True)
    observacoes = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f'Solicitação de {self.usuario.username}'


class EfetivarDoacao(models.Model):
    solicitacao = models.OneToOneField(SolicitacaoDoacao, on_delete=models.CASCADE, related_name='efetivacao')
    quantidade_efetivada = models.IntegerField()
    especie_doada = models.CharField(max_length=100, null=True, blank=True)
    avaliador = models.ForeignKey(User, on_delete=models.CASCADE)
    data_plantio = models.DateTimeField(null=True, blank=True)
    data_efetivacao = models.DateTimeField(null=True, blank=True)
    observacoes = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f'Doação efetivada para {self.solicitacao.usuario.username} - {self.solicitacao.especie}'
