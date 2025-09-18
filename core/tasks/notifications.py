from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from ..models.grupos import Task, Notification

@shared_task
def check_task_deadlines():
    """
    Verifica tarefas próximas do prazo e envia notificações.
    Executado a cada hora.
    """
    now = timezone.now()
    
    # Tarefas que vencem em 24 horas
    tasks_due_soon = Task.objects.filter(
        due_date__range=(now, now + timedelta(hours=24)),
        status__in=['todo', 'in_progress', 'waiting']
    ).exclude(
        notifications__notification_type='task_due_soon',
        notifications__created_at__gte=now - timedelta(hours=24)
    )
    
    for task in tasks_due_soon:
        Notification.objects.create(
            user=task.assigned_to,
            task=task,
            notification_type='task_due_soon',
            message=f'A tarefa "{task.title}" vence em 24 horas.'
        )

@shared_task
def check_overdue_tasks():
    """
    Verifica tarefas atrasadas e envia notificações.
    Executado diariamente.
    """
    now = timezone.now()
    
    # Tarefas atrasadas
    overdue_tasks = Task.objects.filter(
        due_date__lt=now,
        status__in=['todo', 'in_progress', 'waiting']
    ).exclude(
        notifications__notification_type='task_overdue',
        notifications__created_at__gte=now - timedelta(days=1)
    )
    
    for task in overdue_tasks:
        days_overdue = (now - task.due_date).days
        Notification.objects.create(
            user=task.assigned_to,
            task=task,
            notification_type='task_overdue',
            message=f'A tarefa "{task.title}" está atrasada há {days_overdue} dias.'
        )

@shared_task
def send_daily_digest():
    """
    Envia resumo diário das tarefas pendentes.
    Executado uma vez por dia.
    """
    now = timezone.now()
    
    # Para cada usuário com tarefas pendentes
    for task in Task.objects.filter(
        status__in=['todo', 'in_progress', 'waiting']
    ).select_related('assigned_to').distinct('assigned_to'):
        
        user = task.assigned_to
        if not user:
            continue
            
        # Conta tarefas por status
        user_tasks = Task.objects.filter(
            assigned_to=user,
            status__in=['todo', 'in_progress', 'waiting']
        )
        
        todo_count = user_tasks.filter(status='todo').count()
        in_progress_count = user_tasks.filter(status='in_progress').count()
        waiting_count = user_tasks.filter(status='waiting').count()
        overdue_count = user_tasks.filter(due_date__lt=now).count()
        
        # Cria notificação com resumo
        message = (
            f'Resumo diário:\n'
            f'- {todo_count} tarefas a fazer\n'
            f'- {in_progress_count} tarefas em andamento\n'
            f'- {waiting_count} tarefas aguardando feedback\n'
            f'- {overdue_count} tarefas atrasadas'
        )
        
        Notification.objects.create(
            user=user,
            notification_type='daily_digest',
            message=message
        )