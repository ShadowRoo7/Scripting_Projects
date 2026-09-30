from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Client, Delivery, Loading, Repayment


@admin.register(Loading)
class LoadingAdmin(SimpleHistoryAdmin):
    list_display = ("day", "number", "qty_loaded", "qty_carried", "closed_at")
    list_filter = ("day",)


@admin.register(Delivery)
class DeliveryAdmin(SimpleHistoryAdmin):
    list_display = ("created_at", "loading", "client", "qty", "unit_price", "payment", "created_by")
    list_filter = ("payment",)
    search_fields = ("client__name",)


@admin.register(Repayment)
class RepaymentAdmin(SimpleHistoryAdmin):
    list_display = ("created_at", "client", "amount", "method", "received_by")


@admin.register(Client)
class ClientAdmin(SimpleHistoryAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)