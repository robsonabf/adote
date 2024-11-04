from itertools import chain, groupby
import datetime
from datetime import timedelta, timezone
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from reportlab.platypus import Image, PageTemplate
from rest_framework.authentication import TokenAuthentication
import shutil
import os
from reportlab.lib.pagesizes import landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
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
from django.http import HttpResponse, JsonResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from rest_framework import status, permissions
import io
from django.conf import settings
#API
from .serializers import UserSerializer, UserProfileSerializer, SolicitacaoDoacaoSerializer, MudaSerializer
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
def dados(request):
    dados_estatisticos = obter_dados_estatisticos()
    lista_por_mes = obter_doacoes_ultimos_meses()
    return render(request, 'dados.html',
                  {'dados_estatisticos': dados_estatisticos, 'lista_mes': lista_por_mes['lista_por_mes']})


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
    # Realize a consulta no banco de dados
    resultados = DoacaoAvulso.objects.all()

    # Configurações para a orientação da página (paisagem)
    width, height = landscape(A4)

    # Inicie o buffer do PDF
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=(width, height))

    # Lista para armazenar os dados dos resultados
    data = []

    # Adicione os resultados à lista de dados
    for resultado in resultados:
        data.append([
            Paragraph(resultado.nome_completo, ParagraphStyle(name='Normal', fontSize=10, leading=12, wordWrap='CJK')),
            Paragraph(resultado.endereco, ParagraphStyle(name='Normal', fontSize=10, leading=12, wordWrap='CJK')),
            Paragraph(resultado.cidade, ParagraphStyle(name='Normal', fontSize=10, leading=12, wordWrap='CJK')),
            Paragraph(resultado.estado, ParagraphStyle(name='Normal', fontSize=10, leading=12, wordWrap='CJK')),
            Paragraph(resultado.telefone, ParagraphStyle(name='Normal', fontSize=10, leading=12, wordWrap='CJK')),
            Paragraph(resultado.data_plantio.strftime('%d/%m/%Y'), ParagraphStyle(name='Normal', fontSize=10, leading=12, wordWrap='CJK')),
            Paragraph(resultado.data_adocao.strftime('%d/%m/%Y'), ParagraphStyle(name='Normal', fontSize=10, leading=12, wordWrap='CJK')),
            Paragraph(resultado.local_de_plantio, ParagraphStyle(name='Normal', fontSize=10, leading=12, wordWrap='CJK')),
            Paragraph(resultado.observacoes, ParagraphStyle(name='Normal', fontSize=10, leading=12, wordWrap='CJK'))
        ])

    # Adicione o título à lista de dados
    header = [
        'Nome Completo',
        'Endereço',
        'Cidade',
        'Estado',
        'Telefone',
        'Data de Plantio',
        'Data de Adoção',
        'Local de Plantio',
        'Observações'
    ]
    data.insert(0, header)

    # Crie a tabela com os dados
    table = Table(data)

    # Estilo da tabela
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

    # Aplicar estilo à tabela
    table.setStyle(style)

    # Adicione a tabela ao documento PDF
    elements = [table]


    # Adicione o título ao documento PDF
    title = 'Relatório de Doações Avulsas'
    title_style = ParagraphStyle(name='Title', fontSize=16, alignment=1, spaceAfter=20)  # Adiciona espaço após o título
    title_paragraph = Paragraph(title, title_style)
    elements.insert(0, title_paragraph)

    # Desenhe as imagens no cabeçalho do PDF
    def draw_header(canvas, doc):
        # Adicione as logos
        logo_left_path = str(settings.STATIC_ROOT) + '/logo1.png'
        logo_right_path = str(settings.STATIC_ROOT) + '/adote.jpg'

        canvas.drawImage(logo_left_path, 50, height - 50 - 20, width=100, height=50, preserveAspectRatio=True)
        canvas.drawImage(logo_right_path, width - 150, height - 50 - 20, width=100, height=50, preserveAspectRatio=True)
    # Construa o PDF
    pdf.build(elements, onFirstPage=draw_header)

    # Volte para o início do buffer antes de enviar a resposta
    buffer.seek(0)

    # Configurações para a resposta
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="relatorio_doacao_avulso.pdf"'

    # Envie o conteúdo do buffer como resposta
    response.write(buffer.getvalue())
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
    data_atual = timezone.now()

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
            token, created = Token.objects.get_or_create(user=user)
            print(token.key)

            # Retorne a resposta JSON com o token (ou qualquer outra informação necessária)
            return Response({
                'message': 'Autenticação bem-sucedida',
                'token': token.key
            }, status=status.HTTP_200_OK)
        else:
            # Caso as credenciais sejam inválidas
            return Response({'error': 'Credenciais inválidas'}, status=status.HTTP_401_UNAUTHORIZED)


