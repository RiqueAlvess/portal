from django.contrib import admin
from .models import Empresa, UsuarioEmpresa

class UsuarioEmpresaInline(admin.TabularInline):
    model = UsuarioEmpresa
    extra = 1

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('CODIGO', 'RAZAOSOCIAL', 'CIDADE', 'UF', 'CNPJ', 'ATIVO')
    list_filter = ('ATIVO', 'UF', 'CIDADE')
    search_fields = ('CODIGO', 'RAZAOSOCIAL', 'CNPJ')
    inlines = [UsuarioEmpresaInline]

@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'data_vinculo')
    list_filter = ('data_vinculo',)
    search_fields = ('usuario__username', 'empresa__RAZAOSOCIAL')