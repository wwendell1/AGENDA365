from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.contrib.auth.models import User
from ..forms import RecuperarSenhaForm, DefinirNovaSenhaForm, ExcluirContaForm

def recuperar_senha(request):
    if request.method == 'POST':
        form = RecuperarSenhaForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = form.get_users(email).first()
            if user:
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_url = request.build_absolute_uri(
                    reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                )
                
                # Enviar email
                context = {
                    'user': user,
                    'reset_url': reset_url,
                }
                email_html = render_to_string('core/auth/email/recuperar_senha.html', context)
                email_text = render_to_string('core/auth/email/recuperar_senha.txt', context)
                
                send_mail(
                    'Recuperação de Senha - Produtiva',
                    email_text,
                    'noreply@produtiva.com',
                    [email],
                    html_message=email_html,
                    fail_silently=False,
                )
                
                messages.success(request, 'Email de recuperação enviado com sucesso!')
                return redirect('login')
            else:
                messages.error(request, 'Email não encontrado.')
    else:
        form = RecuperarSenhaForm()
    
    return render(request, 'core/auth/recuperar_senha.html', {'form': form})

def redefinir_senha(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = DefinirNovaSenhaForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Sua senha foi alterada com sucesso!')
                return redirect('login')
        else:
            form = DefinirNovaSenhaForm(user)
        return render(request, 'core/auth/redefinir_senha.html', {'form': form})
    else:
        messages.error(request, 'O link de recuperação de senha é inválido ou expirou.')
        return redirect('login')

@login_required
def excluir_conta(request):
    if request.method == 'POST':
        form = ExcluirContaForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            user = authenticate(username=request.user.username, password=password)
            
            if user is not None and form.cleaned_data['confirm_deletion']:
                # Excluir conta e todos os dados relacionados
                user.delete()
                messages.success(request, 'Sua conta foi excluída com sucesso.')
                return redirect('login')
            else:
                messages.error(request, 'Senha incorreta ou confirmação não marcada.')
    else:
        form = ExcluirContaForm()
    
    return render(request, 'core/auth/excluir_conta.html', {'form': form})