class RegisterView(APIView):
    def post(self, request):
        user_serializer = UserSerializer(data=request.data)

        try:
            if user_serializer.is_valid():
                user = user_serializer.save()

                token, created = Token.objects.get_or_create(user=user)

                return Response({
                    'message': 'Registro bem-sucedido',
                    'token': token.key
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            message = f"Erro ao registrar usuário: {e}"
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@permission_classes([IsAuthenticated])
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


@login_required
@user_passes_test(is_member_of_team)
def fazer_backup(request):
    # Diretório de backup
    backup_dir = '../backups/'

    # Diretório do arquivo atual
    current_dir = os.path.dirname(__file__)

    # Caminho para o arquivo do banco de dados SQLite3
    db_file = os.path.join(current_dir, '..', 'db.sqlite3')
    # Limite de quantidade de backups
    max_backups = 5

    # Verifica se o arquivo do banco de dados existe
    if os.path.exists(db_file):
        # Cria o diretório de backup, se não existir
        os.makedirs(backup_dir, exist_ok=True)
        os.chmod(backup_dir, 0o777)

        # Nome do arquivo de backup com timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f'backup_{timestamp}.sqlite3'
        backup_path = os.path.join(backup_dir, backup_filename)

        # Copia o arquivo do banco de dados para o diretório de backup
        def copy_and_set_permissions(src, dst):
            # Copia o arquivo
            shutil.copy2(src, dst)
            os.chmod(dst, 0o777)

        copy_and_set_permissions(db_file, backup_path)

        # Verifica se o diretório de backup existe
        if os.path.exists(backup_dir):
            # Lista os arquivos no diretório de backup
            backups = [os.path.join(backup_dir, file) for file in os.listdir(backup_dir)]
            # Remove backups antigos se necessário
            if len(backups) > max_backups:
                # Ordena os backups pelo tempo de modificação (ou criação, se preferir)
                backups = sorted(backups, key=os.path.getmtime)

                # Verifica se os backups além do limite máximo são os mais antigos
                oldest_backups = backups[:len(backups) - max_backups]
                for old_backup in oldest_backups:
                    os.remove(old_backup)
        else:
            print(f'O diretório de backup "{backup_dir}" não existe.')


        # Download do backup
        with open(backup_path, 'rb') as backup_file:
            response = HttpResponse(backup_file.read(), content_type='application/x-sqlite3')
            response['Content-Disposition'] = f'attachment; filename="{backup_filename}"'
            return response
    else:
        messages.error(request, 'Arquivo de banco de dados não encontrado.')
        return redirect(request.META.get('HTTP_REFERER', 'index'))


class MudaListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        mudas = Muda.objects.all()
        serializer = MudaSerializer(mudas, many=True)
        return Response(serializer.data)


class SolicitarDoacaoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SolicitacaoDoacaoSerializer(data=request.data)
        if serializer.is_valid():
            # Cria a solicitação de doação com o usuário e a data da solicitação
            solicitacao = serializer.save(usuario=request.user, data_solicitacao=timezone.now())
            return Response({
                'message': 'Solicitação de doação realizada com sucesso!',
                'data': {
                    'id': solicitacao.id,
                    'usuario': solicitacao.usuario.username,
                    'especie': solicitacao.especie,
                    'quantidade_solicitada': solicitacao.quantidade_solicitada,
                    'local_de_plantio': solicitacao.local_de_plantio,
                    'status': solicitacao.status,
                    'data_solicitacao': solicitacao.data_solicitacao,
                    'observacoes': solicitacao.observacoes
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk, *args, **kwargs):
        try:
            solicitacao = SolicitacaoDoacao.objects.get(pk=pk, usuario=request.user)

            if solicitacao.status != 'Pendente':
                return Response({'error': 'Apenas solicitações pendentes podem ser editadas.'},
                                status=status.HTTP_400_BAD_REQUEST)

            serializer = SolicitacaoDoacaoSerializer(solicitacao, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except SolicitacaoDoacao.DoesNotExist:
            return Response({'error': 'Solicitação não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, *args, **kwargs):
        try:
            solicitacao = SolicitacaoDoacao.objects.get(pk=pk, usuario=request.user)

            if solicitacao.status != 'Pendente':
                return Response({'error': 'Apenas solicitações pendentes podem ser excluídas.'},
                                status=status.HTTP_400_BAD_REQUEST)

            solicitacao.delete()
            return Response({'message': 'Solicitação excluída com sucesso.'}, status=status.HTTP_204_NO_CONTENT)

        except SolicitacaoDoacao.DoesNotExist:
            return Response({'error': 'Solicitação não encontrada.'}, status=status.HTTP_404_NOT_FOUND)


@permission_classes([IsAuthenticated])
def api_dados_estatisticos(request):
    dados_estatisticos = obter_dados_estatisticos()
    lista_por_mes = obter_doacoes_ultimos_meses()
    response_data = {
        'dados_estatisticos': dados_estatisticos,
        'lista_mes': lista_por_mes['lista_por_mes']
    }
    return JsonResponse(response_data)
