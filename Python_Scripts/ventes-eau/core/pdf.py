"""Génération des PDF — ReportLab (aucune dépendance système)."""
from datetime import timedelta
from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from django.utils.formats import date_format
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from .models import Delivery
from .services import day_report, loading_stats, report_data

AQUA_900 = colors.HexColor("#062544")
AQUA_600 = colors.HexColor("#0d6aa0")
AQUA_100 = colors.HexColor("#d9ecf7")
ROW_ALT = colors.HexColor("#eef5fb")
GRID = colors.HexColor("#b8cfe0")
MUTED = colors.HexColor("#5c7893")

PAGE_W = 269 * mm          # largeur utile en A4 paysage avec marges de 14 mm
PAY = dict(Delivery.Payment.choices)
DELIVERY_W = [24 * mm, 62 * mm, 30 * mm, 30 * mm, 36 * mm, 42 * mm, 45 * mm]
REPAY_W = [30 * mm, 90 * mm, 50 * mm, 40 * mm, 59 * mm]

TITLE = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=16,
                       textColor=AQUA_900, spaceAfter=3)
SUB = ParagraphStyle("S", fontName="Helvetica", fontSize=9, textColor=MUTED)
H2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=12.5,
                    textColor=AQUA_600, spaceBefore=12, spaceAfter=5)
H3 = ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=10.5,
                    textColor=AQUA_900, spaceBefore=9, spaceAfter=4)
NOTE = ParagraphStyle("N", fontName="Helvetica-Oblique", fontSize=8, textColor=MUTED)


def fmt(n):
    return f"{n:,}".replace(",", " ")


def _who(request):
    return request.user.first_name or request.user.username


def _response(story, filename, title):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=13 * mm, bottomMargin=13 * mm, title=title)
    doc.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


def _table(data, widths, total_row=False):
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("BACKGROUND", (0, 0), (-1, 0), AQUA_900),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]
    body_rows = len(data) - 1 - (1 if total_row else 0)
    if body_rows > 0:
        last = len(data) - 2 if total_row else len(data) - 1
        style.append(("ROWBACKGROUNDS", (0, 1), (-1, last), [colors.white, ROW_ALT]))
    if total_row:
        style += [("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                  ("BACKGROUND", (0, -1), (-1, -1), AQUA_100)]
    t.setStyle(TableStyle(style))
    return t


def _stats_table(pairs):
    """Bandeau de statistiques : libellés / valeurs."""
    t = Table([[l for l, _ in pairs], [str(v) for _, v in pairs]],
              colWidths=[PAGE_W / len(pairs)] * len(pairs))
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("FONTSIZE", (0, 1), (-1, 1), 11),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 1), (-1, 1), AQUA_900),
        ("BACKGROUND", (0, 1), (-1, 1), AQUA_100),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _loading_block(story, loading, stats, heading=True):
    if heading:
        state = (f"terminé à {timezone.localtime(loading.closed_at):%H:%M}"
                 if loading.closed_at else "en cours")
        story.append(Paragraph(
            f"Chargement n° {loading.number} — démarré à "
            f"{timezone.localtime(loading.created_at):%H:%M} ({state})", H3))
    story.append(_stats_table([
        ("Chargés", loading.qty_loaded),
        ("Restant préc.", loading.qty_carried),
        ("Livrés", stats["qty"]),
        ("Offerts", stats["gift"]),
        ("Restant", stats["remaining"]),
        ("Encaissé", f'{fmt(stats["paid"])} F'),
        ("dont espèces", f'{fmt(stats["especes"])} F'),
        ("dont Wave", f'{fmt(stats["wave"])} F'),
        ("Crédit", f'{fmt(stats["credit"])} F'),
    ]))
    story.append(Spacer(1, 6))
    data = [["Heure", "Client", "Sachets", "Offerts", "Prix unitaire", "Montant", "Paiement"]]
    for d in loading.deliveries.all():
        data.append([
            timezone.localtime(d.created_at).strftime("%H:%M"),
            d.client.name if d.client else "—",
            str(d.qty), str(d.qty_gift), fmt(d.unit_price),
            fmt(d.amount), PAY[d.payment],
        ])
    if len(data) > 1:
        data.append(["TOTAL", "", str(stats["qty"]), str(stats["gift"]),
                     "", f'{fmt(stats["total"])} F', ""])
        story.append(_table(data, DELIVERY_W, total_row=True))
    else:
        story.append(Paragraph("Aucune livraison.", NOTE))


# ---------- PDF d'un chargement ----------

def loading_report(request, loading):
    stats = loading_stats(loading)
    story = [
        Paragraph(f"Rapport du chargement n° {loading.number}", TITLE),
        Paragraph(f"Journée du {date_format(loading.day, 'l d F Y')} — généré le "
                  f"{timezone.localtime():%d/%m/%Y à %H:%M} par {_who(request)}", SUB),
        Spacer(1, 8),
    ]
    _loading_block(story, loading, stats, heading=False)
    story.append(Spacer(1, 10))
    story.append(Paragraph("Les sachets offerts sont livrés mais ne comptent pas dans les montants.", NOTE))
    return _response(story, f"chargement-n{loading.number}-{loading.day:%Y-%m-%d}.pdf",
                     f"Chargement n° {loading.number}")


# ---------- PDF journalier / période (détaillé) ----------

