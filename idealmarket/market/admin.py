from django.contrib import admin
from .models import Product, Catagory, Ombor, Sale, SaleItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0

class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = ('id', 'created_at', 'total_sum_display')
    readonly_fields = ('total_sum_display',)

    def total_sum_display(self, obj):
        return obj.total_sum
    total_sum_display.short_description = "Umumiy summa"

admin.site.register(Product)
admin.site.register(Catagory)
admin.site.register(Ombor)
admin.site.register(Sale, SaleAdmin)
