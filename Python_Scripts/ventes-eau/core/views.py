import csv
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import DeliveryForm, LoadingForm, RepaymentForm, TeamUserForm
from .models import Client, Delivery, Loading, Repayment
from .services import (current_context, history_context, loading_stats,
                       next_number, today_totals)

User = get_user_model()


def _is_boss(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name="Chef").exists())

boss_required = user_passes_test(_is_boss)


# ---------- Page principale (temps réel via HTMX) ----------

@login_required
def home(request):
    context = current_context()
    context["t"] = today_totals()
    context.update(history_context())
    return render(request, "core/home.html", context)


@login_required
def partial_today(request):
    return render(request, "core/partials/today.html", {"t": today_totals()})


@login_required
def partial_current(request):
    return render(request, "core/partials/current_zone.html", current_context())


@login_required
def partial_history(request):
    return render(request, "core/partials/history.html", history_context())


# ---------- Chargements ----------

@login_required
def loading_create(request):
    if request.method != "POST":
        return redirect("core:home")
    if Loading.objects.filter(closed_at__isnull=True).exists():
        messages.error(request, "Un chargement est déjà en cours.")
        return redirect("core:home")
    form = LoadingForm(request.POST)
    if form.is_valid():
        loading = form.save(commit=False)
        loading.day = timezone.localdate()
        loading.number = next_number()
        loading.created_by = request.user
        try:
            loading.save()
        except IntegrityError:                 # deux démarrages simultanés → on renumérote
            loading.number = next_number()
            loading.save()
        messages.success(request, f"Chargement n° {loading.number} démarré.")
    else:
        messages.error(request, "Sachets chargés et prix unitaire sont obligatoires.")
    return redirect("core:home")


@login_required
def loading_close(request, pk):
    loading = get_object_or_404(Loading, pk=pk, closed_at__isnull=True)
    if request.method == "POST":
        loading.closed_at = timezone.now()
        loading.save()
        messages.success(request, f"Chargement n° {loading.number} terminé.")
    return redirect("core:home")


@login_required
def loading_detail(request, pk):
    loading = get_object_or_404(Loading, pk=pk)
    return render(request, "core/loading_detail.html",
                  {"loading": loading, "stats": loading_stats(loading)})


@login_required
def loading_delete(request, pk):
    loading = get_object_or_404(Loading, pk=pk)
    if request.method == "POST":
        loading.deliveries.all().delete()      # supprimées une à une → tout est tracé
        loading.delete()
        messages.success(request, "Chargement supprimé (action tracée dans l'historique).")
    return redirect("core:home")


# ---------- Livraisons ----------

@login_required
def delivery_add(request):
    open_loading = Loading.objects.filter(closed_at__isnull=True).first()
    if request.method != "POST" or not open_loading:
        return redirect("core:home")
    form = DeliveryForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        qty = data.get("qty") or 0
        qty_gift = data.get("qty_gift") or 0
        remaining = loading_stats(open_loading)["remaining"]
        if qty + qty_gift > remaining:
            messages.error(request, f"Il ne reste que {remaining} sachet(s).")
            return redirect("core:home")
        client = None
        name = (data.get("client") or "").strip()
        if name:
            client, _ = Client.objects.get_or_create(name__iexact=name, defaults={"name": name})
        Delivery.objects.create(loading=open_loading, client=client, qty=qty, qty_gift=qty_gift,
                                unit_price=data["unit_price"], payment=data["payment"],
                                lat=data["lat"], lng=data["lng"], created_by=request.user)
        parts = []
        if qty:
            parts.append(f"{qty} vendu(s)")
        if qty_gift:
            parts.append(f"{qty_gift} offert(s)")
        messages.success(request, " · ".join(parts) + ".")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect("core:home")


@login_required
def delivery_delete(request, pk):
    delivery = get_object_or_404(Delivery, pk=pk)
    if request.method == "POST":
        delivery.delete()
        messages.success(request, "Livraison supprimée (tracée dans l'historique).")
    return redirect(request.META.get("HTTP_REFERER", "/"))


# ---------- Crédits ----------

@login_required
def credits(request):
    rows = []
    for client in Client.objects.all():
        credit = sum(d.amount for d in client.deliveries.filter(payment=Delivery.Payment.CREDIT))
        repaid = sum(r.amount for r in client.repayments.all())
        if credit or repaid:
            rows.append({"client": client, "credit": credit, "repaid": repaid,
                         "balance": credit - repaid})
    rows.sort(key=lambda r: r["balance"], reverse=True)
    repayments = Repayment.objects.select_related("client", "received_by")[:30]
    return render(request, "core/credits.html",
                  {"rows": rows, "repayments": repayments, "form": RepaymentForm()})


