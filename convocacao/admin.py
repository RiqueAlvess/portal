from django.contrib import admin
from .models import Convocacao

@admin.register(Convocacao)
class ConvocacaoAdmin(admin.ModelAdmin):
    list_display = (
        'NOME', 
        'EXAME', 
        'get_status', 
        'ULTIMOPEDIDO', 
        'DATARESULTADO', 
        'REFAZER', 
        'empresa_nome'
    )
    
    list_filter = (
        'empresa__RAZAOSOCIAL',
        'SETOR',
        'EXAME',
    )
    
    search_fields = (
        'NOME',
        'CPFFUNCIONARIO',
        'MATRICULA',
        'EXAME',
        'funcionario__NOME',
    )
    
    autocomplete_fields = ['empresa', 'funcionario']
    
    fieldsets = (
        ('Empresa e Local', {
            'fields': (
                'empresa',
                'NOMEABREVIADO',
                'UNIDADE',
                'CIDADE',
                'ESTADO',
                'BAIRRO',
                'ENDERECO',
                'CEP',
                'CNPJUNIDADE',
            )
        }),
        ('Funcionário', {
            'fields': (
                'funcionario',
                'SETOR',
                'CARGO',
            )
        }),
        ('Dados do Exame', {
            'fields': (
                'CODIGOEXAME',
                'EXAME',
                'ULTIMOPEDIDO',
                'DATARESULTADO',
                'PERIODICIDADE',
                'REFAZER',
            )
        }),
    )
    
    readonly_fields = (
        'CODIGOEMPRESA', 
        'CODIGOFUNCIONARIO',
        'NOME',
        'CPFFUNCIONARIO',
        'MATRICULA',
        'DATAADMISSAO',
        'EMAILFUNCIONARIO',
        'TELEFONEFUNCIONARIO',
    )
    
    def get_status(self, obj):
        return obj.STATUS
    get_status.short_description = 'Status'
    
    def empresa_nome(self, obj):
        return obj.empresa.RAZAOSOCIAL if obj.empresa else '-'
    empresa_nome.short_description = 'Empresa'