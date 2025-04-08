from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from dashboard.models import EmpresaAtivaUsuario, UsuarioEmpresa, Empresa
from funcionarios.models import Funcionario

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from dashboard.models import EmpresaAtivaUsuario
from funcionarios.models import Funcionario

@login_required
def dashboard(request):
    try:
        empresa_ativa = EmpresaAtivaUsuario.objects.get(usuario=request.user).empresa
    except EmpresaAtivaUsuario.DoesNotExist:
        return redirect('login')

    funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).exclude(NOME__iexact='nomegenerico')

    total_funcionarios = funcionarios.count()
    total_ferias = funcionarios.filter(SITUACAO="Férias").count()
    total_afastados = funcionarios.filter(SITUACAO="Afastado").count()

    sem_matricula = funcionarios.filter(MATRICULAFUNCIONARIO__startswith='semmatricula')

    perc_ferias = round((total_ferias / total_funcionarios) * 100, 1) if total_funcionarios else 0
    perc_afastados = round((total_afastados / total_funcionarios) * 100, 1) if total_funcionarios else 0
    perc_sem_matricula = round((sem_matricula.count() / total_funcionarios) * 100, 1) if total_funcionarios else 0

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