@login_required
def repayment_add(request):
    if request.method == "POST":
        form = RepaymentForm(request.POST)
        if form.is_valid():
            repayment = form.save(commit=False)
            repayment.received_by = request.user
            repayment.save()
            messages.success(request, f"Remboursement de {repayment.amount} F enregistré pour {repayment.client}.")
        else:
            messages.error(request, "Formulaire invalide.")
    return redirect("core:credits")


# ---------- Rapport & export ----------

@login_required
def report(request):
    today = timezone.localdate()

    def parse(name, default):
        try:
            return datetime.strptime(request.GET.get(name, ""), "%Y-%m-%d").date()
        except ValueError:
            return default

    start = parse("from", today - timedelta(days=6))
    end = min(parse("to", today), today)

    keys = ["qty", "gift", "especes", "wave", "credit", "rep_especes", "rep_wave"]
    days, totals = [], {k: 0 for k in keys}
    day = start
    while day <= end:
        row = {"day": day, **{k: 0 for k in keys}}
        for d in Delivery.objects.filter(loading__day=day):
            row["qty"] += d.qty
            row["gift"] += d.qty_gift
            row[d.payment] += d.amount
        for r in Repayment.objects.filter(created_at__date=day):
            row["rep_" + r.method] += r.amount
        if any(v for k, v in row.items() if k != "day"):
            days.append(row)
            for k in keys:
                totals[k] += row[k]
        day += timedelta(days=1)

    totals["paid"] = totals["especes"] + totals["wave"]
    totals["cash_in"] = totals["paid"] + totals["rep_especes"] + totals["rep_wave"]
    return render(request, "core/report.html",
                  {"start": start, "end": end, "days": days, "totals": totals})


@login_required
def export_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="ventes-eau-{timezone.localdate()}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["date", "heure", "chargement", "client", "sachets", "offerts",
                     "prix_unitaire", "montant", "paiement"])
    recap = [["RECAPITULATIF"],
             ["date", "chargement", "sachets_livres", "offerts", "especes", "wave", "credit", "total_paye"]]
    totals = {"qty": 0, "gift": 0, "especes": 0, "wave": 0, "credit": 0, "paid": 0}
    labels = dict(Delivery.Payment.choices)
    for loading in Loading.objects.prefetch_related("deliveries").order_by("id"):
        stats = loading_stats(loading)
        for d in loading.deliveries.all():
            moment = timezone.localtime(d.created_at)
            writer.writerow([moment.strftime("%d/%m/%Y"), moment.strftime("%H:%M"), loading.number,
                             d.client.name if d.client else "", d.qty, d.qty_gift, d.unit_price,
                             d.amount, labels[d.payment]])
        recap.append([loading.day.strftime("%d/%m/%Y"), loading.number, stats["qty"], stats["gift"],
                      stats["especes"], stats["wave"], stats["credit"], stats["paid"]])
        for k in totals:
            totals[k] += stats[k]
    recap.append(["TOTAL", "", totals["qty"], totals["gift"], totals["especes"], totals["wave"],
                  totals["credit"], totals["paid"]])
    writer.writerow([])
    for row in recap:
        writer.writerow(row)
    return response


# ---------- Équipe (Chef uniquement) ----------

@boss_required
def team(request):
    form = TeamUserForm()
    if request.method == "POST":
        form = TeamUserForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                user = User.objects.create_user(username=data["username"],
                                                password=data["password"],
                                                first_name=data["full_name"])
            except IntegrityError:
                form.add_error("username", "Cet identifiant existe déjà.")
            else:
                if data["is_boss"]:
                    chef, _ = Group.objects.get_or_create(name="Chef")
                    user.groups.add(chef)
                messages.success(request, f"Compte « {user.username} » créé.")
                return redirect("core:team")
    users = [{"u": u, "chef": u.groups.filter(name="Chef").exists()}
             for u in User.objects.order_by("first_name", "username")]
    return render(request, "core/team.html", {"form": form, "users": users})


@boss_required
def user_toggle(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST" and user != request.user:
        user.is_active = not user.is_active
        user.save()
        messages.success(request, f"{user.first_name or user.username} "
                                  f"{'réactivé' if user.is_active else 'désactivé'}.")
    return redirect("core:team")