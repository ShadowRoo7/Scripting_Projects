from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from .forms import DeliveryForm, LoadingForm
from .models import Client, Delivery, Loading, Repayment


def loading_stats(loading):
    s = {"qty": 0, "gift": 0, "especes": 0, "wave": 0, "credit": 0}
    for d in loading.deliveries.all():
        s["qty"] += d.qty
        s["gift"] += d.qty_gift
        s[d.payment] += d.amount
    s["paid"] = s["especes"] + s["wave"]
    s["total"] = s["paid"] + s["credit"]
    s["remaining"] = loading.available - s["qty"] - s["gift"]
    return s


def next_number():
    today = timezone.localdate()
    last = Loading.objects.filter(day=today).order_by("number").last()
    return last.number + 1 if last else 1


def suggested_carried_and_price():
    last = Loading.objects.order_by("-id").first()
    if not last:
        return 0, ""
    return max(0, loading_stats(last)["remaining"]), last.default_price


def today_totals():
    today = timezone.localdate()
    t = {"qty": 0, "gift": 0, "especes": 0, "wave": 0, "credit": 0, "rep_especes": 0, "rep_wave": 0}
    for d in Delivery.objects.filter(loading__day=today):
        t["qty"] += d.qty
        t["gift"] += d.qty_gift
        t[d.payment] += d.amount
    for r in Repayment.objects.filter(created_at__date=today):
        t["rep_" + r.method] += r.amount
    t["cash"] = t["especes"] + t["rep_especes"]
    t["wave_total"] = t["wave"] + t["rep_wave"]
    return t


def history_context():
    since = timezone.localdate() - timedelta(days=settings.HISTORY_DAYS - 1)
    loadings = (Loading.objects.filter(closed_at__isnull=False, day__gte=since)
                .prefetch_related("deliveries").order_by("-id"))
    return {"history_rows": [{"loading": l, "stats": loading_stats(l)} for l in loadings],
            "history_days": settings.HISTORY_DAYS}


def current_context():
    open_loading = Loading.objects.filter(closed_at__isnull=True).first()
    ctx = {"open_loading": open_loading}
    if open_loading:
        ctx["stats"] = loading_stats(open_loading)
        ctx["delivery_form"] = DeliveryForm(initial={"unit_price": open_loading.default_price})
        ctx["clients"] = Client.objects.all()
    else:
        carried, price = suggested_carried_and_price()
        ctx["loading_form"] = LoadingForm(initial={"qty_carried": carried, "default_price": price})
        ctx["next_number"] = next_number()
    return ctx


def parse_period(request):
    """Lit ?from=YYYY-MM-DD&to=YYYY-MM-DD (7 derniers jours par défaut)."""
    today = timezone.localdate()

    def parse(name, default):
        try:
            return datetime.strptime(request.GET.get(name, ""), "%Y-%m-%d").date()
        except ValueError:
            return default

    start = parse("from", today - timedelta(days=6))
    end = min(parse("to", today), today)
    return start, end


def report_data(start, end):
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
    return days, totals


def day_report(day):
    """Rapport détaillé d'une journée : chargements + remboursements + totaux."""
    loadings = [{"loading": l, "stats": loading_stats(l)}
                for l in Loading.objects.filter(day=day)
                .prefetch_related("deliveries").order_by("id")]
    repayments = list(Repayment.objects.filter(created_at__date=day)
                      .select_related("client", "received_by").order_by("id"))
    t = {"qty": 0, "gift": 0, "especes": 0, "wave": 0, "credit": 0, "rep_especes": 0, "rep_wave": 0}
    for l in loadings:
        s = l["stats"]
        t["qty"] += s["qty"]
        t["gift"] += s["gift"]
        t["especes"] += s["especes"]
        t["wave"] += s["wave"]
        t["credit"] += s["credit"]
    for r in repayments:
        t["rep_" + r.method] += r.amount
    t["paid"] = t["especes"] + t["wave"]
    t["cash_in"] = t["paid"] + t["rep_especes"] + t["rep_wave"]
    return {"day": day, "loadings": loadings, "repayments": repayments, "totals": t}