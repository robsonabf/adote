from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from .models import Muda, SolicitacaoDoacao, EfetivarDoacao, UserProfile
from django.contrib.auth import login
from django.contrib.auth.decorators import user_passes_test
from .forms import MudaForm, SolicitacaoDoacaoForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import ExtractYear


@login_required
def lista_mudas(request):
    mudas = Muda.objects.all()
    return render(request, 'lista_mudas.html', {'mudas': mudas})


@login_required
def detalhes_muda(request, muda_id):
    muda = get_object_or_404(Muda, pk=muda_id)
    return render(request, 'detalhes_muda.html', {'muda': muda})


def index(request):
    return render(request, 'index.html')


def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()

            # Crie o perfil do usuário
            UserProfile.objects.create(
                user=user,
                email=form.cleaned_data['email'],
                nome_completo=form.cleaned_data['nome_completo'],
                endereco=form.cleaned_data['endereco'],
                telefone=form.cleaned_data['telefone'],
                cpf=form.cleaned_data['cpf']
            )

            login(request, user)
            return redirect('index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})


def is_member_of_team(user):
    # Verifica se o usuário pertence ao grupo 'equipe'
    is_in_team_group = user.groups.filter(name='equipe').exists()

    # Verifica se o usuário é um superusuário (opcional, dependendo dos requisitos)
    is_superuser = user.is_superuser

    # Retorna True se o usuário pertencer ao grupo 'equipe' ou for um superusuário
    return is_in_team_group or is_superuser


@login_required
@user_passes_test(is_member_of_team)
def admin_dashboard(request):
    dados_estatisticos = obter_dados_estatisticos()
    return render(request, 'admin_dashboard.html', {'dados_estatisticos': dados_estatisticos})


def obter_dados_estatisticos():
    # Contagem por ano
    dados_por_ano = EfetivarDoacao.objects.annotate(ano=ExtractYear('data_efetivacao')).values('ano').annotate(count=Count('ano'))

    # Contagem por espécie
    dados_por_especie = EfetivarDoacao.objects.values('especie_doada').annotate(count=Count('especie_doada'))

    # Contagem por tipo de solicitação
    dados_por_tipo_solicitacao = SolicitacaoDoacao.objects.values('status').annotate(count=Count('status'))

    # Contagem por tipo de solicitação
    dados_por_especie_solicitacao = SolicitacaoDoacao.objects.values('especie').annotate(count=Count('especie'))

    # Convertendo os resultados para listas
    lista_por_ano = list(dados_por_ano)
    lista_por_especie = list(dados_por_especie)
    lista_por_tipo_solicitacao = list(dados_por_tipo_solicitacao)
    lista_por_especie_solicitacao = list(dados_por_especie_solicitacao)

    return {'por_ano': lista_por_ano, 'por_especie': lista_por_especie, 'por_tipo_solicitacao': lista_por_tipo_solicitacao, 'por_especie_solicitacao': lista_por_especie_solicitacao}


@login_required
@user_passes_test(is_member_of_team)
def adicionar_muda(request):
    if request.method == 'POST':
        form = MudaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')  # Redirecionar para a página do dashboard
    else:
        form = MudaForm()

    return render(request, 'adicionar_muda.html', {'form': form})


@login_required
def solicitar_doacao(request):
    if request.method == 'POST':
        form = SolicitacaoDoacaoForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.usuario = request.user
            solicitacao.data_solicitacao = timezone.now()  # Adiciona a data atual
            solicitacao.save()
            # Adiciona uma mensagem de sucesso
            messages.success(request, 'Solicitação de doação realizada com sucesso!')
            return redirect('index')  # Redirecionar para a página do dashboard ou outra página desejada
    else:
        form = SolicitacaoDoacaoForm()

    return render(request, 'solicitar_doacao.html', {'form': form})


@login_required
@user_passes_test(is_member_of_team)
def listar_solicitacoes(request):
    solicitacoes = SolicitacaoDoacao.objects.all()
    efetivadas = EfetivarDoacao.objects.all()
    return render(request, 'listar_solicitacoes.html', {'solicitacoes': solicitacoes, 'efetivadas': efetivadas})


@login_required
@user_passes_test(is_member_of_team)
def aprovar_reprovar_doacao(request, solicitacao_id):
    solicitacao = SolicitacaoDoacao.objects.get(pk=solicitacao_id)

    if request.method == 'POST':
        if 'aprovar' in request.POST:
            # Recupere a quantidade efetivada do request.POST
            quantidade_efetivada = request.POST.get('quantidade_efetivada')
            observacoes = request.POST.get('observacoes')

            # Verifique se a quantidade_efetivada é um número válido
            if quantidade_efetivada.isdigit():
                quantidade_efetivada = int(quantidade_efetivada)

                # Crie a instância EfetivarDoacao e salve
                efetivacao = EfetivarDoacao.objects.create(
                    solicitacao=solicitacao,
                    quantidade_efetivada=quantidade_efetivada,
                    avaliador=request.user,
                    observacoes=observacoes,
                    especie_doada=solicitacao.especie,
                    data_plantio=solicitacao.data_solicitacao,
                    data_efetivacao= timezone.now()
                )

                # Atualize o status da SolicitacaoDoacao para 'Aprovada'
                solicitacao.status = 'Aprovada'
                solicitacao.save()
                efetivacao.save()

        elif 'reprovar' in request.POST:
            # Atualize o status da SolicitacaoDoacao para 'Reprovada'
            observacoes = request.POST.get('observacoes')
            solicitacao.status = 'Reprovada'
            solicitacao.observacoes = observacoes
            solicitacao.save()

        return redirect('listar_solicitacoes')

    return render(request, 'aprovar_reprovar_doacao.html', {'solicitacao': solicitacao})


@login_required
def minhas_solicitacoes(request):
    solicitacoes = SolicitacaoDoacao.objects.filter(usuario=request.user)
    efetivadas = EfetivarDoacao.objects.filter(solicitacao__usuario=request.user)
    return render(request, 'minhas_solicitacoes.html', {'solicitacoes': solicitacoes, 'efetivadas': efetivadas})


@login_required
@user_passes_test(is_member_of_team)
def editar_muda(request, muda_id):
    muda = get_object_or_404(Muda, pk=muda_id)
    if request.method == 'POST':
        form = MudaForm(request.POST, instance=muda)
        if form.is_valid():
            form.save()
            return redirect('listar_mudas')
    else:
        form = MudaForm(instance=muda)
    return render(request, 'editar_muda.html', {'form': form, 'muda': muda})


@login_required
@user_passes_test(is_member_of_team)
def excluir_muda(request, muda_id):
    muda = get_object_or_404(Muda, pk=muda_id)
    if request.method == 'POST':
        muda.delete()
        return redirect('listar_mudas')
    return render(request, 'excluir_muda.html', {'muda': muda})
