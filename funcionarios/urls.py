from django.urls import path
from . import views

urlpatterns = [
    path('', views.funcionarios, name='funcionarios'),
    path('<int:id>/', views.detalhes_funcionario, name='detalhes_funcionario'),
]
