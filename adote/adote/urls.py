from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    path('', include('arvore.urls')),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(template_name='logout.html'), name='logout'),
    path('accounts/profile/', auth_views.LoginView.as_view(redirect_authenticated_user=True), name='profile'),
]

# Restringir acesso para membros da equipe
admin.site.site_header = 'Área Administrativa - Adoção de Mudas'
admin.site.site_title = 'Administração'
admin.site.index_title = 'Bem-vindo à Área Administrativa'
