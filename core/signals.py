from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from .models import Perfil, Tarefa, Comentario, ConfiguracaoNotificacao

@receiver(post_save, sender=User)
def criar_perfil(sender, instance, created, **kwargs):
    if created:
        try:
            with transaction.atomic():
                print(f'Iniciando criação de perfil e configurações para {instance.username}')
                
                # Verifica se já existe um perfil
                perfil_existente = Perfil.objects.filter(usuario=instance).first()
                if perfil_existente:
                    print(f'Perfil já existe para {instance.username} com ID: {perfil_existente.id}')
                else:
                    print(f'Criando novo perfil para {instance.username}...')
                    perfil = Perfil.objects.create(
                        usuario=instance,
                        tema='light',
                        notificacoes_email=True,
                        preferencias_notificacao={}
                    )
                    print(f'Perfil criado com sucesso. ID: {perfil.id}')
                
                # Verifica se já existe configuração de notificação
                config_existente = ConfiguracaoNotificacao.objects.filter(usuario=instance).first()
                if config_existente:
                    print(f'Configuração já existe para {instance.username} com ID: {config_existente.id}')
                else:
                    print(f'Criando novas configurações de notificação...')
                    config = ConfiguracaoNotificacao.objects.create(
                        usuario=instance,
                        email_tarefas=True,
                        email_grupos=True,
                        email_financas=True,
                        notificacao_browser=True,
                        antecedencia_tarefa=24
                    )
                    print(f'Configurações criadas com sucesso. ID: {config.id}')
                
                print(f'Processo de criação concluído para {instance.username}')
                
        except Exception as e:
            import traceback
            print('Erro durante a criação de perfil e configurações:')
            print(f'Tipo de erro: {type(e).__name__}')
            print(f'Mensagem de erro: {str(e)}')
            print(f'Traceback completo:\n{traceback.format_exc()}')
            
            # Tenta recuperar de forma individual
            try:
                if not Perfil.objects.filter(usuario=instance).exists():
                    print('Tentando criar perfil novamente...')
                    Perfil.objects.create(usuario=instance)
            except Exception as e2:
                print(f'Erro ao criar perfil: {str(e2)}')
            
            try:
                if not ConfiguracaoNotificacao.objects.filter(usuario=instance).exists():
                    print('Tentando criar configurações novamente...')
                    ConfiguracaoNotificacao.objects.create(usuario=instance)
            except Exception as e3:
                print(f'Erro ao criar configurações: {str(e3)}')
            
            raise

@receiver(pre_save, sender=Tarefa)
def atualizar_status_tarefa(sender, instance, **kwargs):
    # Não alterar status de tarefas já concluídas
    if instance.status != 'concluida':
        if instance.data_limite < timezone.now():
            instance.status = 'atrasada'
        elif instance.status == 'atrasada' and instance.data_limite > timezone.now():
            instance.status = 'pendente'

@receiver(post_save, sender=Comentario)
def limpar_mencoes_antigas(sender, instance, **kwargs):
    # Remove menções que não existem mais no texto
    mencoes_atuais = [user for user in instance.mencoes.all() 
                     if f'@{user.username}' not in instance.texto]
    for user in mencoes_atuais:
        instance.mencoes.remove(user)