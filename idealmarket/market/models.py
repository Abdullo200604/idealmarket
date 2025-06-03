from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Catagory(models.Model):
    name = models.CharField(max_length=100)
    desc = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Ombor(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Product(models.Model):
    catagory = models.ForeignKey(Catagory, on_delete=models.CASCADE, related_name='products')
    ombor = models.ForeignKey(Ombor, on_delete=models.CASCADE, related_name='products')
    barcode = models.CharField(max_length=100, unique=True)
    desc = models.TextField(blank=True, null=True)
    r_price = models.DecimalField(max_digits=12, decimal_places=2)
    s_price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=0)
    # Muddati uchun
    start_date = models.DateField(default=timezone.now)     # Mahsulot sotuvga chiqqan sana
    end_date = models.DateField(blank=True, null=True)      # Muddati tugash sanasi (ixtiyoriy)

    @property
    def is_active(self):
        now = timezone.now().date()
        if self.start_date and self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True

    def __str__(self):
        return f"{self.barcode} - {self.desc or ''}"

class Sale(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def total_sum(self):
        return sum(item.price * item.quantity for item in self.items.all())

    def __str__(self):
        return f"Sale #{self.id} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if not self.price or self.price == 0:
            self.price = self.product.s_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.barcode} ({self.quantity} x {self.price})"
