# idealmarket/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from market import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='market/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard_redirect, name='dashboard'),  # foydalanuvchi roliga qarab yo'naltirish
    path('', include('market.urls')),  # Barcha boshqa marshrutlar market appdan olinadi
]
