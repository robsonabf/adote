from datetime import datetime, timedelta, timezone
from itertools import chain, groupby
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from rest_framework.authentication import TokenAuthentication

from .forms import CustomUserCreationForm, DoacaoAvulsoForm, MudaForm, SolicitacaoDoacaoForm, DoacaoAvulsoForm2
from .models import Muda, SolicitacaoDoacao, EfetivarDoacao, UserProfile, EspecieQuantidade
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Subquery, OuterRef
from django.db.models.functions import ExtractYear, ExtractMonth
from .models import DoacaoAvulso
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from rest_framework import viewsets, serializers, views, status, permissions
import io
#API
from .serializers import UserSerializer, UserProfileSerializer, SolicitacaoDoacaoSerializer
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated


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
    lista_por_mes = obter_doacoes_ultimos_meses()
    return render(request, 'admin_dashboard.html', {'dados_estatisticos': dados_estatisticos, 'lista_mes': lista_por_mes['lista_por_mes']})


def obter_dados_estatisticos():
    # Contagem por ano de doações e não de quantidade de mudas doadas por ano
    # Contagem por ano em EfetivarDoacao
    dados_por_ano_efetivar = EfetivarDoacao.objects.annotate(ano=ExtractYear('data_efetivacao')).values('ano').annotate(
        count=Count('ano'))

    # Contagem por ano em DoacaoAvulsa
    dados_por_ano_avulsa = DoacaoAvulso.objects.annotate(ano=ExtractYear('data_adocao')).values('ano').annotate(
        count=Count('ano'))

    # Combine os resultados das duas consultas
    dados_por_ano = list(chain(dados_por_ano_efetivar, dados_por_ano_avulsa))

    # Agrupe os resultados por ano e calcule a soma das contagens
    dados_agrupados_por_ano = {}
    for item in dados_por_ano:
        ano = item['ano']
        count = item['count']
        if ano in dados_agrupados_por_ano:
            if isinstance(dados_agrupados_por_ano[ano], int):
                dados_agrupados_por_ano[ano] += count
            else:
                dados_agrupados_por_ano[ano] = count
        else:
            dados_agrupados_por_ano[ano] = count


        # Consulta para somar as quantidades por ano em EspecieQuantidade
        # Somatório por ano em EfetivarDoacao
    soma_por_ano_efetivar = EfetivarDoacao.objects.annotate(ano=ExtractYear('data_efetivacao')).values(
    'ano').annotate(somatorio_efetivar=Sum('quantidade_efetivada'))

    soma_por_ano_especie = (
    EspecieQuantidade.objects.filter(doacao__data_adocao__isnull=False)
    .annotate(ano=ExtractYear('doacao__data_adocao')).values('ano').annotate(somatorio_especie=Sum('quantidade')))

    # Combine os resultados das duas consultas
    dados_por_ano_soma = list(chain(soma_por_ano_efetivar, soma_por_ano_especie))
    # Agrupe os resultados por ano e calcule a soma das contagens
    dados_agrupados_por_ano_soma = {}
    for item in dados_por_ano_soma:
        ano = item['ano']
        somatorio_efetivar = item.get('somatorio_efetivar', 0)
        somatorio_especie = item.get('somatorio_especie', 0)

        if ano in dados_agrupados_por_ano_soma:
            # Se existir, adicione os valores
            dados_agrupados_por_ano_soma[ano]['somatorio_efetivar'] = dados_agrupados_por_ano_soma[ano].get(
            'somatorio_efetivar', 0) + somatorio_efetivar
            dados_agrupados_por_ano_soma[ano]['somatorio_especie'] = dados_agrupados_por_ano_soma[ano].get(
            'somatorio_especie', 0) + somatorio_especie
        else:
            # Se não existir, crie um novo registro
            dados_agrupados_por_ano_soma[ano] = {'somatorio_efetivar': somatorio_efetivar,
                                                 'somatorio_especie': somatorio_especie,
                }

    # Contagem por espécie
    # Contagem por espécie com somatório de quantidade (EspecieQuantidade)
    dados_por_especie_quantidade = EspecieQuantidade.objects.values('especie').annotate(
        quantidade=Sum('quantidade')
    )

    # Contagem por espécie doada com somatório de quantidade (EfetivarDoacao)
    dados_por_especie_doada = EfetivarDoacao.objects.values('especie_doada').annotate(
        quantidade_efetivada=Sum('quantidade_efetivada')
    )
    # Mesclar as duas listas por 'especie'
    especies_combined = {}

    for k, v in groupby(sorted(dados_por_especie_quantidade, key=lambda x: x['especie']), key=lambda x: x['especie']):
        especies_combined[k] = {'quantidade': sum(item['quantidade'] for item in v), 'quantidade_efetivada': 0}

    for item in dados_por_especie_doada:
        especie = item['especie_doada']
        if especie in especies_combined:
            especies_combined[especie]['quantidade_efetivada'] = item['quantidade_efetivada']
        else:
            especies_combined[especie] = {'quantidade': 0, 'quantidade_efetivada': item['quantidade_efetivada']}

    # Contagem por status de solicitação
    dados_por_tipo_solicitacao = SolicitacaoDoacao.objects.values('status').annotate(count=Count('status'))
    # Contagem por especie de solicitação
    dados_por_especie_solicitacao = SolicitacaoDoacao.objects.values('especie').annotate(count=Count('especie'))

    # Convertendo os resultados para listas
    lista_por_ano = [{'ano': ano, 'count': count} for ano, count in dados_agrupados_por_ano.items()]
    lista_por_soma = [
        {'ano': ano, 'somatorio_efetivar': item['somatorio_efetivar'], 'somatorio_especie': item['somatorio_especie']}
        for ano, item in dados_agrupados_por_ano_soma.items()]

    lista_por_especie_combined = [{'especie': k, **v} for k, v in especies_combined.items()]
    lista_por_tipo_solicitacao = list(dados_por_tipo_solicitacao)
    lista_por_especie_solicitacao = list(dados_por_especie_solicitacao)

    return {'por_ano': lista_por_ano, 'por_soma': lista_por_soma, 'por_especie': lista_por_especie_combined,
            'por_tipo_solicitacao': lista_por_tipo_solicitacao, 'por_especie_solicitacao': lista_por_especie_solicitacao}


