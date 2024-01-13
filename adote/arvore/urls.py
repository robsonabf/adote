from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('mudas/', views.lista_mudas, name='lista_mudas'),
    path('mudas/<int:muda_id>/', views.detalhes_muda, name='detalhes_muda'),
    path('mudas/<int:muda_id>/editar/', views.editar_muda, name='editar_muda'),
    path('mudas/<int:muda_id>/excluir/', views.excluir_muda, name='excluir_muda'),
    path('signup/', views.signup, name='signup'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('adicionar_muda/', views.adicionar_muda, name='adicionar_muda'),
    path('solicitar_doacao/', views.solicitar_doacao, name='solicitar_doacao'),
    path('listar_solicitacoes/', views.listar_solicitacoes, name='listar_solicitacoes'),
    path('aprovar_reprovar_doacao/<int:solicitacao_id>/', views.aprovar_reprovar_doacao, name='aprovar_reprovar_doacao'),
    path('minhas_solicitacoes/', views.minhas_solicitacoes, name='minhas_solicitacoes'),
]
