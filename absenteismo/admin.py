from django.contrib import admin
from .models import Absenteismo
from funcionarios.models import Funcionario

@admin.register(Absenteismo)
class AbsenteismoAdmin(admin.ModelAdmin):
    list_display = ('get_funcionario_nome', 'MATRICULA_FUNC', 'get_tipo_atestado',
                   'DT_INICIO_ATESTADO', 'DT_FIM_ATESTADO', 'DIAS_AFASTADOS',
                   'CID_PRINCIPAL', 'TIPO_LICENCA')
    list_filter = ('TIPO_ATESTADO', 'empresa__RAZAOSOCIAL', 'DT_INICIO_ATESTADO',
                  'GRUPO_PATOLOGICO')
    search_fields = ('MATRICULA_FUNC', 'NOME_FUNCIONARIO', 'CID_PRINCIPAL',
                    'DESCRICAO_CID', 'UNIDADE', 'SETOR')
    date_hierarchy = 'DT_INICIO_ATESTADO'
    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'CODIGOEMPRESA', 'MATRICULA_FUNC', 'NOME_FUNCIONARIO', 'UNIDADE', 'SETOR')
        }),
        ('Dados do Atestado', {
            'fields': ('TIPO_ATESTADO', 'DT_INICIO_ATESTADO', 'DT_FIM_ATESTADO',
                      'HORA_INICIO_ATESTADO', 'HORA_FIM_ATESTADO', 'DIAS_AFASTADOS',
                      'HORAS_AFASTADO')
        }),
        ('Dados Médicos', {
            'fields': ('CID_PRINCIPAL', 'DESCRICAO_CID', 'GRUPO_PATOLOGICO', 'TIPO_LICENCA')
        }),
        ('Dados do Funcionário', {
            'fields': ('DT_NASCIMENTO', 'SEXO'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('CODIGOEMPRESA',)
    
    def get_funcionario_nome(self, obj):
        return obj.NOME_FUNCIONARIO or f"Matrícula: {obj.MATRICULA_FUNC}" or "Não identificado"
    get_funcionario_nome.short_description = 'Funcionário'
    get_funcionario_nome.admin_order_field = 'NOME_FUNCIONARIO'
    
    def get_tipo_atestado(self, obj):
        return obj.get_TIPO_ATESTADO_display()
    get_tipo_atestado.short_description = 'Tipo de Atestado'
    get_tipo_atestado.admin_order_field = 'TIPO_ATESTADO'
    
    def save_model(self, request, obj, form, change):
      
        if obj.empresa:
            obj.CODIGOEMPRESA = obj.empresa.CODIGO
        
        
        if obj.MATRICULA_FUNC and not obj.NOME_FUNCIONARIO:
            try:
                func = Funcionario.objects.filter(
                    MATRICULAFUNCIONARIO=obj.MATRICULA_FUNC,
                    CODIGOEMPRESA=obj.CODIGOEMPRESA
                ).first()
                
                if func:
                    obj.NOME_FUNCIONARIO = func.NOME
                    if not obj.DT_NASCIMENTO:
                        obj.DT_NASCIMENTO = func.DATA_NASCIMENTO
                    if not obj.SEXO and func.SEXO:
                        obj.SEXO = func.SEXO
            except:
                pass

        if not obj.DIAS_AFASTADOS and obj.DT_INICIO_ATESTADO and obj.DT_FIM_ATESTADO:
            delta = obj.DT_FIM_ATESTADO - obj.DT_INICIO_ATESTADO
            obj.DIAS_AFASTADOS = delta.days + 1
            
        super().save_model(request, obj, form, change)


if not admin.site.is_registered(Funcionario):
    @admin.register(Funcionario)
    class FuncionarioAdmin(admin.ModelAdmin):
        list_display = ('CODIGO', 'NOME', 'CODIGOEMPRESA', 'NOMEEMPRESA', 'CPF', 'SITUACAO')
        list_filter = ('CODIGOEMPRESA', 'SITUACAO', 'SEXO', 'ESTADOCIVIL')
        search_fields = ['NOME', 'CPF', 'MATRICULAFUNCIONARIO', 'CODIGO']