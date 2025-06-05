from django import forms
from .models import Product, Ombor

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

class OmborForm(forms.ModelForm):
    class Meta:
        model = Ombor
        fields = ['name']