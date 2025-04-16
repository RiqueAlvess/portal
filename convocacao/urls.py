from django.urls import path
from . import views

urlpatterns = [
    path('', views.convocacao, name='convocacao'),
    path('detalhes/<int:id>/', views.convocacao_detalhes, name='convocacao_detalhes'),
]