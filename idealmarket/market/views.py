from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.views.decorators.http import require_POST
from django.contrib import messages
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.db.models.functions import ExtractHour
from .models import Product, Sale, SaleItem, Ombor, Catagory
from .forms import ProductForm, OmborForm, CatagoryForm
from django.contrib.auth.forms import AdminPasswordChangeForm
import pandas as pd

# ROLLARNI ANIQLASH
def is_kassir_or_admin(user):
    return user.is_superuser or user.groups.filter(name='Kassir').exists()

def home(request):
    return render(request, "index.html")

@user_passes_test(lambda u: u.is_superuser)
def admin_user_change_password(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = AdminPasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Parol muvaffaqiyatli o‘zgartirildi.")
            return redirect('admin_users')
    else:
        form = AdminPasswordChangeForm(user)
    return render(request, 'market/admin_user_change_password.html', {
        'form': form,
        'user_obj': user  # E’TIBOR BER: user_obj
    })


@login_required
def dashboard_redirect(request):
    user = request.user
    if user.is_superuser:
        return redirect('admin_management')
    elif user.groups.filter(name='Kassir').exists():
        return redirect('kassa')
    else:
        return render(request, 'market/access_denied.html', {
            'message': "Sizga kirishga ruxsat yo‘q!"
        })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_management(request):
    # Kerakli admin ma'lumotlar va funksiya
    return render(request, 'market/admin_management.html')


@login_required
def kassa(request):
    query = request.GET.get('q', '')
    now = timezone.now()
    products = Product.objects.filter(
        is_active=True,                           # Faqat faol mahsulotlar!
        start_date__lte=now
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    )
    if query:
        products = products.filter(Q(desc__icontains=query) | Q(barcode__icontains=query))

    # AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        products_html = render_to_string('market/_products_table.html', {'products': products})
        return JsonResponse({'products_html': products_html})

    # Savat hisob-kitobi...
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
    if request.method != "POST":
        return redirect('kassa')

    product = get_object_or_404(Product, pk=product_id)

    # Muddat tugagan mahsulot uchun xatolik
    if not product.is_active:
        msg = "Bu mahsulot muddati tugagan va sotib bo‘lmaydi!"
        return JsonResponse({'message': msg}, status=400)

    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    request.session['cart'] = cart

    # Savat holatini qaytarish
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
        return JsonResponse({'message': 'Noto‘g‘ri amal'}, status=400)
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

    # AJAX (fetch/XHR) orqali so‘rov keldi
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
        return JsonResponse({'cart_html': html, 'message': "Mahsulot o‘chirildi!"})

    # Oddiy so‘rov bo‘lsa
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

@user_passes_test(is_kassir_or_admin)
def sales_list(request):
    sales = Sale.objects.order_by('-created_at').select_related('created_by')
    sales_data = []
    for sale in sales:
        total_sum = sum([item.quantity * item.price for item in sale.items.all()])
        sales_data.append({
            'id': sale.id,
            'created_at': sale.created_at,
            'created_by': sale.created_by,
            'total_sum': total_sum,
        })
    return render(request, 'market/sales_list.html', {
        'sales_data': sales_data,
    })


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

@user_passes_test(is_kassir_or_admin)
def export_sales_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="cheklar.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, height - 40, "Cheklar Tarixi (Sales History)")
    y = height - 70
    p.setFont("Helvetica", 10)
    p.drawString(30, y, "ID")
    p.drawString(70, y, "Sana")
    p.drawString(160, y, "Foydalanuvchi")
    p.drawString(250, y, "Umumiy summa")
    y -= 15

    sales = Sale.objects.order_by('-created_at')
    for sale in sales:
        p.drawString(30, y, str(sale.id))
        p.drawString(70, y, sale.created_at.strftime('%Y-%m-%d %H:%M'))
        p.drawString(160, y, sale.created_by.username if sale.created_by else "-")
        p.drawString(250, y, str(sale.total_sum))
        y -= 14
        if y < 40:
            p.showPage()
            y = height - 40

    p.save()
    return response

@user_passes_test(is_kassir_or_admin)
def export_statistics_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="statistika.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, height-40, "Statistika va Hisobotlar")
    y = height - 70

    # Eng ko‘p sotilgan mahsulotlar
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, "Eng ko‘p sotilgan mahsulotlar")
    y -= 20
    p.setFont("Helvetica", 10)

    stats = (
        SaleItem.objects.values('product__desc')
        .annotate(total=Sum('quantity'))
        .order_by('-total')[:10]
    )
    p.drawString(30, y, "Mahsulot"); p.drawString(250, y, "Soni")
    y -= 16
    for row in stats:
        p.drawString(30, y, row['product__desc'][:30])
        p.drawString(250, y, str(row['total']))
        y -= 14
        if y < 40: p.showPage(); y = height - 40

    p.save()
    return response

@user_passes_test(is_kassir_or_admin)
def export_statistics_excel(request):
    stats = (
        SaleItem.objects.values('product__desc')
        .annotate(total=Sum('quantity'))
        .order_by('-total')[:10]
    )
    df = pd.DataFrame(list(stats))
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="statistika.xlsx"'
    df.to_excel(response, index=False)
    return response


