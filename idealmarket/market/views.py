from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.models import Group, User
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractHour
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import pandas as pd

from .forms import CatagoryForm, OmborForm, ProductForm
from .models import Catagory, Ombor, Product, Sale, SaleItem


# ==== Permissions ====

def is_admin(user: User) -> bool:
    """Return True if user is superuser."""
    return user.is_superuser


def is_kassir_or_admin(user: User) -> bool:
    """Return True for cashier or admin users."""
    return user.is_superuser or user.groups.filter(name="Kassir").exists()


# ==== Helpers ====

def _get_cart(request) -> dict:
    cart = request.session.get("cart", {})
    request.session.setdefault("cart", cart)
    return cart


def _save_cart(request, cart: dict) -> None:
    request.session["cart"] = cart
    request.session.modified = True


def _cart_items_and_total(cart: dict) -> tuple[list[dict], float]:
    items = []
    total = 0
    for pid, qty in cart.items():
        product = get_object_or_404(Product, pk=pid)
        subtotal = product.s_price * qty
        items.append({"product": product, "quantity": qty, "subtotal": subtotal})
        total += subtotal
    return items, total


def _render_cart(request) -> str:
    items, total = _cart_items_and_total(_get_cart(request))
    return render_to_string(
        "market/_cart_partial.html", {"cart_items": items, "total": total}, request=request
    )


def _render_products(request, products) -> str:
    return render_to_string(
        "market/_products_table.html", {"products": products}, request=request
    )


# ==== Public Views ====

def home(request):
    """Landing page."""
    return render(request, "index.html")


@login_required
def dashboard_redirect(request):
    """Redirect user to proper dashboard based on role."""
    if request.user.is_superuser:
        return redirect("admin_management")
    if request.user.groups.filter(name="Kassir").exists():
        return redirect("kassa")
    return render(request, "market/access_denied.html", {"message": "Ruxsat yo'q"})


# ==== Cashier and Cart ====

@login_required
def kassa(request):
    """Cashier page with product search and cart."""
    query = request.GET.get("q", "")
    now = timezone.now()
    products = (
        Product.objects.filter(is_active=True, start_date__lte=now)
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=now))
        .order_by("-id")
    )
    if query:
        products = products.filter(Q(desc__icontains=query) | Q(barcode__icontains=query))

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"products_html": _render_products(request, products)})

    cart_html = _render_cart(request)
    return render(
        request,
        "market/kassa.html",
        {"products": products, "cart_html": cart_html, "query": query},
    )


@login_required
@require_POST
def cart_add(request, product_id: int):
    """Add product to cart."""
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = _get_cart(request)
    quantity = int(request.POST.get("quantity", 1))
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    _save_cart(request, cart)
    return JsonResponse({"cart_html": _render_cart(request)})


@login_required
@require_POST
def cart_update(request, product_id: int):
    """Increase or decrease product quantity."""
    action = request.POST.get("action")
    cart = _get_cart(request)
    if action == "add":
        cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    elif action == "remove" and str(product_id) in cart:
        cart[str(product_id)] -= 1
        if cart[str(product_id)] <= 0:
            del cart[str(product_id)]
    else:
        return JsonResponse({"error": "Noto'g'ri amal"}, status=400)
    _save_cart(request, cart)
    return JsonResponse({"cart_html": _render_cart(request)})


@login_required
@require_POST
def cart_remove(request, product_id: int):
    """Remove product from cart."""
    cart = _get_cart(request)
    cart.pop(str(product_id), None)
    _save_cart(request, cart)
    return JsonResponse({"cart_html": _render_cart(request)})


@login_required
@require_POST
def cart_clear(request):
    """Empty the cart."""
    _save_cart(request, {})
    return JsonResponse({"cart_html": _render_cart(request)})


