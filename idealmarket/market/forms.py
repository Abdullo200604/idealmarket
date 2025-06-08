from django import forms
from .models import Product, Ombor

from django.utils import timezone
from datetime import timedelta

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['start_date'].initial = timezone.now()
            self.fields['end_date'].initial = timezone.now() + timedelta(days=30)


class OmborForm(forms.ModelForm):
    class Meta:
        model = Ombor
        fields = ['name']