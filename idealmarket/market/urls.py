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

    #Admin
    path('management/', views.admin_management, name='admin_management'),
    path('management/products/', views.admin_products, name='admin_products'),
    path('management/categories/', views.admin_categories, name='admin_categories'),
    path('management/users/', views.admin_users, name='admin_users'),
    path('management/groups/', views.admin_groups, name='admin_groups'),
    path('management/ombors/', views.admin_ombors, name='admin_ombors'),
    path('management/sales/', views.admin_sales, name='admin_sales'),
    path('management/', views.admin_management, name='admin_management'),

    #Admin product
    path('management/products/', views.admin_products, name='admin_products'),
    path('management/products/add/', views.admin_product_add, name='admin_product_add'),
    path('management/products/edit/<int:pk>/', views.admin_product_edit, name='admin_product_edit'),
    path('management/products/delete/<int:pk>/', views.admin_product_delete, name='admin_product_delete'),
    path('management/products/bulk_delete/', views.admin_product_bulk_delete, name='admin_product_bulk_delete'),

   # Kategoriyalar uchun URL’lar
    path('management/categories/', views.admin_categories, name='admin_categories'),
    path('management/categories/add/', views.admin_category_add, name='admin_category_add'),
    path('management/categories/<int:pk>/edit/', views.admin_category_edit, name='admin_category_edit'),
    path('management/categories/<int:pk>/delete/', views.admin_category_delete, name='admin_category_delete'),

    # Omborlar uchun URL’lar
    path('management/ombors/', views.admin_ombors, name='admin_ombors'),
    path('management/ombors/add/', views.admin_ombor_add, name='admin_ombor_add'),
    path('management/ombors/<int:pk>/edit/', views.admin_ombor_edit, name='admin_ombor_edit'),
    path('management/ombors/<int:pk>/delete/', views.admin_ombor_delete, name='admin_ombor_delete'),

    # users
    path('management/users/', views.admin_users, name='admin_users'),
    path('management/users/add/', views.admin_user_add, name='admin_user_add'),
    path('management/users/<int:user_id>/edit/', views.admin_user_edit, name='admin_user_edit'),
    path('management/users/<int:user_id>/delete/', views.admin_user_delete, name='admin_user_delete'),

    #Group
    path('management/groups/', views.admin_groups, name='admin_groups'),
    path('management/groups/add/', views.admin_group_add, name='admin_group_add'),
    path('management/groups/<int:group_id>/edit/', views.admin_group_edit, name='admin_group_edit'),
    path('management/groups/<int:group_id>/delete/', views.admin_group_delete, name='admin_group_delete'),

]
