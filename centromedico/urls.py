"""
URL configuration for centromedico project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# centromedico/urls.py

from django.contrib import admin
from django.urls import path
from centroimmune import views

urlpatterns = [
    path('', views.index, name='index'),
    path('registro/', views.registro, name='registro'),
    path('inicio_sesion/', views.inicio_sesion, name='inicio_sesion'),
    path('portal/', views.portal_usuario, name='portal_usuario'),
    path('solicitar_cita/', views.solicitar_cita, name='solicitar_cita'),
    path('modificar_cita/<int:cita_id>/', views.modificar_cita, name='modificar_cita'),
    path('asignar_tratamiento/<int:cita_id>/', views.asignar_tratamiento, name='asignar_tratamiento'),
    path('cancelar_cita/<int:cita_id>/', views.cancelar_cita, name='cancelar_cita'),
    # ... otras rutas ...
]