from django import forms

from .models import Delivery, Loading, Repayment


class LoadingForm(forms.ModelForm):
    class Meta:
        model = Loading
        fields = ["qty_loaded", "qty_carried", "default_price"]
        widgets = {f: forms.NumberInput(attrs={"class": "form-control", "min": "0"}) for f in fields}


class DeliveryForm(forms.Form):
    client = forms.CharField(label="Client", required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "list": "client-list",
                                      "autocomplete": "off", "placeholder": "facultatif"}))
    qty = forms.IntegerField(label="Sachets", min_value=0, required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "0", "inputmode": "numeric"}))
    qty_gift = forms.IntegerField(label="Offerts", min_value=0, required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "0", "inputmode": "numeric", "placeholder": "0"}))
    unit_price = forms.IntegerField(label="Prix unitaire", min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "0"}))
    payment = forms.ChoiceField(label="Paiement", choices=Delivery.Payment.choices,
        widget=forms.Select(attrs={"class": "form-select"}))
    lat = forms.DecimalField(required=False, widget=forms.HiddenInput)
    lng = forms.DecimalField(required=False, widget=forms.HiddenInput)

    def clean(self):
        cleaned = super().clean()
        qty = cleaned.get("qty") or 0
        gift = cleaned.get("qty_gift") or 0
        if qty + gift < 1:
            raise forms.ValidationError("Indiquez au moins 1 sachet (vendu ou offert).")
        if cleaned.get("payment") == Delivery.Payment.CREDIT and qty > 0 and not (cleaned.get("client") or "").strip():
            raise forms.ValidationError("Un nom de client est obligatoire pour une vente à crédit.")
        return cleaned


class RepaymentForm(forms.ModelForm):
    class Meta:
        model = Repayment
        fields = ["client", "amount", "method", "note"]
        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "method": forms.Select(attrs={"class": "form-select"}),
            "note": forms.TextInput(attrs={"class": "form-control", "placeholder": "facultatif"}),
        }


class TeamUserForm(forms.Form):
    username = forms.CharField(label="Identifiant", max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}))
    full_name = forms.CharField(label="Nom complet", max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(label="Mot de passe", min_length=6,
        widget=forms.PasswordInput(attrs={"class": "form-control"}))
    is_boss = forms.BooleanField(label="Chef", required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))