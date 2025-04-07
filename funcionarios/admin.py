# funcionarios/admin.py
from django.contrib import admin
from .models import Funcionario

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('CODIGO', 'NOME', 'CODIGOEMPRESA', 'NOMEEMPRESA', 'CPF', 'SITUACAO')
    list_filter = ('CODIGOEMPRESA', 'SITUACAO', 'SEXO', 'ESTADOCIVIL')
    search_fields = ('CODIGO', 'NOME', 'CPF', 'RG', 'EMAIL')
    fieldsets = (
        ('Informações da Empresa', {
            'fields': ('empresa',)
        }),
        ('Informações Básicas', {
            'fields': ('CODIGO', 'NOME', 'CPF', 'SEXO', 'DATA_NASCIMENTO', 'DATA_ADMISSAO')
        }),
        ('Informações Organizacionais', {
            'fields': ('CODIGOUNIDADE', 'NOMEUNIDADE', 'CODIGOSETOR', 'NOMESETOR', 'CODIGOCARGO', 'NOMECARGO', 'CBOCARGO', 'CCUSTO', 'NOMECENTROCUSTO'),
            'classes': ('collapse',)
        }),
        ('Documentação', {
            'fields': ('RG', 'UFRG', 'ORGAOEMISSORRG', 'PIS', 'CTPS', 'SERIECTPS'),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('DATA_DEMISSAO', 'DATAULTALTERACAO'),
            'classes': ('collapse',)
        }),
        ('Contato', {
            'fields': ('ENDERECO', 'NUMERO_ENDERECO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'TELEFONERESIDENCIAL', 'TELEFONECELULAR', 'EMAIL', 'TELCOMERCIAL', 'RAMAL'),
            'classes': ('collapse',)
        }),
        ('Outras Informações', {
            'fields': ('MATRICULAFUNCIONARIO', 'MATRICULARH', 'SITUACAO', 'TIPOCONTATACAO', 'DEFICIENTE', 'DEFICIENCIA', 'NM_MAE_FUNCIONARIO', 'COR', 'ESCOLARIDADE', 'NATURALIDADE', 'REGIMEREVEZAMENTO', 'REGIMETRABALHO', 'TURNOTRABALHO', 'ESTADOCIVIL'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if obj.empresa:
            obj.CODIGOEMPRESA = obj.empresa.CODIGO
            obj.NOMEEMPRESA = obj.empresa.RAZAOSOCIAL
        super().save_model(request, obj, form, change)