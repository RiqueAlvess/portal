from django.urls import path, include
from . import views
from dashboard.views import trocar_empresa


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('trocar-empresa/', trocar_empresa, name='trocar_empresa'),
]
