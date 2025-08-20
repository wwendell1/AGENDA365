from celery import shared_task
from django.core.management import call_command

@shared_task
def verificar_alertas_diarios():
    """Tarefa agendada para verificar alertas financeiros diariamente."""
    call_command('verificar_alertas')