@login_required
@user_passes_test(is_member_of_team)
def adicionar_muda(request):
    if request.method == 'POST':
        form = MudaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Adicionada com sucesso!')
            return redirect('adicionar_muda')  # Redirecionar para a página do dashboard
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
    # Paginação para as solicitações pendentes
    paginator_pendentes = Paginator(solicitacoes.filter(status='Pendente'), 10)
    page_pendentes = request.GET.get('page_pendentes')
    try:
        solicitacoes_pendentes = paginator_pendentes.page(page_pendentes)
    except PageNotAnInteger:
        solicitacoes_pendentes = paginator_pendentes.page(1)
    except EmptyPage:
        solicitacoes_pendentes = paginator_pendentes.page(paginator_pendentes.num_pages)

    # Paginação para as solicitações aprovadas
    paginator_aprovadas = Paginator(efetivadas.filter(solicitacao__status='Aprovada'), 10)
    page_aprovadas = request.GET.get('page_aprovadas')
    try:
        solicitacoes_aprovadas = paginator_aprovadas.page(page_aprovadas)
    except PageNotAnInteger:
        solicitacoes_aprovadas = paginator_aprovadas.page(1)
    except EmptyPage:
        solicitacoes_aprovadas = paginator_aprovadas.page(paginator_aprovadas.num_pages)

    # Paginação para as solicitações reprovadas
    paginator_reprovadas = Paginator(solicitacoes.filter(status='Reprovada'), 10)
    page_reprovadas = request.GET.get('page_reprovadas')
    try:
        solicitacoes_reprovadas = paginator_reprovadas.page(page_reprovadas)
    except PageNotAnInteger:
        solicitacoes_reprovadas = paginator_reprovadas.page(1)
    except EmptyPage:
        solicitacoes_reprovadas = paginator_reprovadas.page(paginator_reprovadas.num_pages)

    return render(request, 'listar_solicitacoes.html', {
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'solicitacoes_aprovadas': solicitacoes_aprovadas,
        'solicitacoes_reprovadas': solicitacoes_reprovadas,
    })


