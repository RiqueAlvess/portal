from django.urls import path
from . import views

urlpatterns = [
    path('', views.absenteismo, name='absenteismo'),
    path('ntep/', views.ntep, name='ntep'),
    path('ntep/<int:id>/', views.ntep_detalhes, name='ntep_detalhes'),
]