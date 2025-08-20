from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta
from .models import TransacaoFinanceira, ConfiguracaoNotificacao

def enviar_notificacao_tarefa(tarefa):
    send_mail(
        subject='Lembrete: Tarefa próxima do prazo',
        message=f'A tarefa "{tarefa.titulo}" vence em 24 horas.',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[tarefa.responsavel.email],
        fail_silently=False,
    )

def verificar_alertas_financeiros():
    """Verifica e envia alertas financeiros para os usuários."""
    hoje = datetime.now().date()
    amanha = hoje + timedelta(days=1)
    semana = hoje + timedelta(days=7)
    
    # Busca todas as transações financeiras relevantes
    transacoes = TransacaoFinanceira.objects.filter(
        data__range=[hoje, semana]
    ).select_related('usuario')
    
    # Agrupa transações por usuário
    alertas_por_usuario = {}
    for transacao in transacoes:
        if transacao.usuario not in alertas_por_usuario:
            alertas_por_usuario[transacao.usuario] = {
                'despesas_recorrentes': [],
                'receitas_programadas': [],
                'transacoes_vencidas': []
            }
        
        # Verifica o tipo de alerta necessário
        if transacao.data == amanha:
            if transacao.tipo == 'despesa' and transacao.recorrente:
                alertas_por_usuario[transacao.usuario]['despesas_recorrentes'].append(transacao)
            elif transacao.tipo == 'receita':
                alertas_por_usuario[transacao.usuario]['receitas_programadas'].append(transacao)
        elif transacao.data < hoje and not transacao.pago:
            alertas_por_usuario[transacao.usuario]['transacoes_vencidas'].append(transacao)
    
    # Envia alertas para cada usuário
    for usuario, alertas in alertas_por_usuario.items():
        try:
            config = ConfiguracaoNotificacao.objects.get(usuario=usuario)
            
            # Prepara mensagem de email
            mensagem = []
            
            # Adiciona despesas recorrentes
            if config.notificar_despesas_recorrentes and alertas['despesas_recorrentes']:
                mensagem.append('\nDespesas Recorrentes para Amanhã:')
                for despesa in alertas['despesas_recorrentes']:
                    mensagem.append(f'- {despesa.descricao}: R$ {despesa.valor:.2f}')
            
            # Adiciona receitas programadas
            if config.notificar_receitas_programadas and alertas['receitas_programadas']:
                mensagem.append('\nReceitas Programadas para Amanhã:')
                for receita in alertas['receitas_programadas']:
                    mensagem.append(f'- {receita.descricao}: R$ {receita.valor:.2f}')
            
            # Adiciona transações vencidas
            if config.notificar_transacoes_vencidas and alertas['transacoes_vencidas']:
                mensagem.append('\nTransações Vencidas:')
                for transacao in alertas['transacoes_vencidas']:
                    mensagem.append(f'- {transacao.descricao}: R$ {transacao.valor:.2f} (Vencida em {transacao.data})')
            
            # Envia email se houver alertas e o usuário optou por receber emails
            if mensagem and config.receber_emails:
                send_mail(
                    subject='Alertas Financeiros - EclesiaUnity',
                    message='\n'.join(mensagem),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[usuario.email],
                    fail_silently=True
                )
                
        except ConfiguracaoNotificacao.DoesNotExist:
            continue