@login_required
@user_passes_test(is_member_of_team)
def listar_doacoes(request):
    doacoes_list = DoacaoAvulso.objects.prefetch_related('especiequantidade_set').all()
    paginator = Paginator(doacoes_list, 5)  # Mostrar 10 doações por página

    page = request.GET.get('page')
    try:
        doacoes = paginator.page(page)
    except PageNotAnInteger:
        # Se a página não for um inteiro, exibir a primeira página
        doacoes = paginator.page(1)
    except EmptyPage:
        # Se a página estiver fora do intervalo (e.g., 9999), exibir a última página
        doacoes = paginator.page(paginator.num_pages)

    return render(request, 'lista_doacoes.html', {'doacoes': doacoes})


@login_required
@user_passes_test(is_member_of_team)
def detalhes_doacao(request, pk):
    doacao = get_object_or_404(DoacaoAvulso, pk=pk)
    especies_quantidades = doacao.especiequantidade_set.all()
    return render(request, 'detalhes_doacao.html', {'doacao': doacao, 'especies_quantidades': especies_quantidades})


@login_required
@user_passes_test(is_member_of_team)
def criar_doacao(request):
    if request.method == 'POST':
        form = DoacaoAvulsoForm(request.POST)

        if form.is_valid():
            doacao = form.save(commit=False)
            doacao.funcionario = request.user
            doacao.save()

            especies_quantidades_raw = request.POST.getlist('especies_quantidades[]')
            especies_quantidades = [item.split('|') for item in especies_quantidades_raw]

            for especie_quantidade in especies_quantidades:
                especie, quantidade = especie_quantidade
                EspecieQuantidade.objects.create(doacao=doacao, especie=especie, quantidade=quantidade)

            return redirect('lista_doacoes')
    else:
        form = DoacaoAvulsoForm()

    return render(request, 'criar_doacao.html', {'form': form})


@login_required
@user_passes_test(is_member_of_team)
def editar_doacao(request, pk):
    doacao = get_object_or_404(DoacaoAvulso, pk=pk)

    if request.method == 'POST':
        form = DoacaoAvulsoForm2(request.POST, instance=doacao)

        if form.is_valid():
            doacao = form.save(commit=False)
            doacao.funcionario = request.user
            doacao.save()

            # Limpa as instâncias antigas antes de adicionar as novas
            doacao.especiequantidade_set.all().delete()

            especies_quantidades_raw = request.POST.getlist('especies_quantidades[]')

            for especie_quantidade_str in especies_quantidades_raw:
                especie, quantidade = especie_quantidade_str.split('|')
                EspecieQuantidade.objects.create(doacao=doacao, especie=especie, quantidade=quantidade)

            return redirect('detalhes_doacao', pk=pk)
    else:
        form = DoacaoAvulsoForm2(instance=doacao)

    return render(request, 'editar_doacao.html', {'form': form, 'doacao': doacao})


@login_required
@user_passes_test(is_member_of_team)
def excluir_doacao(request, pk):
    doacao = get_object_or_404(DoacaoAvulso, pk=pk)

    if request.method == 'POST':
        # Excluir os registros de EspecieQuantidade associados à DoacaoAvulso
        doacao.especiequantidade_set.all().delete()

        # Em seguida, exclua a DoacaoAvulso
        doacao.delete()

        # Redirecione para a página de lista após a exclusão
        return redirect('lista_doacoes')

    return render(request, 'excluir_doacao.html', {'doacao': doacao})


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
            return redirect('lista_mudas')
    else:
        form = MudaForm(instance=muda)
    return render(request, 'editar_muda.html', {'form': form, 'muda': muda})


