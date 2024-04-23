from django.urls import path
from . import views
from .views import RegisterView, LoginView, LogoutView
from rest_framework.authtoken.views import obtain_auth_token
from .views import api_listar_solicitacoes


urlpatterns = [
    path('', views.index, name='index'),
    path('mudas/', views.lista_mudas, name='lista_mudas'),
    path('mudas/<int:muda_id>/', views.detalhes_muda, name='detalhes_muda'),
    path('mudas/<int:muda_id>/editar/', views.editar_muda, name='editar_muda'),
    path('mudas/<int:muda_id>/excluir/', views.excluir_muda, name='excluir_muda'),
    #CADASTRO
    path('signup/', views.signup, name='signup'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('adicionar_muda/', views.adicionar_muda, name='adicionar_muda'),
    path('solicitar_doacao/', views.solicitar_doacao, name='solicitar_doacao'),
    path('listar_solicitacoes/', views.listar_solicitacoes, name='listar_solicitacoes'),
    path('aprovar_reprovar_doacao/<int:solicitacao_id>/', views.aprovar_reprovar_doacao, name='aprovar_reprovar_doacao'),
    path('minhas_solicitacoes/', views.minhas_solicitacoes, name='minhas_solicitacoes'),
    path('doacoes/', views.listar_doacoes, name='lista_doacoes'),
    path('doacoes/alterar/<int:pk>/', views.editar_doacao, name='alterar_doacao'),
    path('doacoes/excluir/<int:pk>/', views.excluir_doacao, name='excluir_doacao'),
    path('doacoes/<int:pk>/', views.detalhes_doacao, name='detalhes_doacao'),
    path('doacoes/criar/', views.criar_doacao, name='criar_doacao'),
    path('pesquisar_adotantes/', views.pesquisar_adotantes, name='pesquisar_adotantes'),
    path('consulta_e_gera_pdf/', views.consulta_e_gera_pdf, name='consulta_e_gera_pdf'),
    path('fazer_backup/', views.fazer_backup, name='fazer_backup'),
    #ROTAS DA API REST
    path('api/login/', LoginView.as_view(), name='api_login'),
    path('api/token/', obtain_auth_token, name='api_token'),
    path('api/register/', RegisterView.as_view(), name='api_register'),
    path('api/logout/', LogoutView.as_view(), name='api_logout'),
    path('api/listar_solicitacoes/', api_listar_solicitacoes, name='api_listar_solicitacoes'),
]
