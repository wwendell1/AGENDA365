from django.core.mail import send_mail
from django.conf import settings

def enviar_notificacao_tarefa(tarefa):
    send_mail(
        subject='Lembrete: Tarefa próxima do prazo',
        message=f'A tarefa "{tarefa.titulo}" vence em 24 horas.',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[tarefa.responsavel.email],
        fail_silently=False,
    )