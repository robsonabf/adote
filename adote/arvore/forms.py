from django.contrib.auth.models import User
from .models import Muda
from .models import SolicitacaoDoacao
from django.contrib.auth.forms import UserCreationForm


from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = ['username', 'password']


class MudaForm(forms.ModelForm):
    class Meta:
        model = Muda
        fields = ['nome', 'especie', 'descricao']


class SolicitacaoDoacaoForm(forms.ModelForm):

    class Meta:
        model = SolicitacaoDoacao
        fields = ['especie', 'quantidade_solicitada', 'local_de_plantio']
        widgets = {
            'especie': forms.TextInput(attrs={'class': 'form-control'}),
            'quantidade_solicitada': forms.NumberInput(attrs={'class': 'form-control'}),
            'local_de_plantio': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'especie': 'Espécie',
            'quantidade_solicitada': 'Quantidade Solicitada',
            'local_de_plantio': 'Local de Plantio',
        }


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label='E-mail'  # Adicionando a label manualmente
    )
    nome_completo = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Nome Completo'
    )
    endereco = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Endereço'
    )
    telefone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Telefone'
    )
    cpf = forms.CharField(
        max_length=14,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='CPF'
    )

    class Meta:
        model = User
        fields = ['username',  'email', 'password1', 'password2', 'nome_completo', 'endereco', 'telefone', 'cpf']
