from datetime import datetime

import requests
from django.core.management.base import BaseCommand, CommandError
from core.models import Client, Delivery, Loading


def ts(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Command(BaseCommand):
    help = "Importe les chargements et livraisons depuis Supabase (ancienne app)."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, help="https://xxxx.supabase.co")
        parser.add_argument("--key", required=True, help="Clé anon ou service_role")
        parser.add_argument("--force", action="store_true",
                            help="Importer même si la base n'est pas vide")

    def handle(self, *args, **options):
        if Loading.objects.exists() and not options["force"]:
            raise CommandError("Des chargements existent déjà. Ajoutez --force pour importer quand même.")
        headers = {"apikey": options["key"], "Authorization": f"Bearer {options['key']}"}

        def fetch(table):
            r = requests.get(f"{options['url']}/rest/v1/{table}?select=*&order=id",
                             headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()

        loadings, deliveries = fetch("loadings"), fetch("deliveries")
        mapping = {}
        for row in loadings:
            loading = Loading.objects.create(
                day=row["day"], number=row["number"],
                qty_loaded=row["qty_loaded"], qty_carried=row.get("qty_carried") or 0,
                default_price=row["default_price"],
                created_at=ts(row.get("created_at")), closed_at=ts(row.get("closed_at")))
            mapping[row["id"]] = loading

        for row in deliveries:
            client = None
            if row.get("client"):
                name = row["client"].strip()
                client, _ = Client.objects.get_or_create(name__iexact=name, defaults={"name": name})
            Delivery.objects.create(
                loading=mapping[row["loading_id"]], client=client,
                qty=row["qty"], unit_price=row["unit_price"], payment=row["payment"],
                created_at=ts(row.get("created_at")))

        self.stdout.write(self.style.SUCCESS(
            f"{len(loadings)} chargement(s) et {len(deliveries)} livraison(s) importés."))