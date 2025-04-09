from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from dashboard.models import EmpresaAtivaUsuario, UsuarioEmpresa, Empresa
from funcionarios.models import Funcionario
from datetime import timedelta, date
from django.db.models import Count, Sum, F
from absenteismo.models import Absenteismo

@login_required
def dashboard(request):
    try:
        empresa_ativa = EmpresaAtivaUsuario.objects.get(usuario=request.user).empresa
    except EmpresaAtivaUsuario.DoesNotExist:
        return redirect('login')

    funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).exclude(NOME__istartswith='nomegenerico')

    total_funcionarios = funcionarios.count()
    total_ferias = funcionarios.filter(SITUACAO="Férias").count()
    total_afastados = funcionarios.filter(SITUACAO="Afastado").count()
    sem_matricula = funcionarios.filter(MATRICULAFUNCIONARIO__startswith='semmatricula')

    perc_ferias = round((total_ferias / total_funcionarios) * 100, 1) if total_funcionarios else 0
    perc_afastados = round((total_afastados / total_funcionarios) * 100, 1) if total_funcionarios else 0
    perc_sem_matricula = round((sem_matricula.count() / total_funcionarios) * 100, 1) if total_funcionarios else 0

    filtro_periodo = request.GET.get('periodo', 'semestre')
    dias_por_periodo = {
        'mes': 30,
        'trimestre': 90,
        'semestre': 180
    }
    dias = dias_por_periodo.get(filtro_periodo, 180)
    data_limite = date.today() - timedelta(days=dias)
    limite_atestados = {'mes': 2, 'trimestre': 6, 'semestre': 12}.get(filtro_periodo, 12)

    abs_periodo = Absenteismo.objects.filter(
        empresa=empresa_ativa,
        DT_INICIO_ATESTADO__gte=data_limite
    ).exclude(NOME_FUNCIONARIO__istartswith='nomegenerico') \
     .exclude(funcionario__isnull=True)

    hiperatestadistas = (
        abs_periodo.values('MATRICULA_FUNC', 'NOME_FUNCIONARIO')
        .annotate(
            total_atestados=Count('id'),
            total_dias=Sum('DIAS_AFASTADOS')
        )
        .filter(total_atestados__gte=limite_atestados)
        .order_by('-total_atestados')
    )

    hoje = date.today()
    experiencia_limite = hoje - timedelta(days=90)

    abs_experiencia = Absenteismo.objects.filter(
        empresa=empresa_ativa,
        funcionario__isnull=False,
        funcionario__DATA_ADMISSAO__gte=experiencia_limite,
        funcionario__DATA_ADMISSAO__isnull=False,
        DT_INICIO_ATESTADO__gte=F('funcionario__DATA_ADMISSAO'),
        DT_INICIO_ATESTADO__lte=F('funcionario__DATA_ADMISSAO') + timedelta(days=90)
    ).exclude(NOME_FUNCIONARIO__istartswith='nomegenerico')

    atestados_experiencia = (
        abs_experiencia.values('MATRICULA_FUNC', 'NOME_FUNCIONARIO', 'funcionario__CPF')
        .annotate(
            total_atestados=Count('id'),
            total_dias=Sum('DIAS_AFASTADOS')
        )
        .order_by('-total_atestados')
    )

    return render(request, "dashboard.html", {
        "empresa_ativa": empresa_ativa,
        "total_funcionarios": total_funcionarios,
        "total_ferias": total_ferias,
        "perc_ferias": perc_ferias,
        "total_afastados": total_afastados,
        "perc_afastados": perc_afastados,
        "total_sem_matricula": sem_matricula.count(),
        "perc_sem_matricula": perc_sem_matricula,
        "colaboradores_sem_matricula": sem_matricula,
        "hiperatestadistas": hiperatestadistas,
        "atestados_experiencia": atestados_experiencia,
        "filtro_periodo": filtro_periodo,
    })



@require_POST
@login_required
def trocar_empresa(request):
    empresa_id = request.POST.get('empresa_id')

    if not empresa_id:
        return redirect('dashboard')

    empresa = get_object_or_404(Empresa, id=empresa_id)

    if not UsuarioEmpresa.objects.filter(usuario=request.user, empresa=empresa).exists():
        return redirect('dashboard')

    EmpresaAtivaUsuario.objects.update_or_create(
        usuario=request.user,
        defaults={'empresa': empresa}
    )

    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