@login_required
@user_passes_test(is_member_of_team)
def excluir_muda(request, muda_id):
    muda = get_object_or_404(Muda, pk=muda_id)
    if request.method == 'POST':
        muda.delete()
        return redirect('lista_mudas')
    return render(request, 'excluir_muda.html', {'muda': muda})


@login_required
@user_passes_test(is_member_of_team)
def pesquisar_adotantes(request):
    resultados = []

    if 'q' in request.GET:
        query = request.GET['q']

        # Consultar DoacaoAvulso
        doacoes_avulso = DoacaoAvulso.objects.filter(nome_completo__icontains=query)
        resultados += [
            {
                'tipo': 'DoacaoAvulso',
                'nome_completo': doacao.nome_completo,
                'especies_quantidades': [
                    {'especie': especie_quantidade.especie, 'quantidade': especie_quantidade.quantidade}
                    for especie_quantidade in doacao.especiequantidade_set.all()
                ],
            }
            for doacao in doacoes_avulso
        ]

        # Consultar EfetivarDoacao através da solicitação
        efetivacoes = EfetivarDoacao.objects.filter(solicitacao__usuario__username__icontains=query)
        resultados += [
            {
                'tipo': 'EfetivarDoacao',
                'nome_completo': (
                    efetivacao.solicitacao.usuario.userprofile.nome_completo
                    if hasattr(efetivacao.solicitacao.usuario, 'userprofile')
                    else None
                ),
                'especie_doada': efetivacao.especie_doada,
                'quantidade_efetivada': efetivacao.quantidade_efetivada,
            }
            for efetivacao in efetivacoes
        ]

    return render(request, 'pesquisar_adotantes.html', {'resultados': resultados})


@login_required
@user_passes_test(is_member_of_team)
def consulta_e_gera_pdf(request):
    # Realize a consulta no banco de dados aqui
    resultados = DoacaoAvulso.objects.all()

    # Inicie o buffer do PDF
    # Configurações para o tamanho da página
    width, height = 595, 842  # Tamanho padrão da página A4 em pontos
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=(width, height))

    # Adicione os resultados ao PDF
    for resultado in resultados:
        p.drawString(100, 800, f"Nome Completo: {resultado.nome_completo}")
        p.drawString(100, 780, f"Endereço: {resultado.endereco}")
        p.drawString(100, 760, f"Cidade: {resultado.cidade}")
        p.drawString(100, 740, f"Estado: {resultado.estado}")
        p.drawString(100, 720, f"Telefone: {resultado.telefone}")
        p.drawString(100, 700, f"Data de Plantio: {resultado.data_plantio}")
        p.drawString(100, 680, f"Data de Adoção: {resultado.data_adocao}")
        p.drawString(100, 660, f"Local de Plantio: {resultado.local_de_plantio}")
        p.drawString(100, 640, f"Observações: {resultado.observacoes}")

        p.showPage()  # Adicione uma nova página para cada resultado
        # Conclua o PDF
    p.save()

    # Volte para o início do buffer antes de enviar a resposta
    buffer.seek(0)

    # Configurações para a resposta
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="relatorio_doacao_avulso.pdf"'

    # Envie o conteúdo do buffer como resposta
    response.write(buffer.read())
    return response


