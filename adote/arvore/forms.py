from django.contrib.auth.models import User
from .models import SolicitacaoDoacao, EspecieQuantidade, Muda, DoacaoAvulso
from django.contrib.auth.forms import UserCreationForm
from django.forms import inlineformset_factory
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


class DateInput(forms.DateInput):
    input_type = 'date'


class DoacaoAvulsoForm(forms.ModelForm):
    telefone = forms.CharField(widget=forms.TextInput(attrs={
            'type': 'tel',
            'placeholder': '(99)99999-9999',
            'pattern': '[0-9()\\-\\s]{15}',
            'title': 'Informe um número de telefone válido (apenas números)',
            'required': True
        }))
    data_plantio = forms.DateField(widget=DateInput())
    data_adocao = forms.DateField(widget=DateInput())

    class Meta:
        model = DoacaoAvulso
        fields = '__all__'
        exclude = ['funcionario']


class EspecieQuantidadeForm(forms.ModelForm):
    class Meta:
        model = EspecieQuantidade
        fields = ['especie', 'quantidade']


EspecieQuantidadeFormSet = inlineformset_factory(
    DoacaoAvulso,
    EspecieQuantidade,
    form=EspecieQuantidadeForm,
    extra=1,  # número inicial de formulários vazios exibidos
)


class EspecieQuantidadeFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        super(EspecieQuantidadeFormSet, self).__init__(*args, **kwargs)

        for form in self.forms:
            form.fields['data_plantio'].initial = form.instance.data_plantio
            form.fields['data_adocao'].initial = form.instance.data_adocao


class DoacaoAvulsoForm2(forms.ModelForm):
    telefone = forms.CharField(widget=forms.TextInput(attrs={
            'type': 'tel',
            'placeholder': '(99)99999-9999',
            'title': 'Informe um número de telefone válido (apenas números)',
            'required': True
        }))

    class Meta:
        model = DoacaoAvulso
        fields = '__all__'
        exclude = ['funcionario']
