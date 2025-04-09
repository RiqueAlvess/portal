from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from dashboard.models import EmpresaAtivaUsuario
from .models import Funcionario
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.db.models import Q

@login_required
def funcionarios(request):
    try:
        empresa_ativa = EmpresaAtivaUsuario.objects.get(usuario=request.user).empresa
    except EmpresaAtivaUsuario.DoesNotExist:
        return redirect('login')
        
    busca = request.GET.get('q', '')
    situacao = request.GET.get('situacao', '')

    funcionarios_queryset = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).exclude(
        NOME__icontains='nomegenerico'
    )

    if busca:
        funcionarios_queryset = funcionarios_queryset.filter(
            Q(NOME__icontains=busca) | Q(CPF__icontains=busca)
        )

    if situacao:
        funcionarios_queryset = funcionarios_queryset.filter(SITUACAO=situacao)

    paginator = Paginator(funcionarios_queryset, 10)
    page = request.GET.get('page')

    try:
        funcionarios_paginados = paginator.page(page)
    except PageNotAnInteger:
        funcionarios_paginados = paginator.page(1)
    except EmptyPage:
        funcionarios_paginados = paginator.page(paginator.num_pages)

    situacoes_disponiveis = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).exclude(
        SITUACAO__isnull=True
    ).values_list('SITUACAO', flat=True).distinct()

    return render(request, 'funcionarios.html', {
        'funcionarios': funcionarios_paginados,
        'situacoes': situacoes_disponiveis,
        'busca': busca,
        'situacao_selecionada': situacao,
        'empresa_ativa': empresa_ativa  
    })


@login_required
def detalhes_funcionario(request, id):
    try:
        empresa_ativa = EmpresaAtivaUsuario.objects.get(usuario=request.user).empresa
    except EmpresaAtivaUsuario.DoesNotExist:
        return redirect('login')
        
    funcionario = Funcionario.objects.get(id=id, empresa=empresa_ativa)
    
    tab_ativa = request.GET.get('tab', 'dados')
    
    return render(request, 'detalhes_funcionarios.html', {
        'funcionario': funcionario,
        'empresa_ativa': empresa_ativa,
        'tab_ativa': tab_ativa
    })