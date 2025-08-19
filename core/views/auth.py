from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from ..forms import (
    RegistroUsuarioForm,
    LoginForm,
    PerfilForm,
    ExcluirContaForm,
    RecuperarSenhaForm,
    DefinirNovaSenhaForm
)

def login_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'Você já está logado.')
        return redirect('dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Por favor, preencha todos os campos.')
            return render(request, 'core/auth/login.html')
            
        try:
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Sua conta está desativada.')
            else:
                messages.error(request, 'Usuário ou senha inválidos. Por favor, tente novamente.')
        except Exception as e:
            messages.error(request, 'Erro ao fazer login. Por favor, tente novamente.')
    
    return render(request, 'core/auth/login.html')

def registro_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'Você já está logado.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    print('Iniciando criação do usuário...')
                    print(f'Dados do formulário: {form.cleaned_data}')
                    
                    # Cria o usuário
                    user = form.save(commit=False)
                    print(f'Usuário preparado com username: {user.username}')
                    
                    # Salva o usuário
                    user.save()
                    print(f'Usuário salvo com ID: {user.id}')
                    
                    # Aguarda um momento para garantir que os sinais sejam processados
                    from time import sleep
                    sleep(1)
                    
                    # Força o refresh do usuário do banco de dados
                    from django.contrib.auth.models import User
                    user = User.objects.get(id=user.id)
                    print(f'Usuário recarregado do banco de dados: {user.username}')
                    
                    # Verifica se o perfil foi criado pelo sinal
                    from ..models import Perfil
                    perfil = Perfil.objects.filter(usuario=user).first()
                    if not perfil:
                        print('Perfil não encontrado após sinal. Criando manualmente...')
                        perfil = Perfil.objects.create(usuario=user)
                        print(f'Perfil criado manualmente com ID: {perfil.id}')
                    else:
                        print(f'Perfil encontrado com ID: {perfil.id}')
                    
                    # Verifica configurações de notificação
                    from ..models import ConfiguracaoNotificacao
                    config = ConfiguracaoNotificacao.objects.filter(usuario=user).first()
                    if not config:
                        print('Configuração de notificação não encontrada. Criando manualmente...')
                        config = ConfiguracaoNotificacao.objects.create(usuario=user)
                        print(f'Configuração criada com ID: {config.id}')
                    else:
                        print(f'Configuração encontrada com ID: {config.id}')
                    
                    print('Processo de criação de conta concluído com sucesso!')
                    messages.success(request, 'Conta criada com sucesso! Por favor, faça login.')
                    return redirect('login')
            except Exception as e:
                import traceback
                print('Erro ao criar conta:')
                print(f'Tipo de erro: {type(e).__name__}')
                print(f'Mensagem de erro: {str(e)}')
                print(f'Traceback completo:\n{traceback.format_exc()}')
                
                # Tratamento de erros específicos
                error_message = 'Erro ao criar conta. Por favor, tente novamente.'
                
                if 'duplicate key' in str(e).lower():
                    if 'username' in str(e).lower():
                        error_message = 'Este nome de usuário já está em uso. Por favor, escolha outro.'
                    elif 'email' in str(e).lower():
                        error_message = 'Este email já está cadastrado. Por favor, use outro email.'
                elif 'invalid' in str(e).lower():
                    if 'username' in str(e).lower():
                        error_message = 'Nome de usuário inválido. Use apenas letras, números e underline.'
                    elif 'email' in str(e).lower():
                        error_message = 'Email inválido. Por favor, verifique o formato do email.'
                    elif 'password' in str(e).lower():
                        error_message = 'Senha inválida. A senha deve ter pelo menos 8 caracteres.'
                
                messages.error(request, error_message)
                return render(request, 'core/auth/registro.html', {'form': form})
        else:
            print('Formulário inválido:')
            print(f'Erros de validação: {form.errors}')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Erro no campo {field}: {error}')
    else:
        form = RegistroUsuarioForm()
    
    return render(request, 'core/auth/registro.html', {'form': form})

@login_required
def perfil_view(request):
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=request.user.perfil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('perfil')
    else:
        form = PerfilForm(instance=request.user.perfil)
    return render(request, 'core/auth/perfil.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def excluir_conta_view(request):
    if request.method == 'POST':
        form = ExcluirContaForm(request.user, request.POST)
        if form.is_valid():
            try:
                user = request.user
                logout(request)
                user.delete()
                messages.success(request, 'Sua conta foi excluída com sucesso.')
                return redirect('login')
            except Exception as e:
                messages.error(request, 'Erro ao excluir conta. Por favor, tente novamente.')
                return redirect('perfil')
    else:
        form = ExcluirContaForm(request.user)
    return render(request, 'core/auth/excluir_conta.html', {'form': form})

def recuperar_senha_view(request):
    if request.method == 'POST':
        form = RecuperarSenhaForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Gera o token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Constrói o link de recuperação
                reset_url = request.build_absolute_uri(
                    f'/recuperar-senha/{uid}/{token}/'
                )
                
                # Envia o email
                subject = 'Recuperação de Senha - Produtiva'
                message = render_to_string('core/auth/email/recuperar_senha.html', {
                    'user': user,
                    'reset_url': reset_url
                })
                
                send_mail(
                    subject,
                    message,
                    'noreply@produtiva.com',
                    [email],
                    fail_silently=False,
                    html_message=message
                )
                
                messages.success(
                    request,
                    'Um email foi enviado com instruções para recuperar sua senha.'
                )
                return redirect('login')
            except User.DoesNotExist:
                messages.error(
                    request,
                    'Não encontramos uma conta com este email.'
                )
    else:
        form = RecuperarSenhaForm()
    
    return render(request, 'core/auth/recuperar_senha.html', {'form': form})

def redefinir_senha_view(request, uidb64, token):
    try:
        # Decodifica o uid e obtém o usuário
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        
        # Verifica se o token é válido
        if default_token_generator.check_token(user, token):
            if request.method == 'POST':
                form = DefinirNovaSenhaForm(user, request.POST)
                if form.is_valid():
                    form.save()
                    messages.success(
                        request,
                        'Sua senha foi alterada com sucesso! Você já pode fazer login.'
                    )
                    return redirect('login')
            else:
                form = DefinirNovaSenhaForm(user)
            
            return render(
                request,
                'core/auth/redefinir_senha.html',
                {'form': form}
            )
        else:
            messages.error(
                request,
                'O link de recuperação de senha é inválido ou já foi usado.'
            )
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(
            request,
            'O link de recuperação de senha é inválido.'
        )
    
    return redirect('login')