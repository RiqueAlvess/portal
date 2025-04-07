from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.messages import constants
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import auth
from dashboard.models import UsuarioEmpresa, EmpresaAtivaUsuario

def login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'GET':
        return render(request, 'login.html')
    
    elif request.method == 'POST':
        username = request.POST.get('username')
        senha = request.POST.get('senha')
        user = authenticate(request, username=username, password=senha)

        if user:
            auth.login(request, user)

            vinculos = UsuarioEmpresa.objects.filter(usuario=user)
            if not vinculos.exists():
                messages.add_message(request, constants.ERROR, 'Usuário sem empresa vinculada.')
                return redirect('login')

            empresa_padrao = vinculos.first().empresa
            EmpresaAtivaUsuario.objects.update_or_create(
                usuario=user,
                defaults={'empresa': empresa_padrao}
            )

            return redirect('/dashboard/')
        
    messages.add_message(request, constants.ERROR, 'Username ou senha inválidos')
    return redirect('login')
