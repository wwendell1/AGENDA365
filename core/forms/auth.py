from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User

class RecuperarSenhaForm(PasswordResetForm):
    email = forms.EmailField(
        label='Email',
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'input', 'placeholder': 'Digite seu email'})
    )

class DefinirNovaSenhaForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label='Nova senha',
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': 'Digite sua nova senha'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label='Confirme a nova senha',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': 'Confirme sua nova senha'}),
    )

class ExcluirContaForm(forms.Form):
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': 'Digite sua senha para confirmar'}),
        help_text='Digite sua senha atual para confirmar a exclusão da conta'
    )
    confirm_deletion = forms.BooleanField(
        label='Confirmo que desejo excluir minha conta permanentemente',
        required=True
    )