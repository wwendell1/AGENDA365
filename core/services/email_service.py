import os
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

class EmailService:
    @staticmethod
    def enviar_convite_grupo(convite):
        """
        Envia email de convite para um grupo
        
        :param convite: Instância do modelo ConviteGrupo
        :return: Booleano indicando sucesso do envio
        """
        try:
            # URL de aceitação do convite
            url_convite = f"{settings.SITE_URL}/convite/{convite.token}/"
            
            # Contexto para o template de email
            context = {
                'grupo_nome': convite.grupo.nome,
                'remetente_nome': convite.grupo.criado_por.get_full_name() or convite.grupo.criado_por.username,
                'url_convite': url_convite,
                'papel': convite.get_role_display(),
            }
            
            # Renderiza o template HTML
            html_content = render_to_string('core/emails/convite_grupo.html', context)
            
            # Texto plano para clientes de email que não suportam HTML
            text_content = strip_tags(html_content)
            
            # Cria o email
            email = EmailMultiAlternatives(
                subject=f'Convite para o grupo {convite.grupo.nome}',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[convite.email]
            )
            
            # Anexa o conteúdo HTML
            email.attach_alternative(html_content, "text/html")
            
            # Envia o email
            email.send()
            
            return True
        except Exception as e:
            # Log do erro (você pode substituir por um logger adequado)
            print(f"Erro ao enviar email de convite: {e}")
            return False

    @staticmethod
    def enviar_notificacao_membro_adicionado(grupo, novo_membro, adicionado_por):
        """
        Envia notificação quando um novo membro é adicionado ao grupo
        
        :param grupo: Instância do Grupo
        :param novo_membro: Usuário recém-adicionado
        :param adicionado_por: Usuário que adicionou o novo membro
        :return: Booleano indicando sucesso do envio
        """
        try:
            # URL do grupo
            url_grupo = f"{settings.SITE_URL}/grupos/{grupo.pk}/"
            
            # Contexto para o template de email
            context = {
                'grupo_nome': grupo.nome,
                'novo_membro_nome': novo_membro.get_full_name() or novo_membro.username,
                'adicionado_por_nome': adicionado_por.get_full_name() or adicionado_por.username,
                'url_grupo': url_grupo,
            }
            
            # Renderiza o template HTML
            html_content = render_to_string('core/emails/membro_adicionado.html', context)
            
            # Texto plano para clientes de email que não suportam HTML
            text_content = strip_tags(html_content)
            
            # Cria o email
            email = EmailMultiAlternatives(
                subject=f'Você foi adicionado ao grupo {grupo.nome}',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[novo_membro.email]
            )
            
            # Anexa o conteúdo HTML
            email.attach_alternative(html_content, "text/html")
            
            # Envia o email
            email.send()
            
            return True
        except Exception as e:
            # Log do erro (você pode substituir por um logger adequado)
            print(f"Erro ao enviar email de notificação de membro: {e}")
            return False