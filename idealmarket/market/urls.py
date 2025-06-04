# idealmarket/market/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.kassa, name='kassa'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('cart/clear/', views.cart_clear, name='cart_clear'),
    path('cart/checkout/', views.cart_checkout, name='cart_checkout'),
    path('cheklar/', views.sales_list, name='sales_list'),
    path('cheklar/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('statistika/', views.statistics, name='statistics'),

    # Eksport yo‘llari
    path('cheklar/export/pdf/', views.export_sales_pdf, name='export_sales_pdf'),
    path('statistics/export/excel/', views.export_statistics_excel, name='statistics_export_excel'),
    path('statistics/export/pdf/', views.export_statistics_pdf, name='statistics_export_pdf'),
]