def admin_products(request):
    products = Product.objects.all().order_by('-id')
    categories = Catagory.objects.all()
    query = request.GET.get('q', '')
    cat_id = request.GET.get('cat')
    show_all = request.GET.get('show_all', '')

    # Faqat faol mahsulotlarni ko'rsatish (superuser bo'lmasa yoki show_all bo'lmasa)
    if not show_all:
        products = products.filter(is_active=True)
    if query:
        products = products.filter(Q(desc__icontains=query) | Q(barcode__icontains=query))
    if cat_id:
        products = products.filter(catagory_id=cat_id)

    context = {
        'products': products,
        'categories': categories
    }
    return render(request, 'market/admin_products.html', context)



#admin praduct
@user_passes_test(lambda u: u.is_superuser)
def admin_product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_products')
    else:
        form = ProductForm()
    return render(request, 'market/admin_product_form.html', {'form': form})


@user_passes_test(lambda u: u.is_superuser)
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('admin_products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'market/admin_product_form.html', {'form': form, 'product': product})



@user_passes_test(lambda u: u.is_superuser)
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('admin_products')
    return render(request, 'market/admin_product_confirm_delete.html', {'product': product})

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def admin_product_bulk_delete(request):
    ids = request.POST.getlist('selected_products')
    if not ids:
        messages.warning(request, "Hech qanaqa mahsulot tanlanmadi.")
        return redirect('admin_products')

    products = Product.objects.filter(id__in=ids)
    deleted_count = 0
    archived_count = 0

    for product in products:
        if SaleItem.objects.filter(product=product).exists():
            product.is_active = False
            product.save()
            archived_count += 1
        else:
            product.delete()
            deleted_count += 1

    if deleted_count > 0:
        messages.success(request, f"{deleted_count} ta mahsulot to‘liq o‘chirildi!")
    if archived_count > 0:
        messages.warning(request, f"{archived_count} ta mahsulot arxivlandi (faolsizlantirildi), chunki sotuvlarda ishlatilgan.")

    return redirect('admin_products')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_categories(request):
    categories = Catagory.objects.all()
    return render(request, 'market/admin_categories.html', {'categories': categories})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_category_add(request):
    if request.method == 'POST':
        form = CatagoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_categories')
    else:
        form = CatagoryForm()
    return render(request, 'market/admin_category_form.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_category_edit(request, pk):
    category = get_object_or_404(Catagory, pk=pk)
    if request.method == 'POST':
        form = CatagoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('admin_categories')
    else:
        form = CatagoryForm(instance=category)
    return render(request, 'market/admin_category_form.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_category_delete(request, pk):
    category = get_object_or_404(Catagory, pk=pk)
    if request.method == 'POST':
        category.delete()
        return redirect('admin_categories')
    return render(request, 'market/admin_category_confirm_delete.html', {'category': category})

#Users
@user_passes_test(lambda u: u.is_superuser)
def admin_users(request):
    users = User.objects.all().order_by('-is_superuser', 'username')
    return render(request, 'market/admin_users.html', {'users': users})

@user_passes_test(lambda u: u.is_superuser)
def admin_user_add(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        role = request.POST.get('role')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Bunday login mavjud!")
        else:
            user = User.objects.create_user(username=username, password=password, first_name=first_name, last_name=last_name)
            if role == 'kassir':
                group, created = Group.objects.get_or_create(name='Kassir')
                user.groups.add(group)
            elif role == 'admin':
                user.is_superuser = True
                user.is_staff = True
                user.save()
            return redirect('admin_users')
    return render(request, 'market/admin_user_add.html')

@user_passes_test(lambda u: u.is_superuser)
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        user.username = request.POST.get('username')
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        role = request.POST.get('role')
        user.groups.clear()
        user.is_superuser = False
        user.is_staff = False
        if role == 'kassir':
            group, created = Group.objects.get_or_create(name='Kassir')
            user.groups.add(group)
        elif role == 'admin':
            user.is_superuser = True
            user.is_staff = True
        user.save()
        return redirect('admin_users')
    return render(request, 'market/admin_user_edit.html', {'user_obj': user})

@user_passes_test(lambda u: u.is_superuser)
def admin_user_delete(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        user.delete()
        return redirect('admin_users')
    return render(request, 'market/admin_user_confirm_delete.html', {'user_obj': user})

#group
@user_passes_test(lambda u: u.is_superuser)
def admin_groups(request):
    groups = Group.objects.all().order_by('name')
    return render(request, 'market/admin_groups.html', {'groups': groups})

@user_passes_test(lambda u: u.is_superuser)
def admin_group_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if Group.objects.filter(name=name).exists():
            messages.error(request, "Bu nomli group bor!")
        else:
            Group.objects.create(name=name)
            return redirect('admin_groups')
    return render(request, 'market/admin_group_add.html')

@user_passes_test(lambda u: u.is_superuser)
def admin_group_edit(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        group.name = name
        group.save()
        return redirect('admin_groups')
    return render(request, 'market/admin_group_edit.html', {'group': group})

@user_passes_test(lambda u: u.is_superuser)
def admin_group_delete(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if request.method == 'POST':
        group.delete()
        return redirect('admin_groups')
    return render(request, 'market/admin_group_confirm_delete.html', {'group': group})

# Sotuvlar
@user_passes_test(lambda u: u.is_superuser)
def admin_sales(request):
    sales = Sale.objects.select_related('created_by').order_by('-created_at')
    return render(request, 'market/admin_sales.html', {'sales': sales})

@user_passes_test(lambda u: u.is_superuser)
def admin_sale_detail(request, sale_id):
    sale = get_object_or_404(Sale, pk=sale_id)
    items = sale.items.select_related('product')
    return render(request, 'market/admin_sale_detail.html', {'sale': sale, 'items': items})

@user_passes_test(lambda u: u.is_superuser)
def admin_sale_delete(request, sale_id):
    sale = get_object_or_404(Sale, pk=sale_id)
    if request.method == 'POST':
        sale.delete()
        return redirect('admin_sales')
    return render(request, 'market/admin_sale_confirm_delete.html', {'sale': sale})


#ombor
@login_required
@user_passes_test(is_kassir_or_admin)
def admin_ombors(request):
    ombors = Ombor.objects.all()
    return render(request, 'market/admin_ombors.html', {'ombors': ombors})

@login_required
@user_passes_test(is_kassir_or_admin)
def admin_ombor_add(request):
    if request.method == 'POST':
        form = OmborForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_ombors')
    else:
        form = OmborForm()
    return render(request, 'market/admin_ombor_add.html', {'form': form})

@login_required
@user_passes_test(is_kassir_or_admin)
def admin_ombor_edit(request, pk):
    ombor = get_object_or_404(Ombor, pk=pk)
    if request.method == 'POST':
        form = OmborForm(request.POST, instance=ombor)
        if form.is_valid():
            form.save()
            return redirect('admin_ombors')
    else:
        form = OmborForm(instance=ombor)
    return render(request, 'market/admin_ombor_edit.html', {'form': form, 'ombor': ombor})

@login_required
@user_passes_test(is_kassir_or_admin)
def admin_ombor_delete(request, pk):
    ombor = get_object_or_404(Ombor, pk=pk)
    if request.method == 'POST':
        ombor.delete()
        return redirect('admin_ombors')
    return render(request, 'market/admin_ombor_confirm_delete.html', {'ombor': ombor})

def management_product_import(request):
    if request.method == "POST":
        import pandas as pd
        file = request.FILES['file']
        try:
            df = pd.read_json(file)
        except Exception as e:
            return HttpResponse("JSON faylni o‘qib bo‘lmadi: " + str(e))
        for _, row in df.iterrows():
            # Kategoriya va Ombor nomi orqali id ni topamiz
            from .models import Catagory, Ombor
            try:
                catagory_obj = Catagory.objects.get(name=row['catagory'])
                ombor_obj = Ombor.objects.get(name=row['ombor'])
            except Catagory.DoesNotExist:
                return HttpResponse(f"Kategoriya topilmadi: {row['catagory']}")
            except Ombor.DoesNotExist:
                return HttpResponse(f"Ombor topilmadi: {row['ombor']}")
            Product.objects.update_or_create(
                barcode=row['barcode'],
                defaults={
                    'catagory': catagory_obj,
                    'ombor': ombor_obj,
                    'desc': row.get('desc', ''),
                    'r_price': row.get('r_price', 0),
                    's_price': row.get('s_price', 0),
                    'stock': row.get('stock', 0),
                    'start_date': row.get('start_date', None),
                    'end_date': row.get('end_date', None),
                }
            )
        return redirect('admin_products')
    return HttpResponse("Faqat POST so‘rov!", status=405)




def management_product_export(request):
    import pandas as pd
    products = Product.objects.filter(is_active=True).values(
        'id', 'catagory_id', 'ombor_id', 'barcode', 'desc', 'r_price', 's_price', 'stock', 'start_date', 'end_date'
    )
    df = pd.DataFrame(list(products))
    response = HttpResponse(content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="products_export.json"'
    response.write(df.to_json(orient='records'))
    return response


def management_category_import(request):
    if request.method == "POST":
        import pandas as pd
        file = request.FILES['file']
        try:
            df = pd.read_json(file)
        except Exception as e:
            return HttpResponse("JSON faylni o‘qib bo‘lmadi: " + str(e))

        for _, row in df.iterrows():
            Catagory.objects.update_or_create(
                name=row['name'],
                defaults={
                    'desc': row.get('desc', '')
                }
            )
        return redirect('admin_categories')
    return HttpResponse("Faqat POST so‘rov!", status=405)

def management_category_export(request):
    import pandas as pd
    categories = Catagory.objects.all().values('id', 'name', 'desc')
    df = pd.DataFrame(list(categories))
    response = HttpResponse(content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="categories_export.json"'
    response.write(df.to_json(orient='records'))
    return response
