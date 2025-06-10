from django.contrib import admin
from .models import Product, Catagory, Ombor, Sale, SaleItem
from import_export.admin import ImportExportModelAdmin

# Inlinelar
class ProductInline(admin.TabularInline):
    model = Product
    extra = 1

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0

# Kategoriya admini
@admin.register(Catagory)
class CatagoryAdmin(ImportExportModelAdmin):
    inlines = [ProductInline]
    list_display = ('name', 'desc')
    search_fields = ('name',)

# Ombor admini
@admin.register(Ombor)
class OmborAdmin(ImportExportModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Mahsulot admini
@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    list_display = ('desc', 'catagory', 's_price', 'barcode', 'ombor', 'stock', 'is_active', 'start_date', 'end_date')
    search_fields = ('desc', 'barcode')
    list_filter = ('catagory', 'ombor', 'is_active')
    list_editable = ('is_active', 'stock')
    ordering = ('-id',)

# Sotuv (Sale) admini
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = ('id', 'created_at', 'created_by', 'total_sum_display')
    readonly_fields = ('total_sum_display',)
    date_hierarchy = 'created_at'
    search_fields = ('id', 'created_by__username')

    def total_sum_display(self, obj):
        return obj.total_sum
    total_sum_display.short_description = "Umumiy summa"

# SaleItem uchun alohida admin (odatda ko‘rinmaydi, faqat inlineda)
@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'sale', 'product', 'quantity', 'price')
    search_fields = ('product__desc', 'sale__id')
    list_filter = ('product',)
