from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import NotificacaoGrupo
from ..forms import ConfiguracaoNotificacaoForm

@login_required
def lista_notificacoes(request):
    notificacoes = Notificacao.objects.filter(
        usuario=request.user,
        lida=False
    ).order_by('-criado_em')
    
    return render(request, 'core/notificacoes/lista.html', {
        'notificacoes': notificacoes
    })

@login_required
def marcar_como_lida(request, pk):
    notificacao = get_object_or_404(Notificacao, pk=pk, usuario=request.user)
    notificacao.lida = True
    notificacao.save()
    messages.success(request, 'Notificação marcada como lida.')
    return redirect('lista_notificacoes')

@login_required
def configurar_notificacoes(request):
    if request.method == 'POST':
        form = ConfiguracaoNotificacaoForm(
            request.POST, 
            instance=request.user.configuracao_notificacao
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Preferências de notificação atualizadas!')
            return redirect('configurar_notificacoes')
    else:
        form = ConfiguracaoNotificacaoForm(
            instance=request.user.configuracao_notificacao
        )
    return render(request, 'core/notificacoes/configurar.html', {'form': form})

def enviar_notificacao(usuario, tipo, conteudo):
    """Função utilitária para criar e enviar notificações"""
    notificacao = Notificacao.objects.create(
        usuario=usuario,
        tipo=tipo,
        conteudo=conteudo
    )
    
    # Se usuário optou por receber emails
    if usuario.configuracao_notificacao.receber_emails:
        from django.core.mail import send_mail
        send_mail(
            subject=f'Nova notificação: {tipo}',
            message=conteudo,
            from_email='noreply@produtiva.com',
            recipient_list=[usuario.email],
            fail_silently=True
        )
    
    return notificacao