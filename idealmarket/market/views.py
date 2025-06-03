from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import JsonResponse
from .models import Product, Sale, SaleItem
from django.contrib import messages

from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

from django.db.models import Count, Sum
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import user_passes_test


# ROLLARNI ANIQLASH
def is_kassir_or_admin(user):
    return user.is_superuser or user.groups.filter(name='Kassir').exists()


@login_required
def kassa(request):
    query = request.GET.get('q', '')
    now = timezone.now()
    products_qs = Product.objects.filter(start_date__lte=now).filter(Q(end_date__isnull=True) | Q(end_date__gte=now))
    if query:
        products_qs = products_qs.filter(Q(desc__icontains=query) | Q(barcode__icontains=query))
    products = products_qs

    # AJAX so‘rov bo‘lsa
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        products_html = render_to_string('market/_products_table.html', {'products': products})
        return JsonResponse({'products_html': products_html})

    # Oddiy sahifa
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
@login_required
def cart_add(request, product_id):
    if request.method != "POST":
        return redirect('kassa')

    product = Product.objects.get(pk=product_id)
    if not product.is_active:
        msg = "Bu mahsulot muddati tugagan va sotib bo‘lmaydi!"
        return JsonResponse(
            {'message': msg, 'cart_html': render_to_string('market/_cart_partial.html', {}, request=request)})

    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    request.session['cart'] = cart

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

    return JsonResponse({'cart_html': html, 'message': "Mahsulot qo'shildi!"})


@login_required
@require_POST
def cart_update(request, product_id):
    action = request.POST.get('action')
    cart = request.session.get('cart', {})

    if action not in ['add', 'remove']:
        return JsonResponse({'message': 'Noto\'g\'ri amal'}, status=400)

    product = get_object_or_404(Product, pk=product_id)

    if action == 'add':
        if not product.is_active:
            return JsonResponse({'message': "Bu mahsulot muddati tugagan!"}, status=400)
        cart[str(product_id)] = cart.get(str(product_id), 0) + 1

    elif action == 'remove':
        if str(product_id) in cart:
            cart[str(product_id)] -= 1
            if cart[str(product_id)] <= 0:
                del cart[str(product_id)]

    request.session['cart'] = cart

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

    return JsonResponse({'cart_html': html, 'message': 'Savat yangilandi!'})


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
    if request.method == "POST":
        request.session['cart'] = {}
        cart_items = []
        total = 0
        html = render_to_string('market/_cart_partial.html', {
            'cart_items': cart_items,
            'total': total,
        }, request=request)
        return JsonResponse({'cart_html': html, 'message': "Savat tozalandi!"})
    return JsonResponse({'message': "Noto'g'ri so'rov."}, status=400)


@login_required
def cart_checkout(request):
    if request.method == "POST":
        cart = request.session.get('cart', {})
        if not cart:
            html = render_to_string('market/_cart_partial.html', {
                'cart_items': [],
                'total': 0,
            }, request=request)
            return JsonResponse({'cart_html': html, 'message': "Savat bo'sh!"}, status=400)

        error_msg = None
        for product_id, quantity in cart.items():
            product = Product.objects.get(pk=product_id)
            if not product.is_active:
                error_msg = f"{product.desc} muddati tugagan!"
                break
            if product.stock < quantity:
                error_msg = f"{product.desc} yetarli emas, qolgan: {product.stock}"
                break

        if error_msg:
            cart_items = []
            total = 0
            for pid, qty in cart.items():
                p = Product.objects.get(pk=pid)
                cart_items.append({
                    'product': p,
                    'quantity': qty,
                    'item_total': p.s_price * qty
                })
                total += p.s_price * qty
            html = render_to_string('market/_cart_partial.html', {
                'cart_items': cart_items,
                'total': total,
            }, request=request)
            return JsonResponse({'cart_html': html, 'message': error_msg}, status=400)

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
        html = render_to_string('market/_cart_partial.html', {
            'cart_items': [],
            'total': 0,
        }, request=request)
        return JsonResponse({'cart_html': html, 'message': f"Chek #{sale.id} saqlandi!"})

    return JsonResponse({'message': "Noto'g'ri so'rov."}, status=400)


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



from django.db.models.functions import ExtractHour

@user_passes_test(is_kassir_or_admin)
def statistics(request):
    category_stats = (
        SaleItem.objects
        .values('product__catagory__name')
        .annotate(total_sales=Sum('quantity'), total_sum=Sum('price'))
        .order_by('-total_sales')
    )
    product_stats = (
        SaleItem.objects
        .values('product__desc')
        .annotate(total_sales=Sum('quantity'), total_sum=Sum('price'))
        .order_by('-total_sales')[:10]
    )
    kassir_stats = (
        Sale.objects
        .values('created_by__username')
        .annotate(total_cheks=Count('id'), total_sum=Sum('items__price'))
        .order_by('-total_cheks')
    )
    date_stats = (
        Sale.objects
        .values('created_at__date')
        .annotate(total_cheks=Count('id'), total_sum=Sum('items__price'))
        .order_by('-created_at__date')
    )
    hour_stats = (
        Sale.objects
        .annotate(hour=ExtractHour('created_at'))
        .values('hour')
        .annotate(total_cheks=Count('id'))
        .order_by('-total_cheks')
    )
    now = timezone.now().date()
    expired_products = Product.objects.filter(end_date__lt=now)

    return render(request, 'market/statistics.html', {
        'category_stats': category_stats,
        'product_stats': product_stats,
        'kassir_stats': kassir_stats,
        'date_stats': date_stats,
        'hour_stats': hour_stats,
        'expired_products': expired_products,
    })