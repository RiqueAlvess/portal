from datetime import timedelta, date
from django.db.models import Count, Sum, Avg, F, Q, Value, IntegerField, Case, When, CharField
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from dashboard.models import EmpresaAtivaUsuario
from absenteismo.models import Absenteismo
from funcionarios.models import Funcionario

@login_required
def absenteismo(request):
    try:
        empresa_ativa = EmpresaAtivaUsuario.objects.get(usuario=request.user).empresa
    except EmpresaAtivaUsuario.DoesNotExist:
        return render(request, "erro.html", {"mensagem": "Empresa ativa não encontrada."})

    periodo = request.GET.get("periodo", "semestre")
    grupo = request.GET.get("grupo")
    unidade = request.GET.get("unidade")
    setor = request.GET.get("setor")

    hoje = date.today()
    if periodo == "trimestre":
        data_inicio = hoje - timedelta(days=90)
    elif periodo == "mes":
        data_inicio = hoje - timedelta(days=30)
    else:
        data_inicio = hoje - timedelta(days=180)

    atestados = Absenteismo.objects.filter(
        empresa=empresa_ativa,
        DT_INICIO_ATESTADO__gte=data_inicio,
        funcionario__isnull=False
    ).exclude(NOME_FUNCIONARIO__icontains="nomegenerico")

    if grupo:
        atestados = atestados.filter(SETOR__startswith=grupo)
    if unidade:
        atestados = atestados.filter(UNIDADE=unidade)
    if setor:
        atestados = atestados.filter(SETOR=setor)

    VALOR_HORA = 8.02

    total_atestados = atestados.count()
    total_dias = atestados.aggregate(total=Sum("DIAS_AFASTADOS"))["total"] or 0
    total_funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).exclude(NOME__icontains="nomegenerico").count()

    media_dias_atestado = round(total_dias / total_atestados, 2) if total_atestados else 0
    media_atestados_por_func = round(total_atestados / total_funcionarios, 2) if total_funcionarios else 0

    total_horas_afastadas = total_dias * 8
    impacto_financeiro = round(total_horas_afastadas * VALOR_HORA, 2)

    bradford = (
        atestados.values("MATRICULA_FUNC", "NOME_FUNCIONARIO")
        .annotate(
            episodios=Count("id"),
            dias=Sum("DIAS_AFASTADOS")
        )
        .annotate(
            bradford=F("episodios") * F("episodios") * F("dias"),
            risco=Case(
                When(bradford__gte=600, then=Value("Alto")),
                When(bradford__gte=300, then=Value("Médio")),
                default=Value("Baixo"),
                output_field=CharField()
            )
        )
        .order_by("-bradford")
    )

    cid_setor = (
        atestados.values("SETOR", "CID_PRINCIPAL")
        .annotate(qtd=Count("id"))
        .order_by("SETOR", "-qtd")
    )

    por_genero = (
        atestados.values("SEXO")
        .annotate(qtd=Count("id"), dias=Sum("DIAS_AFASTADOS"))
    )

    return render(request, "absenteismo.html", {
        "empresa_ativa": empresa_ativa,
        "total_funcionarios": total_funcionarios,
        "total_atestados": total_atestados,
        "total_dias": total_dias,
        "media_dias_atestado": media_dias_atestado,
        "media_atestados_por_func": media_atestados_por_func,
        "impacto_financeiro": impacto_financeiro,
        "bradford": bradford,
        "cid_setor": cid_setor,
        "por_genero": por_genero,
        "periodo": periodo,
        "grupo": grupo,
        "unidade": unidade,
        "setor": setor,
    })
