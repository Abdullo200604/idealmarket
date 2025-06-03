from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import JsonResponse
from .models import Product, Sale, SaleItem
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db.models import Q

# ROLLARNI ANIQLASH
def is_kassir_or_admin(user):
    return user.is_superuser or user.groups.filter(name='Kassir').exists()

@login_required
def kassa(request):
    query = request.GET.get('q', '')
    now = timezone.now()
    # faqat faol mahsulotlar
    products_qs = Product.objects.filter(start_date__lte=now).filter(Q(end_date__isnull=True) | Q(end_date__gte=now))
    if query:
        products_qs = products_qs.filter(Q(desc__icontains=query) | Q(barcode__icontains=query))
    products = products_qs

    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    for product_id, quantity in cart.items():
        product = Product.objects.get(pk=product_id)
        item_total = product.s_price * quantity
        total += item_total
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'item_total': item_total
        })
    return render(request, 'market/kassa.html', {
        'products': products,
        'cart_items': cart_items,
        'total': total,
        'query': query,
    })

@login_required
def cart_add(request, product_id):
    product = Product.objects.get(pk=product_id)
    # Muddatini tekshiramiz!
    if not product.is_active():
        messages.error(request, "Bu mahsulot muddati tugagan va sotib bo‘lmaydi!")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            cart_items = []
            total = 0
            cart = request.session.get('cart', {})
            for pid, qty in cart.items():
                p = Product.objects.get(pk=pid)
                item_total = p.s_price * qty
                total += item_total
                cart_items.append({
                    'product': p,
                    'quantity': qty,
                    'item_total': item_total
                })
            html = render_to_string('market/_cart_partial.html', {
                'cart_items': cart_items,
                'total': total,
            }, request=request)
            return JsonResponse({'cart_html': html, 'message': "Bu mahsulot muddati tugagan va sotib bo‘lmaydi!"})
        return redirect('kassa')

    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    request.session['cart'] = cart
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_items = []
        total = 0
        for pid, qty in cart.items():
            p = Product.objects.get(pk=pid)
            item_total = p.s_price * qty
            total += item_total
            cart_items.append({
                'product': p,
                'quantity': qty,
                'item_total': item_total
            })
        html = render_to_string('market/_cart_partial.html', {
            'cart_items': cart_items,
            'total': total,
        }, request=request)
        return JsonResponse({'cart_html': html})
    return redirect('kassa')

@login_required
def cart_remove(request, product_id):
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
    request.session['cart'] = cart
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_items = []
        total = 0
        for pid, qty in cart.items():
            product = Product.objects.get(pk=pid)
            item_total = product.s_price * qty
            total += item_total
            cart_items.append({
                'product': product,
                'quantity': qty,
                'item_total': item_total
            })
        html = render_to_string('market/_cart_partial.html', {
            'cart_items': cart_items,
            'total': total,
        }, request=request)
        return JsonResponse({'cart_html': html})
    return redirect('kassa')

@login_required
def cart_clear(request):
    request.session['cart'] = {}
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_items = []
        total = 0
        html = render_to_string('market/_cart_partial.html', {
            'cart_items': cart_items,
            'total': total,
        }, request=request)
        return JsonResponse({'cart_html': html})
    return redirect('kassa')

@login_required
def cart_checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        msg = "Savat bo'sh!"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            cart_items = []
            total = 0
            html = render_to_string('market/_cart_partial.html', {
                'cart_items': cart_items,
                'total': total,
            }, request=request)
            return JsonResponse({'cart_html': html, 'message': msg})
        messages.error(request, msg)
        return redirect('kassa')

    # Ombordagi qolgan miqdorni va muddatini tekshirish
    error_msg = None
    for product_id, quantity in cart.items():
        product = Product.objects.get(pk=product_id)
        if not product.is_active():
            error_msg = f"Mahsulot '{product.desc}' muddati tugagan!"
            break
        if product.stock < quantity:
            error_msg = f"Mahsulot '{product.desc}' uchun omborda yetarli qoldiq yo‘q! Qolgan: {product.stock} dona."
            break

    if error_msg:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            cart_items = []
            total = 0
            for pid, qty in cart.items():
                p = Product.objects.get(pk=pid)
                item_total = p.s_price * qty
                total += item_total
                cart_items.append({
                    'product': p,
                    'quantity': qty,
                    'item_total': item_total
                })
            html = render_to_string('market/_cart_partial.html', {
                'cart_items': cart_items,
                'total': total,
            }, request=request)
            return JsonResponse({'cart_html': html, 'message': error_msg})
        messages.error(request, error_msg)
        return redirect('kassa')

    # Chek yaratish
    sale = Sale.objects.create(created_by=request.user)
    for product_id, quantity in cart.items():
        product = Product.objects.get(pk=product_id)
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=quantity,
            price=product.s_price
        )
        product.stock -= quantity
        product.save()
    request.session['cart'] = {}
    msg = f"Chek #{sale.id} saqlandi!"
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_items = []
        total = 0
        html = render_to_string('market/_cart_partial.html', {
            'cart_items': cart_items,
            'total': total,
        }, request=request)
        return JsonResponse({'cart_html': html, 'message': msg})
    messages.success(request, msg)
    return redirect('kassa')

# FAQAT KASSIR VA ADMIN KO‘RISHI MUMKIN!
@user_passes_test(is_kassir_or_admin)
def sales_list(request):
    sales = Sale.objects.order_by('-created_at')
    return render(request, 'market/sales_list.html', {'sales': sales})

@user_passes_test(is_kassir_or_admin)
def sale_detail(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.all()
    total_sum = sum([item.quantity * item.price for item in items])
    return render(request, 'market/sale_detail.html', {
        'sale': sale,
        'items': items,
        'total_sum': total_sum
    })
