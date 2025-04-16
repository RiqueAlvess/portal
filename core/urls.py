from django.contrib import admin
from django.urls import path, include
from core.views import landing

urlpatterns = [
    path('', landing, name='landing'),
    path('admin/', admin.site.urls),
    path('usuarios/', include('usuarios.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('funcionarios/', include('funcionarios.urls')),
    path('absenteismo/', include('absenteismo.urls')),
    path('convocacao/', include('convocacao.urls')),
]
