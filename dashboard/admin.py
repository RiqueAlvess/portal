from django.contrib import admin
from .models import Empresa, UsuarioEmpresa, EmpresaAtivaUsuario
from funcionarios.models import Funcionario

class UsuarioEmpresaInline(admin.TabularInline):
    model = UsuarioEmpresa
    extra = 1

class FuncionarioInline(admin.TabularInline):
    model = Funcionario
    fields = ['CODIGO', 'NOME', 'CPF', 'SITUACAO']
    readonly_fields = ['CODIGO', 'NOME', 'CPF', 'SITUACAO']
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "Funcionário"
    verbose_name_plural = "Funcionários"

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('CODIGO', 'RAZAOSOCIAL', 'CIDADE', 'UF', 'CNPJ', 'ATIVO')
    list_filter = ('ATIVO', 'UF', 'CIDADE')
    search_fields = ('CODIGO', 'RAZAOSOCIAL', 'CNPJ')
    inlines = [UsuarioEmpresaInline, FuncionarioInline]

@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'data_vinculo')
    list_filter = ('data_vinculo',)
    search_fields = ('usuario__username', 'empresa__RAZAOSOCIAL')

@admin.register(EmpresaAtivaUsuario)
class EmpresaAtivaUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa')
    search_fields = ('usuario__username', 'empresa__RAZAOSOCIAL')
    list_filter = ('empresa',)