def period_report(request, start, end):
    single = start == end
    title = (f"Rapport journalier — {start:%d/%m/%Y}" if single
             else f"Rapport des ventes d'eau — du {start:%d/%m/%Y} au {end:%d/%m/%Y}")
    story = [
        Paragraph(title, TITLE),
        Paragraph(f"Généré le {timezone.localtime():%d/%m/%Y à %H:%M} par {_who(request)}", SUB),
        Spacer(1, 8),
    ]

    sections = []
    day = start
    while day <= end:
        rep = day_report(day)
        if rep["loadings"] or rep["repayments"]:
            sections.append(rep)
        day += timedelta(days=1)

    if not sections:
        story.append(Paragraph("Aucune donnée sur cette période.", SUB))
        return _response(story, "rapport-vide.pdf", title)

    grand = {k: 0 for k in ["qty", "gift", "especes", "wave", "credit", "rep_especes", "rep_wave"]}
    for i, rep in enumerate(sections):
        story.append(Paragraph(f"Journée du {date_format(rep['day'], 'l d F Y')}", H2))
        for l in rep["loadings"]:
            _loading_block(story, l["loading"], l["stats"])

        if rep["repayments"]:
            story.append(Paragraph("Remboursements de la journée", H3))
            data = [["Heure", "Client", "Montant", "Mode", "Encaissé par"]]
            for r in rep["repayments"]:
                data.append([timezone.localtime(r.created_at).strftime("%H:%M"),
                             r.client.name, f"{fmt(r.amount)} F", r.get_method_display(),
                             (r.received_by.first_name or r.received_by.username) if r.received_by else "—"])
            data.append(["TOTAL", "",
                         f"{fmt(sum(r.amount for r in rep['repayments']))} F", "", ""])
            story.append(_table(data, REPAY_W, total_row=True))

        t = rep["totals"]
        story.append(Paragraph("Résumé de la journée", H3))
        story.append(_stats_table([
            ("Sachets", t["qty"]),
            ("Offerts", t["gift"]),
            ("Espèces", f'{fmt(t["especes"])} F'),
            ("Wave", f'{fmt(t["wave"])} F'),
            ("Crédit vendu", f'{fmt(t["credit"])} F'),
            ("Remb. espèces", f'{fmt(t["rep_especes"])} F'),
            ("Remb. Wave", f'{fmt(t["rep_wave"])} F'),
            ("Encaissé", f'{fmt(t["cash_in"])} F'),
        ]))
        for k in grand:
            grand[k] += t[k]
        if i < len(sections) - 1:
            story.append(PageBreak())

    if not single:
        grand["cash_in"] = grand["especes"] + grand["wave"] + grand["rep_especes"] + grand["rep_wave"]
        story.append(Paragraph("TOTAL DE LA PÉRIODE", H2))
        story.append(_stats_table([
            ("Sachets", grand["qty"]),
            ("Offerts", grand["gift"]),
            ("Espèces", f'{fmt(grand["especes"])} F'),
            ("Wave", f'{fmt(grand["wave"])} F'),
            ("Crédit vendu", f'{fmt(grand["credit"])} F'),
            ("Remb. espèces", f'{fmt(grand["rep_especes"])} F'),
            ("Remb. Wave", f'{fmt(grand["rep_wave"])} F'),
            ("Encaissé", f'{fmt(grand["cash_in"])} F'),
        ]))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Les sachets offerts sont livrés mais ne comptent pas dans les montants. "
                           "« Encaissé » = espèces + Wave (ventes) + remboursements.", NOTE))
    filename = (f"journalier-{start:%Y-%m-%d}.pdf" if single
                else f"rapport-{start:%Y-%m-%d}_{end:%Y-%m-%d}.pdf")
    return _response(story, filename, title)


# ---------- PDF résumé (une ligne par jour) ----------

def period_summary(request, start, end):
    days, totals = report_data(start, end)
    data = [["Jour", "Sachets", "Offerts", "Espèces", "Wave", "Crédit vendu",
             "Remb. espèces", "Remb. Wave", "Encaissé"]]
    for d in days:
        enc = d["especes"] + d["rep_especes"] + d["wave"] + d["rep_wave"]
        data.append([d["day"].strftime("%d/%m/%Y"), str(d["qty"]), str(d["gift"]),
                     fmt(d["especes"]), fmt(d["wave"]), fmt(d["credit"]),
                     fmt(d["rep_especes"]), fmt(d["rep_wave"]), fmt(enc)])
    data.append(["TOTAL", str(totals["qty"]), str(totals["gift"]), fmt(totals["especes"]),
                 fmt(totals["wave"]), fmt(totals["credit"]), fmt(totals["rep_especes"]),
                 fmt(totals["rep_wave"]), fmt(totals["cash_in"])])
    story = [
        Paragraph("Rapport des ventes d'eau (résumé)", TITLE),
        Paragraph(f"Période : du {start:%d/%m/%Y} au {end:%d/%m/%Y} — généré le "
                  f"{timezone.localtime():%d/%m/%Y à %H:%M} par {_who(request)}", SUB),
        Spacer(1, 10),
        _table(data, [45 * mm] + [28 * mm] * 8, total_row=True),
    ]
    return _response(story, f"rapport-resume-{start:%Y-%m-%d}_{end:%Y-%m-%d}.pdf",
                     "Rapport résumé")