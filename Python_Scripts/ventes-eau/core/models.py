from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords


class Loading(models.Model):
    day = models.DateField("Jour", default=timezone.localdate)
    number = models.PositiveIntegerField("N° du jour")
    qty_loaded = models.PositiveIntegerField("Sachets chargés")
    qty_carried = models.PositiveIntegerField("Restant précédent", default=0)
    default_price = models.PositiveIntegerField("Prix unitaire par défaut")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="loadings")
    created_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-id"]
        constraints = [models.UniqueConstraint(fields=["day", "number"], name="unique_day_number")]

    def __str__(self):
        return f"Chargement n° {self.number} — {self.day:%d/%m/%Y}"

    @property
    def available(self):
        return self.qty_loaded + self.qty_carried


class Client(models.Model):
    """Créé automatiquement quand un nom est saisi. Aucune gestion manuelle."""
    name = models.CharField("Nom", max_length=120, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Delivery(models.Model):
    class Payment(models.TextChoices):
        ESPECES = "especes", "Espèces"
        WAVE = "wave", "Wave"
        CREDIT = "credit", "Crédit"

    loading = models.ForeignKey(Loading, on_delete=models.CASCADE, related_name="deliveries")
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="deliveries")
    qty = models.PositiveIntegerField("Sachets")
    qty_gift = models.PositiveIntegerField("Sachets offerts", default=0)
    unit_price = models.PositiveIntegerField("Prix unitaire")
    payment = models.CharField("Paiement", max_length=10, choices=Payment.choices,
                               default=Payment.ESPECES)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="deliveries")
    created_at = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    class Meta:
        ordering = ["id"]

    @property
    def amount(self):
        return self.qty * self.unit_price


class Repayment(models.Model):
    class Method(models.TextChoices):
        ESPECES = "especes", "Espèces"
        WAVE = "wave", "Wave"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="repayments")
    amount = models.PositiveIntegerField("Montant")
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.ESPECES)
    note = models.CharField("Note", max_length=200, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="repayments")
    created_at = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-id"]