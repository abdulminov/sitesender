"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError


def health_check(request):
    return JsonResponse({"status": "healthy"}, status=200)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('logs/', include('logs.urls')), #подключаем страничку с БД
    path('health/', health_check, name='health_check'), #подключаем healthcheck
]
