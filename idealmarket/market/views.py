from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import JsonResponse
from .models import Product, Sale, SaleItem
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test

# ROLLARNI ANIQLASH
def is_kassir_or_admin(user):
    return user.is_superuser or user.groups.filter(name='Kassir').exists()

@login_required
def kassa(request):
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(desc__icontains=query) | Product.objects.filter(barcode__icontains=query)
    else:
        products = Product.objects.all()
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
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
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

    # Ombordagi qolgan miqdorni tekshirish
    error_msg = None
    for product_id, quantity in cart.items():
        product = Product.objects.get(pk=product_id)
        if product.stock < quantity:
            error_msg = f"Mahsulot '{product.desc}' uchun omborda yetarli qoldiq yo‘q! Qolgan: {product.stock} dona."
            break

    if error_msg:
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
            return JsonResponse({'cart_html': html, 'message': error_msg})
        messages.error(request, error_msg)
        return redirect('kassa')

    # **FAQAT BIR MARTA YARATILADI**
    sale = Sale.objects.create(created_by=request.user)
    for product_id, quantity in cart.items():
        product = Product.objects.get(pk=product_id)
        SaleItem.objects.create(
            sale=sale,                # <-- har bir item uchun faqat shu bir xil sale!
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
