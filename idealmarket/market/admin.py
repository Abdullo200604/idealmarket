from django.contrib import admin
from .models import Product, Catagory, Ombor, Sale, SaleItem
from import_export.admin import ImportExportModelAdmin

class ProductInline(admin.TabularInline):
    model = Product
    extra = 1

@admin.register(Catagory)
class CatagoryAdmin(ImportExportModelAdmin):
    inlines = [ProductInline]
    list_display = ('name', 'desc')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    list_display = ('desc', 'catagory', 's_price', 'barcode', 'ombor')
    search_fields = ('desc', 'barcode')
    list_filter = ('catagory', 'ombor')

# Ombor uchun ImportExport imkoniyatini qo‘shish
@admin.register(Ombor)
class OmborAdmin(ImportExportModelAdmin):
    list_display = ('name',)

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = ('id', 'created_at', 'total_sum_display')
    readonly_fields = ('total_sum_display',)
    date_hierarchy = 'created_at'

    def total_sum_display(self, obj):
        return obj.total_sum
    total_sum_display.short_description = "Umumiy summa"
