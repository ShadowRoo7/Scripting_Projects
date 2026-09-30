from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("partiel/jour/", views.partial_today, name="partial_today"),
    path("partiel/actuel/", views.partial_current, name="partial_current"),
    path("partiel/historique/", views.partial_history, name="partial_history"),
    path("chargement/nouveau/", views.loading_create, name="loading_create"),
    path("chargement/<int:pk>/", views.loading_detail, name="loading_detail"),
    path("chargement/<int:pk>/terminer/", views.loading_close, name="loading_close"),
    path("chargement/<int:pk>/supprimer/", views.loading_delete, name="loading_delete"),
    path("livraison/ajouter/", views.delivery_add, name="delivery_add"),
    path("livraison/<int:pk>/supprimer/", views.delivery_delete, name="delivery_delete"),
    path("credits/", views.credits, name="credits"),
    path("remboursement/ajouter/", views.repayment_add, name="repayment_add"),
    path("rapport/", views.report, name="report"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path("equipe/", views.team, name="team"),
    path("equipe/<int:pk>/basculer/", views.user_toggle, name="user_toggle"),
]