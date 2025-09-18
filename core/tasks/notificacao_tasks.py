from celery import shared_task
from django.utils import timezone
from core.services.notificacao_service import NotificacaoService

@shared_task
def verificar_prazos_tarefas():
    """
    Task periódica para verificar prazos de tarefas
    Deve ser executada a cada hora
    """
    try:
        # Verifica prazos próximos (24h)
        proximas = NotificacaoService.verificar_prazos_proximos()
        
        # Verifica prazos vencidos
        vencidas = NotificacaoService.notificar_prazo_vencido()
        
        # Processa notificações contínuas
        continuas = NotificacaoService.processar_notificacoes_continuas()
        
        return {
            'sucesso': True,
            'proximas': proximas,
            'vencidas': vencidas,
            'continuas': continuas,
            'executado_em': timezone.now().isoformat()
        }
    except Exception as e:
        return {
            'sucesso': False,
            'erro': str(e),
            'executado_em': timezone.now().isoformat()
        }

@shared_task
def limpar_notificacoes_antigas():
    """
    Task para limpeza de notificações antigas
    Deve ser executada diariamente
    """
    try:
        removidas = NotificacaoService.limpar_notificacoes_antigas(dias=30)
        
        return {
            'sucesso': True,
            'notificacoes_removidas': removidas,
            'executado_em': timezone.now().isoformat()
        }
    except Exception as e:
        return {
            'sucesso': False,
            'erro': str(e),
            'executado_em': timezone.now().isoformat()
        }

@shared_task
def processar_mencoes_comentario(comentario_id):
    """
    Task para processar menções em comentários
    """
    try:
        from core.models import ComentarioTarefa
        
        comentario = ComentarioTarefa.objects.get(id=comentario_id)
        comentario.processar_mencoes()
        
        return {
            'sucesso': True,
            'comentario_id': comentario_id,
            'processado_em': timezone.now().isoformat()
        }
    except Exception as e:
        return {
            'sucesso': False,
            'erro': str(e),
            'comentario_id': comentario_id,
            'processado_em': timezone.now().isoformat()
        }