@login_required
@require_POST
def cart_checkout(request):
    """Create sale from cart."""
    cart = _get_cart(request)
    if not cart:
        return JsonResponse({"error": "Savat bo'sh"}, status=400)

    for pid, qty in cart.items():
        product = get_object_or_404(Product, pk=pid)
        if not product.is_available or product.stock < qty:
            return JsonResponse({"error": f"{product.desc} mavjud emas"}, status=400)

    sale = Sale.objects.create(created_by=request.user)
    for pid, qty in cart.items():
        product = Product.objects.get(pk=pid)
        SaleItem.objects.create(sale=sale, product=product, quantity=qty, price=product.s_price)
        product.stock -= qty
        product.save()

    _save_cart(request, {})
    return JsonResponse({"cart_html": _render_cart(request), "message": f"Chek #{sale.id} saqlandi"})


# ==== Sales and Statistics ====

@login_required
@user_passes_test(is_kassir_or_admin)
def sales_list(request):
    """List of sales."""
    sales = Sale.objects.select_related("created_by").order_by("-created_at")
    return render(request, "market/sales_list.html", {"sales": sales})


@login_required
@user_passes_test(is_kassir_or_admin)
def sale_detail(request, pk: int):
    """Sale detail."""
    sale = get_object_or_404(Sale, pk=pk)
    return render(request, "market/sale_detail.html", {"sale": sale})


@login_required
@user_passes_test(is_kassir_or_admin)
def statistics(request):
    """Sales statistics."""
    category_stats = (
        SaleItem.objects.values("product__catagory__name")
        .annotate(total_sales=Sum("quantity"), total_sum=Sum("price"))
        .order_by("-total_sales")
    )
    product_stats = (
        SaleItem.objects.values("product__desc")
        .annotate(total_sales=Sum("quantity"), total_sum=Sum("price"))
        .order_by("-total_sales")
    )
    kassir_stats = (
        Sale.objects.values("created_by__username")
        .annotate(total_cheks=Count("id"), total_sum=Sum("items__price"))
        .order_by("-total_cheks")
    )
    date_stats = (
        Sale.objects.values("created_at__date")
        .annotate(total_cheks=Count("id"), total_sum=Sum("items__price"))
        .order_by("-created_at__date")
    )
    hour_stats = (
        Sale.objects.annotate(hour=ExtractHour("created_at"))
        .values("hour")
        .annotate(total_cheks=Count("id"))
        .order_by("-total_cheks")
    )
    expired_products = Product.objects.filter(end_date__lt=timezone.now().date())
    context = {
        "category_stats": category_stats,
        "product_stats": product_stats,
        "kassir_stats": kassir_stats,
        "date_stats": date_stats,
        "hour_stats": hour_stats,
        "expired_products": expired_products,
    }
    return render(request, "market/statistics.html", context)


@login_required
@user_passes_test(is_kassir_or_admin)
def export_sales_pdf(request):
    """Export sales to PDF."""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="cheklar.pdf"'
    c = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, height - 40, "Cheklar Tarixi")
    y = height - 70
    c.setFont("Helvetica", 10)
    c.drawString(30, y, "ID")
    c.drawString(70, y, "Sana")
    c.drawString(160, y, "Foydalanuvchi")
    c.drawString(250, y, "Umumiy summa")
    y -= 15
    for sale in Sale.objects.order_by("-created_at"):
        c.drawString(30, y, str(sale.id))
        c.drawString(70, y, sale.created_at.strftime("%Y-%m-%d %H:%M"))
        c.drawString(160, y, sale.created_by.username if sale.created_by else "-")
        c.drawString(250, y, str(sale.total_sum))
        y -= 14
        if y < 40:
            c.showPage()
            y = height - 40
    c.save()
    return response


@login_required
@user_passes_test(is_kassir_or_admin)
def export_statistics_pdf(request):
    """Export statistics to PDF."""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="statistika.pdf"'
    c = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, height - 40, "Statistika")
    y = height - 70
    c.setFont("Helvetica", 10)
    stats = (
        SaleItem.objects.values("product__desc").annotate(total=Sum("quantity")).order_by("-total")[:10]
    )
    c.drawString(30, y, "Mahsulot")
    c.drawString(250, y, "Soni")
    y -= 16
    for row in stats:
        c.drawString(30, y, row["product__desc"][:30])
        c.drawString(250, y, str(row["total"]))
        y -= 14
        if y < 40:
            c.showPage()
            y = height - 40
    c.save()
    return response


