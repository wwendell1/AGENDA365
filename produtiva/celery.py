import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'produtiva.settings')

app = Celery('produtiva')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configuração das tarefas agendadas
app.conf.beat_schedule = {
    'verificar-alertas-diarios': {
        'task': 'core.tasks.verificar_alertas_diarios',
        'schedule': crontab(hour=8, minute=0),  # Executa todos os dias às 8h
    },
}