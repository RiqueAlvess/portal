from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Case, When, Value, IntegerField
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from dashboard.models import EmpresaAtivaUsuario
from convocacao.models import Convocacao
from funcionarios.models import Funcionario

@login_required
def convocacao(request):
    try:
        empresa_ativa = EmpresaAtivaUsuario.objects.get(usuario=request.user).empresa
    except EmpresaAtivaUsuario.DoesNotExist:
        return redirect('login')
    
    status_filter = request.GET.get('status', '')
    busca = request.GET.get('q', '')
    
    hoje = timezone.now().date()
    fim_de_ano = timezone.datetime(hoje.year, 12, 31).date()

    convocacoes = Convocacao.objects.filter(empresa=empresa_ativa)
    
    em_dia_count = convocacoes.filter(
        Q(REFAZER__isnull=False) & 
        Q(REFAZER__year__gt=hoje.year)
    ).count()
    
    a_vencer_count = convocacoes.filter(
        Q(REFAZER__isnull=False) & 
        Q(REFAZER__lte=fim_de_ano) & 
        Q(REFAZER__gt=hoje)
    ).count()
    
    pendente_count = convocacoes.filter(
        Q(ULTIMOPEDIDO__isnull=False) & 
        Q(DATARESULTADO__isnull=True) & 
        Q(REFAZER__isnull=True)
    ).count()
    
    vencido_count = convocacoes.filter(
        Q(REFAZER__isnull=False) & 
        Q(REFAZER__lt=hoje)
    ).count()
    
    sem_historico_count = convocacoes.filter(
        Q(ULTIMOPEDIDO__isnull=True) & 
        Q(DATARESULTADO__isnull=True) & 
        Q(REFAZER__isnull=True)
    ).count()
    
    if status_filter:
        if status_filter == 'em_dia':
            convocacoes = convocacoes.filter(
                Q(REFAZER__isnull=False) & 
                Q(REFAZER__year__gt=hoje.year)
            )
        elif status_filter == 'a_vencer':
            convocacoes = convocacoes.filter(
                Q(REFAZER__isnull=False) & 
                Q(REFAZER__lte=fim_de_ano) & 
                Q(REFAZER__gt=hoje)
            )
        elif status_filter == 'pendente':
            convocacoes = convocacoes.filter(
                Q(ULTIMOPEDIDO__isnull=False) & 
                Q(DATARESULTADO__isnull=True) & 
                Q(REFAZER__isnull=True)
            )
        elif status_filter == 'vencido':
            convocacoes = convocacoes.filter(
                Q(REFAZER__isnull=False) & 
                Q(REFAZER__lt=hoje)
            )
        elif status_filter == 'sem_historico':
            convocacoes = convocacoes.filter(
                Q(ULTIMOPEDIDO__isnull=True) & 
                Q(DATARESULTADO__isnull=True) & 
                Q(REFAZER__isnull=True)
            )
    
    if busca:
        convocacoes = convocacoes.filter(
            Q(NOME__icontains=busca) | 
            Q(CPFFUNCIONARIO__icontains=busca) | 
            Q(SETOR__icontains=busca) | 
            Q(EXAME__icontains=busca)
        )
    
    funcionarios_exames = (
        convocacoes.values('CODIGOFUNCIONARIO', 'NOME')
        .annotate(
            total_exames=Count('id'),
            em_dia=Count(Case(
                When(REFAZER__isnull=False, REFAZER__year__gt=hoje.year, then=1),
                output_field=IntegerField()
            )),
            a_vencer=Count(Case(
                When(REFAZER__isnull=False, REFAZER__lte=fim_de_ano, REFAZER__gt=hoje, then=1),
                output_field=IntegerField()
            )),
            pendente=Count(Case(
                When(ULTIMOPEDIDO__isnull=False, DATARESULTADO__isnull=True, REFAZER__isnull=True, then=1),
                output_field=IntegerField()
            )),
            vencido=Count(Case(
                When(REFAZER__isnull=False, REFAZER__lt=hoje, then=1),
                output_field=IntegerField()
            )),
            sem_historico=Count(Case(
                When(ULTIMOPEDIDO__isnull=True, DATARESULTADO__isnull=True, REFAZER__isnull=True, then=1),
                output_field=IntegerField()
            ))
        )
        .order_by('NOME')
    )
    
    paginator = Paginator(funcionarios_exames, 10)
    page = request.GET.get('page')
    
    try:
        funcionarios_paginados = paginator.page(page)
    except PageNotAnInteger:
        funcionarios_paginados = paginator.page(1)
    except EmptyPage:
        funcionarios_paginados = paginator.page(paginator.num_pages)
    
    convocacao_total_count = convocacoes.count()
    
    context = {
        'empresa_ativa': empresa_ativa,
        'funcionarios': funcionarios_paginados,
        'busca': busca,
        'status_filter': status_filter,
        'em_dia_count': em_dia_count,
        'a_vencer_count': a_vencer_count,
        'pendente_count': pendente_count,
        'vencido_count': vencido_count,
        'sem_historico_count': sem_historico_count,
        'total_count': convocacao_total_count
    }
    
    return render(request, 'convocacao.html', context)

@login_required
def convocacao_detalhes(request, id):
    try:
        empresa_ativa = EmpresaAtivaUsuario.objects.get(usuario=request.user).empresa
    except EmpresaAtivaUsuario.DoesNotExist:
        return redirect('login')

    funcionario_codigo = id
    funcionario = None
    
    try:
        exames = Convocacao.objects.filter(
            empresa=empresa_ativa,
            CODIGOFUNCIONARIO=funcionario_codigo
        )
        
        if not exames.exists():
            return redirect('convocacao')
            
    except Exception:
        return redirect('convocacao')
    
    hoje = timezone.now().date()
    fim_de_ano = timezone.datetime(hoje.year, 12, 31).date()
    
    exames_em_dia = exames.filter(
        Q(REFAZER__isnull=False) & 
        Q(REFAZER__year__gt=hoje.year)
    )
    
    exames_a_vencer = exames.filter(
        Q(REFAZER__isnull=False) & 
        Q(REFAZER__lte=fim_de_ano) & 
        Q(REFAZER__gt=hoje)
    )
    
    exames_pendentes = exames.filter(
        Q(ULTIMOPEDIDO__isnull=False) & 
        Q(DATARESULTADO__isnull=True) & 
        Q(REFAZER__isnull=True)
    )
    
    exames_vencidos = exames.filter(
        Q(REFAZER__isnull=False) & 
        Q(REFAZER__lt=hoje)
    )
    
    exames_sem_historico = exames.filter(
        Q(ULTIMOPEDIDO__isnull=True) & 
        Q(DATARESULTADO__isnull=True) & 
        Q(REFAZER__isnull=True)
    )
    
    try:
        funcionario = Funcionario.objects.get(CODIGO=funcionario_codigo, empresa=empresa_ativa)
        nome_funcionario = funcionario.NOME
    except Funcionario.DoesNotExist:
        nome_funcionario = exames.first().NOME if exames.exists() else "Funcionário"
    
    context = {
        'empresa_ativa': empresa_ativa,
        'funcionario': funcionario,
        'nome_funcionario': nome_funcionario,
        'exames_em_dia': exames_em_dia,
        'exames_a_vencer': exames_a_vencer,
        'exames_pendentes': exames_pendentes,
        'exames_vencidos': exames_vencidos,
        'exames_sem_historico': exames_sem_historico,
        'total_exames': exames.count()
    }
    
    return render(request, 'convocacao_detalhes.html', context)