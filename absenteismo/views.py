from datetime import timedelta, date
from django.db.models import Count, Sum, Avg, F, Q, Value, IntegerField, CharField, OuterRef, Subquery, Case, When
from django.db.models.functions import ExtractMonth, ExtractWeekDay, ExtractYear, Coalesce
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from dashboard.models import EmpresaAtivaUsuario
from absenteismo.models import Absenteismo
from funcionarios.models import Funcionario
import json

@login_required
def absenteismo(request):
    try:
        empresa_ativa = EmpresaAtivaUsuario.objects.get(usuario=request.user).empresa
    except EmpresaAtivaUsuario.DoesNotExist:
        return render(request, "erro.html", {"mensagem": "Empresa ativa não encontrada."})

    periodo = request.GET.get("periodo", "semestre")
    grupo = request.GET.get("grupo", "")
    tipo_duracao = request.GET.get("tipo_duracao", "")
    setor = request.GET.get("setor", "")

    hoje = date.today()
    if periodo == "trimestre":
        data_inicio = hoje - timedelta(days=90)
        dias_periodo = 90
    elif periodo == "mes":
        data_inicio = hoje - timedelta(days=30)
        dias_periodo = 30
    else:
        data_inicio = hoje - timedelta(days=180)
        dias_periodo = 180

    atestados = Absenteismo.objects.filter(
        empresa=empresa_ativa,
        DT_INICIO_ATESTADO__gte=data_inicio,
        funcionario__isnull=False
    ).exclude(NOME_FUNCIONARIO__icontains="nomegenerico")

    if grupo:
        atestados = atestados.filter(SETOR__startswith=grupo)
    if setor:
        atestados = atestados.filter(SETOR=setor)
    
    if tipo_duracao:
        if tipo_duracao == "horas":
            atestados = atestados.filter(TIPO_ATESTADO=1)
        elif tipo_duracao == "1-3":
            atestados = atestados.filter(DIAS_AFASTADOS__gte=1, DIAS_AFASTADOS__lte=3, TIPO_ATESTADO=0)
        elif tipo_duracao == "4-7":
            atestados = atestados.filter(DIAS_AFASTADOS__gte=4, DIAS_AFASTADOS__lte=7, TIPO_ATESTADO=0)
        elif tipo_duracao == "8-14":
            atestados = atestados.filter(DIAS_AFASTADOS__gte=8, DIAS_AFASTADOS__lte=14, TIPO_ATESTADO=0)
        elif tipo_duracao == "15+":
            atestados = atestados.filter(DIAS_AFASTADOS__gte=15, TIPO_ATESTADO=0)

    setores = atestados.values_list('SETOR', flat=True).distinct().order_by('SETOR')
    VALOR_HORA = 8.02

    total_atestados = atestados.count()
    total_dias = atestados.aggregate(total=Coalesce(Sum("DIAS_AFASTADOS"), 0))["total"]
    total_funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).exclude(NOME__icontains="nomegenerico").count()

    media_dias = total_dias / total_atestados if total_atestados else 0
    media_atestados = total_atestados / total_funcionarios if total_funcionarios else 0
    total_horas_afastadas = total_dias * 8
    impacto_financeiro = total_horas_afastadas * VALOR_HORA

    bradford = atestados.values(
        'MATRICULA_FUNC', 'NOME_FUNCIONARIO'
    ).annotate(
        episodios=Count('id'),
        total_dias=Coalesce(Sum('DIAS_AFASTADOS'), 0)
    ).annotate(
        bradford=F('episodios') * F('episodios') * F('total_dias'),
        risco=Case(
            When(bradford__gte=500, then=Value('ALTO')),
            When(bradford__gte=200, then=Value('MÉDIO')),
            default=Value('BAIXO'),
            output_field=CharField()
        )
    ).order_by('-bradford')

    bradford_critico_count = bradford.filter(risco='ALTO').count()

    funcionarios_com_atestados = atestados.values('funcionario').annotate(count=Count('id'))
    funcionarios_com_reincidencia = funcionarios_com_atestados.filter(count__gt=1).count()
    taxa_reincidencia = (funcionarios_com_reincidencia / funcionarios_com_atestados.count() * 100) if funcionarios_com_atestados.count() else 0

    dias_uteis = int(dias_periodo * 5/7)
    taxa_absenteismo = (total_dias / (total_funcionarios * dias_uteis) * 100) if total_funcionarios and dias_uteis else 0

    duracao_patterns = atestados.aggregate(
        horas=Count('id', filter=Q(TIPO_ATESTADO=1)),
        dias_1_3=Count('id', filter=Q(DIAS_AFASTADOS__gte=1, DIAS_AFASTADOS__lte=3, TIPO_ATESTADO=0)),
        dias_4_7=Count('id', filter=Q(DIAS_AFASTADOS__gte=4, DIAS_AFASTADOS__lte=7, TIPO_ATESTADO=0)),
        dias_8_14=Count('id', filter=Q(DIAS_AFASTADOS__gte=8, DIAS_AFASTADOS__lte=14, TIPO_ATESTADO=0)),
        dias_15_mais=Count('id', filter=Q(DIAS_AFASTADOS__gte=15, TIPO_ATESTADO=0))
    )

    dia_semana = atestados.annotate(
        dia_semana=ExtractWeekDay('DT_INICIO_ATESTADO')
    ).values('dia_semana').annotate(
        count=Count('id')
    ).order_by('dia_semana')

    impacto_por_cid = atestados.values('GRUPO_PATOLOGICO').exclude(
        GRUPO_PATOLOGICO=''
    ).annotate(
        dias=Coalesce(Sum('DIAS_AFASTADOS'), 0),
        horas=Count('id', filter=Q(TIPO_ATESTADO=1)) * 4,
        impacto=((F('dias') * 8) + F('horas')) * VALOR_HORA
    ).order_by('-impacto')[:10]

    absenteismo_por_setor = atestados.values('SETOR').annotate(
        count=Count('id'),
        dias=Coalesce(Sum('DIAS_AFASTADOS'), 0)
    ).order_by('-dias')[:10]

    absenteismo_por_cid = atestados.values('CID_PRINCIPAL', 'DESCRICAO_CID').exclude(
        CID_PRINCIPAL=''
    ).annotate(
        count=Count('id'),
        dias=Coalesce(Sum('DIAS_AFASTADOS'), 0)
    ).order_by('-count')[:10]

    evolucao_mensal = atestados.annotate(
        mes=ExtractMonth('DT_INICIO_ATESTADO'),
        ano=ExtractYear('DT_INICIO_ATESTADO')
    ).values('mes', 'ano').annotate(
        count=Count('id'),
        dias=Coalesce(Sum('DIAS_AFASTADOS'), 0)
    ).order_by('ano', 'mes')

    genero_analysis = atestados.values('SEXO').annotate(
        count=Count('id'),
        dias=Coalesce(Sum('DIAS_AFASTADOS'), 0)
    ).order_by('SEXO')

    cids_por_genero = {}
    for sexo_value, sexo_nome in Absenteismo.SEXO_CHOICES:
        top_cids = atestados.filter(SEXO=sexo_value).exclude(
            GRUPO_PATOLOGICO=''
        ).values('GRUPO_PATOLOGICO').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        if list(top_cids):
            cids_por_genero[sexo_nome] = list(top_cids)

    custo_por_setor = atestados.values('SETOR').annotate(
        dias=Coalesce(Sum('DIAS_AFASTADOS'), 0),
        horas=Count('id', filter=Q(TIPO_ATESTADO=1)) * 4,
        custo=((F('dias') * 8) + F('horas')) * VALOR_HORA
    ).order_by('-custo')[:10]

    cids_por_prefixo_setor = {}
    setor_prefixos = ['F', 'M', 'S', 'T']
    for prefixo in setor_prefixos:
        top_cids = atestados.filter(SETOR__startswith=prefixo).exclude(
            GRUPO_PATOLOGICO=''
        ).values('GRUPO_PATOLOGICO').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        if list(top_cids):
            cids_por_prefixo_setor[prefixo] = list(top_cids)

    age_cid_correlation = []
    age_ranges = [
        (0, 25, "18-25"),
        (26, 35, "26-35"),
        (36, 45, "36-45"),
        (46, 55, "46-55"),
        (56, 100, "56+"),
    ]
    
    for min_age, max_age, label in age_ranges:
        today = date.today()
        min_date = date(today.year - max_age, today.month, today.day)
        max_date = date(today.year - min_age, today.month, today.day)
        
        age_cids = atestados.filter(
            funcionario__DATA_NASCIMENTO__gte=min_date,
            funcionario__DATA_NASCIMENTO__lte=max_date
        ).exclude(
            GRUPO_PATOLOGICO=''
        ).values('GRUPO_PATOLOGICO').annotate(
            count=Count('id')
        ).order_by('-count')[:3]
        
        for cid in age_cids:
            age_cid_correlation.append({
                "age_range": label,
                "cid": cid['GRUPO_PATOLOGICO'],
                "count": cid['count']
            })

    def safe_cid_label(item):
        cid = item.get('CID_PRINCIPAL', '')
        desc = item.get('DESCRICAO_CID', '')
        if not desc:
            return cid
        return f"{cid} - {desc[:20]}"
    
    chart_data = {
        'duracao_patterns': {
            'labels': ['Horas', '1-3 dias', '4-7 dias', '8-14 dias', '15+ dias'],
            'data': [
                duracao_patterns['horas'],
                duracao_patterns['dias_1_3'],
                duracao_patterns['dias_4_7'],
                duracao_patterns['dias_8_14'],
                duracao_patterns['dias_15_mais']
            ]
        },
        'dia_semana': {
            'labels': ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'],
            'data': [0, 0, 0, 0, 0, 0, 0]
        },
        'impacto_por_cid': {
            'labels': [item['GRUPO_PATOLOGICO'] for item in impacto_por_cid],
            'data': [float(item['impacto']) for item in impacto_por_cid]
        },
        'absenteismo_por_setor': {
            'labels': [item['SETOR'] for item in absenteismo_por_setor],
            'data_count': [item['count'] for item in absenteismo_por_setor],
            'data_dias': [item['dias'] for item in absenteismo_por_setor]
        },
        'absenteismo_por_cid': {
            'labels': [safe_cid_label(item) for item in absenteismo_por_cid],
            'data_count': [item['count'] for item in absenteismo_por_cid],
            'data_dias': [item['dias'] for item in absenteismo_por_cid]
        },
        'evolucao_mensal': {
            'labels': [],
            'data_count': [],
            'data_dias': []
        },
        'genero': {
            'labels': ['Masculino', 'Feminino', 'Não informado'],
            'count': [0, 0, 0],
            'dias': [0, 0, 0]
        },
        'custo_por_setor': {
            'labels': [item['SETOR'] for item in custo_por_setor],
            'data': [float(item['custo']) for item in custo_por_setor]
        },
        'age_cid_correlation': {
            'data': age_cid_correlation
        }
    }

    for item in dia_semana:
        day_index = item['dia_semana'] - 1
        if 0 <= day_index < 7:
            chart_data['dia_semana']['data'][day_index] = item['count']

    month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    for item in evolucao_mensal:
        month_label = f"{month_names[item['mes']-1]} {item['ano']}"
        chart_data['evolucao_mensal']['labels'].append(month_label)
        chart_data['evolucao_mensal']['data_count'].append(item['count'])
        chart_data['evolucao_mensal']['data_dias'].append(item['dias'])

    for item in genero_analysis:
        if item['SEXO'] == 1:
            chart_data['genero']['count'][0] = item['count']
            chart_data['genero']['dias'][0] = item['dias']
        elif item['SEXO'] == 2:
            chart_data['genero']['count'][1] = item['count']
            chart_data['genero']['dias'][1] = item['dias']
        else:
            chart_data['genero']['count'][2] = item['count']
            chart_data['genero']['dias'][2] = item['dias']

    context = {
        "empresa_ativa": empresa_ativa,
        "periodo": periodo,
        "grupo": grupo,
        "tipo_duracao": tipo_duracao,
        "setor": setor,
        "setores": setores,
        
        "total_funcionarios": total_funcionarios,
        "total_atestados": total_atestados,
        "total_dias": total_dias,
        "media_dias": media_dias,
        "media_atestados": media_atestados,
        "impacto_financeiro": impacto_financeiro,
        "bradford_critico_count": bradford_critico_count,
        "taxa_reincidencia": taxa_reincidencia,
        "taxa_absenteismo": taxa_absenteismo,
        
        "bradford_detalhado": bradford[:20],
        "cids_por_genero": cids_por_genero,
        "cids_por_prefixo_setor": cids_por_prefixo_setor,
        
        "chart_data": json.dumps(chart_data),
        "sexo_choices": dict(Absenteismo.SEXO_CHOICES)
    }
    
    return render(request, "absenteismo.html", context)