@login_required
@user_passes_test(is_kassir_or_admin)
def export_statistics_excel(request):
    """Export statistics to Excel."""
    stats = (
        SaleItem.objects.values("product__desc").annotate(total=Sum("quantity")).order_by("-total")[:10]
    )
    df = pd.DataFrame(list(stats))
    response = HttpResponse(content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = 'attachment; filename="statistika.xlsx"'
    df.to_excel(response, index=False)
    return response


# ==== Admin Management ====

@login_required
@user_passes_test(is_admin)
def admin_management(request):
    """Simple admin dashboard."""
    return render(request, "market/admin_management.html")


# -- Products --

@login_required
@user_passes_test(is_admin)
def admin_products(request):
    """Product list with search and filters."""
    products = Product.objects.all().order_by("-id")
    query = request.GET.get("q")
    if query:
        products = products.filter(Q(desc__icontains=query) | Q(barcode__icontains=query))
    cat_id = request.GET.get("category")
    if cat_id:
        products = products.filter(catagory_id=cat_id)
    ombor_id = request.GET.get("ombor")
    if ombor_id:
        products = products.filter(ombor_id=ombor_id)
    context = {
        "products": products,
        "categories": Catagory.objects.all(),
        "ombors": Ombor.objects.all(),
    }
    return render(request, "market/admin_products.html", context)


@login_required
@user_passes_test(is_admin)
def admin_product_add(request):
    """Create new product."""
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("admin_products")
    return render(request, "market/admin_product_form.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def admin_product_edit(request, pk: int):
    """Update product."""
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("admin_products")
    return render(request, "market/admin_product_form.html", {"form": form, "product": product})


@login_required
@user_passes_test(is_admin)
def admin_product_delete(request, pk: int):
    """Delete product if not used in sales."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        if SaleItem.objects.filter(product=product).exists():
            product.is_active = False
            product.save()
            messages.warning(request, "Mahsulot arxivlandi")
        else:
            product.delete()
            messages.success(request, "Mahsulot o'chirildi")
        return redirect("admin_products")
    return render(request, "market/admin_product_confirm_delete.html", {"product": product})


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_product_bulk_delete(request):
    """Bulk delete or archive products."""
    ids = request.POST.getlist("ids")
    products = Product.objects.filter(id__in=ids)
    deleted = 0
    archived = 0
    for product in products:
        if SaleItem.objects.filter(product=product).exists():
            product.is_active = False
            product.save()
            archived += 1
        else:
            product.delete()
            deleted += 1
    if deleted:
        messages.success(request, f"{deleted} ta mahsulot o'chirildi")
    if archived:
        messages.warning(request, f"{archived} ta mahsulot arxivlandi")
    return redirect("admin_products")


# -- Categories --

@login_required
@user_passes_test(is_admin)
def admin_categories(request):
    """List of categories."""
    categories = Catagory.objects.all()
    return render(request, "market/admin_categories.html", {"categories": categories})


@login_required
@user_passes_test(is_admin)
def admin_category_add(request):
    """Add new category."""
    form = CatagoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("admin_categories")
    return render(request, "market/admin_category_form.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def admin_category_edit(request, pk: int):
    """Edit category."""
    category = get_object_or_404(Catagory, pk=pk)
    form = CatagoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("admin_categories")
    return render(request, "market/admin_category_form.html", {"form": form, "category": category})


@login_required
@user_passes_test(is_admin)
def admin_category_delete(request, pk: int):
    """Delete category."""
    category = get_object_or_404(Catagory, pk=pk)
    if request.method == "POST":
        category.delete()
        return redirect("admin_categories")
    return render(request, "market/admin_category_confirm_delete.html", {"category": category})


# -- Warehouses --

@login_required
@user_passes_test(is_admin)
def admin_ombors(request):
    """List of warehouses."""
    ombors = Ombor.objects.all()
    return render(request, "market/admin_ombors.html", {"ombors": ombors})


@login_required
@user_passes_test(is_admin)
def admin_ombor_add(request):
    """Add new warehouse."""
    form = OmborForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("admin_ombors")
    return render(request, "market/admin_ombor_form.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def admin_ombor_edit(request, pk: int):
    """Edit warehouse."""
    ombor = get_object_or_404(Ombor, pk=pk)
    form = OmborForm(request.POST or None, instance=ombor)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("admin_ombors")
    return render(request, "market/admin_ombor_form.html", {"form": form, "ombor": ombor})


@login_required
@user_passes_test(is_admin)
def admin_ombor_delete(request, pk: int):
    """Delete warehouse."""
    ombor = get_object_or_404(Ombor, pk=pk)
    if request.method == "POST":
        ombor.delete()
        return redirect("admin_ombors")
    return render(request, "market/admin_ombor_confirm_delete.html", {"ombor": ombor})


# -- Users and Groups --

@login_required
@user_passes_test(is_admin)
def admin_users(request):
    """List of users."""
    users = User.objects.all().order_by("-is_superuser", "username")
    return render(request, "market/admin_users.html", {"users": users})


@login_required
@user_passes_test(is_admin)
def admin_user_add(request):
    """Create new user."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")
        role = request.POST.get("role")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Bunday foydalanuvchi bor")
        else:
            user = User.objects.create_user(
                username=username, password=password, first_name=first_name, last_name=last_name
            )
            if role == "kassir":
                group, _ = Group.objects.get_or_create(name="Kassir")
                user.groups.add(group)
            elif role == "admin":
                user.is_superuser = True
                user.is_staff = True
                user.save()
            return redirect("admin_users")
    return render(request, "market/admin_user_add.html")


@login_required
@user_passes_test(is_admin)
def admin_user_edit(request, user_id: int):
    """Edit user."""
    user_obj = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        user_obj.username = request.POST.get("username")
        user_obj.first_name = request.POST.get("first_name", "")
        user_obj.last_name = request.POST.get("last_name", "")
        role = request.POST.get("role")
        user_obj.groups.clear()
        user_obj.is_superuser = False
        user_obj.is_staff = False
        if role == "kassir":
            group, _ = Group.objects.get_or_create(name="Kassir")
            user_obj.groups.add(group)
        elif role == "admin":
            user_obj.is_superuser = True
            user_obj.is_staff = True
        user_obj.save()
        return redirect("admin_users")
    return render(request, "market/admin_user_edit.html", {"user_obj": user_obj})


@login_required
@user_passes_test(is_admin)
def admin_user_delete(request, user_id: int):
    """Delete user."""
    user_obj = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        user_obj.delete()
        return redirect("admin_users")
    return render(request, "market/admin_user_confirm_delete.html", {"user_obj": user_obj})


@login_required
@user_passes_test(is_admin)
def admin_user_change_password(request, user_id: int):
    """Change user password."""
    user_obj = get_object_or_404(User, pk=user_id)
    form = AdminPasswordChangeForm(user_obj, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Parol o'zgartirildi")
        return redirect("admin_users")
    return render(request, "market/admin_user_change_password.html", {"form": form, "user_obj": user_obj})


@login_required
@user_passes_test(is_admin)
def admin_groups(request):
    """List of groups."""
    groups = Group.objects.all().order_by("name")
    return render(request, "market/admin_groups.html", {"groups": groups})


@login_required
@user_passes_test(is_admin)
def admin_group_add(request):
    """Add new group."""
    if request.method == "POST":
        name = request.POST.get("name")
        if Group.objects.filter(name=name).exists():
            messages.error(request, "Bu nomli guruh bor")
        else:
            Group.objects.create(name=name)
            return redirect("admin_groups")
    return render(request, "market/admin_group_add.html")


@login_required
@user_passes_test(is_admin)
def admin_group_edit(request, group_id: int):
    """Edit group."""
    group = get_object_or_404(Group, pk=group_id)
    if request.method == "POST":
        group.name = request.POST.get("name")
        group.save()
        return redirect("admin_groups")
    return render(request, "market/admin_group_edit.html", {"group": group})


@login_required
@user_passes_test(is_admin)
def admin_group_delete(request, group_id: int):
    """Delete group."""
    group = get_object_or_404(Group, pk=group_id)
    if request.method == "POST":
        group.delete()
        return redirect("admin_groups")
    return render(request, "market/admin_group_confirm_delete.html", {"group": group})


# -- Sales management in admin --

@login_required
@user_passes_test(is_admin)
def admin_sales(request):
    """List sales in admin."""
    sales = Sale.objects.select_related("created_by").order_by("-created_at")
    return render(request, "market/admin_sales.html", {"sales": sales})


@login_required
@user_passes_test(is_admin)
def admin_sale_detail(request, sale_id: int):
    """Detail of a sale."""
    sale = get_object_or_404(Sale, pk=sale_id)
    items = sale.items.select_related("product")
    return render(request, "market/admin_sale_detail.html", {"sale": sale, "items": items})


@login_required
@user_passes_test(is_admin)
def admin_sale_delete(request, sale_id: int):
    """Delete sale."""
    sale = get_object_or_404(Sale, pk=sale_id)
    if request.method == "POST":
        sale.delete()
        return redirect("admin_sales")
    return render(request, "market/admin_sale_confirm_delete.html", {"sale": sale})


# ==== Import/Export ====

@login_required
@user_passes_test(is_admin)
@require_POST
def management_product_import(request):
    """Import products from JSON."""
    file = request.FILES.get("file")
    if not file:
        return HttpResponse("Fayl topilmadi", status=400)
    df = pd.read_json(file)
    for _, row in df.iterrows():
        cat = Catagory.objects.get(name=row["catagory"])
        omb = Ombor.objects.get(name=row["ombor"])
        Product.objects.update_or_create(
            barcode=row["barcode"],
            defaults={
                "catagory": cat,
                "ombor": omb,
                "desc": row.get("desc", ""),
                "r_price": row.get("r_price", 0),
                "s_price": row.get("s_price", 0),
                "stock": row.get("stock", 0),
                "start_date": row.get("start_date"),
                "end_date": row.get("end_date"),
                "is_active": row.get("is_active", True),
            },
        )
    return redirect("admin_products")


@login_required
@user_passes_test(is_admin)
def management_product_export(request):
    """Export active products to JSON."""
    products = Product.objects.filter(is_active=True).values(
        "id",
        "catagory__name",
        "ombor__name",
        "barcode",
        "desc",
        "r_price",
        "s_price",
        "stock",
        "start_date",
        "end_date",
    )
    df = pd.DataFrame(list(products))
    response = HttpResponse(content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="products.json"'
    response.write(df.to_json(orient="records"))
    return response


@login_required
@user_passes_test(is_admin)
@require_POST
def management_category_import(request):
    """Import categories from JSON."""
    file = request.FILES.get("file")
    if not file:
        return HttpResponse("Fayl topilmadi", status=400)
    df = pd.read_json(file)
    for _, row in df.iterrows():
        Catagory.objects.update_or_create(
            name=row["name"], defaults={"desc": row.get("desc", "")}
        )
    return redirect("admin_categories")


@login_required
@user_passes_test(is_admin)
def management_category_export(request):
    """Export categories to JSON."""
    categories = Catagory.objects.all().values("id", "name", "desc")
    df = pd.DataFrame(list(categories))
    response = HttpResponse(content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="categories.json"'
    response.write(df.to_json(orient="records"))
    return response

