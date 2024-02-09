from django.contrib import admin
from .models import Muda, EfetivarDoacao, SolicitacaoDoacao, UserProfile, EspecieQuantidade, DoacaoAvulso


admin.site.register(Muda)
admin.site.register(EfetivarDoacao)
admin.site.register(SolicitacaoDoacao)
admin.site.register(UserProfile)
admin.site.register(DoacaoAvulso)
admin.site.register(EspecieQuantidade)
