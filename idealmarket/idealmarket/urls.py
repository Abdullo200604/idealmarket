# idealmarket/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('market.urls')),   # bu qatorda aynan shunday bo‘lishi kerak!
]