def obter_doacoes_ultimos_meses():
    # Mapeie números de mês para nomes de mês
    meses = {
        1: 'Janeiro',
        2: 'Fevereiro',
        3: 'Março',
        4: 'Abril',
        5: 'Maio',
        6: 'Junho',
        7: 'Julho',
        8: 'Agosto',
        9: 'Setembro',
        10: 'Outubro',
        11: 'Novembro',
        12: 'Dezembro',
    }
    # Obtém a data atual
    data_atual = datetime.now()

    # Calcula a data há 6 meses atrás
    data_inicio = timezone.now() - timedelta(days=180)

    # Consulta as doações efetivadas nos últimos 6 meses
    doacoes_efetivadas = EfetivarDoacao.objects.filter(
        data_efetivacao__gte=data_inicio,
        data_efetivacao__lte=data_atual
    ).annotate(mes=ExtractMonth('data_efetivacao')).values('mes').annotate(
        count=Count('mes'),
        somatorio=Sum('quantidade_efetivada')
    )
    # Consulta as doações avulsas nos últimos 6 meses
    doacoes_avulsas = EspecieQuantidade.objects.filter(
        doacao__data_adocao__gte=data_inicio,
        doacao__data_adocao__lte=data_atual
    ).annotate(
        doacao_avulso_id=Subquery(
            DoacaoAvulso.objects.filter(
                id=OuterRef('doacao_id')
            ).values('id')[:1]
        )
    ).values(mes=ExtractMonth('doacao__data_adocao')).annotate(
        count=Count('doacao_avulso_id', distinct=True),
        somatorio=Sum('quantidade')
    )

    # Combine os resultados das duas consultas
    dados_por_mes = list(chain(doacoes_efetivadas, doacoes_avulsas))
    # Agrupe os resultados por mês e calcule a soma das contagens
    dados_agrupados_por_mes = {}
    for item in dados_por_mes:
        mes_numero = item['mes']
        mes_nome = meses.get(mes_numero, mes_numero)
        count = item['count']
        somatorio = item.get('somatorio', 0)

        if mes_nome in dados_agrupados_por_mes:
            # Incrementa os valores existentes
            dados_agrupados_por_mes[mes_nome]['count'] += count
            dados_agrupados_por_mes[mes_nome]['somatorio'] += somatorio
        else:
            # Adiciona um novo registro para o mês
            dados_agrupados_por_mes[mes_nome] = {
                'count': count,
                'somatorio': somatorio,
            }
    # Convertendo os resultados para listas
    lista_por_mes = [
        {'mes': mes_nome, 'count': dados_agrupados_por_mes[mes_nome]['count'],
         'somatorio': dados_agrupados_por_mes[mes_nome]['somatorio']} for mes_numero, mes_nome in meses.items()
        if mes_nome in dados_agrupados_por_mes
    ]
    return {'lista_por_mes': lista_por_mes}


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user is not None:
            # Faça login no usuário, se a autenticação for bem-sucedida
            login(request, user)

            #CASO NÃO ESTEJA UTILIZANDO O AUTOTOKEN DO DRF, PODE IMPLEMENTAR MANUALMENTE COM OUTRAS CONFIGURAÇÕES
            # Crie ou obtenha o token de autenticação
            #token, created = Token.objects.get_or_create(user=user)

            # Retorne a resposta JSON com o token (ou qualquer outra informação necessária)
            return Response({'message': 'Autenticação bem-sucedida'}, status=status.HTTP_200_OK)
        else:
            # Caso as credenciais sejam inválidas
            return Response({'error': 'Credenciais inválidas'}, status=status.HTTP_401_UNAUTHORIZED)


class RegisterView(APIView):
    def post(self, request):
        user_serializer = UserSerializer(data=request.data)
        profile_serializer = UserProfileSerializer(data=request.data.get('profile', {}))
        try:
            if user_serializer.is_valid() and profile_serializer.is_valid():
                user = user_serializer.save()
                # Crie um token para o usuário recém-registrado (opcional)
                Token.objects.create(user=user)

                return Response({'message': 'Registro bem-sucedido'}, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            # Em caso de violação de unicidade (UserProfile duplicado), emita uma mensagem
            message = f"Erro ao registrar usuário: {e}"
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'error': 'Falha no registro'}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Invalida o token de autenticação, forçando o usuário a fazer login novamente
        request.auth.delete()
        return Response({'message': 'Logout bem-sucedido'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def api_listar_solicitacoes(request):
    if request.method == 'GET':
        solicitacoes = SolicitacaoDoacao.objects.filter(usuario=request.user)
        serializer = SolicitacaoDoacaoSerializer(solicitacoes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response({'error': 'Método não permitido'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
