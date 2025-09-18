from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .grupo import Grupo

class NotificacaoGrupo(models.Model):
    TIPOS_NOTIFICACAO = [
        ('tarefa_atribuida', 'Tarefa Atribuída'),
        ('prazo_proximo', 'Prazo Próximo'),
        ('prazo_vencido', 'Prazo Vencido'),
        ('mencao', 'Menção'),
        ('comentario', 'Novo Comentário'),
        ('status_alterado', 'Status Alterado'),
        ('convite_grupo', 'Convite para Grupo'),
        ('membro_adicionado', 'Membro Adicionado'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes_grupo')
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name='notificacoes')
    tipo = models.CharField(max_length=20, choices=TIPOS_NOTIFICACAO)
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    
    # Referências opcionais
    tarefa = models.ForeignKey('TarefaGrupo', on_delete=models.CASCADE, null=True, blank=True, related_name='notificacoes')
    
    # Controle
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    lida_em = models.DateTimeField(null=True, blank=True)

    def marcar_como_lida(self):
        """Marca notificação como lida"""
        if not self.lida:
            self.lida = True
            self.lida_em = timezone.now()
            self.save()

    @property
    def icone(self):
        """Retorna ícone baseado no tipo de notificação"""
        icones = {
            'tarefa_atribuida': 'fas fa-tasks',
            'prazo_proximo': 'fas fa-clock',
            'prazo_vencido': 'fas fa-exclamation-triangle',
            'mencao': 'fas fa-at',
            'comentario': 'fas fa-comment',
            'status_alterado': 'fas fa-exchange-alt',
            'convite_grupo': 'fas fa-user-plus',
            'membro_adicionado': 'fas fa-users',
        }
        return icones.get(self.tipo, 'fas fa-bell')

    @property
    def cor(self):
        """Retorna cor baseada no tipo de notificação"""
        cores = {
            'tarefa_atribuida': 'info',
            'prazo_proximo': 'warning',
            'prazo_vencido': 'danger',
            'mencao': 'primary',
            'comentario': 'success',
            'status_alterado': 'info',
            'convite_grupo': 'primary',
            'membro_adicionado': 'success',
        }
        return cores.get(self.tipo, 'secondary')

    class Meta:
        verbose_name = 'Notificação do Grupo'
        verbose_name_plural = 'Notificações dos Grupos'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['usuario', 'lida']),
            models.Index(fields=['grupo', 'criado_em']),
            models.Index(fields=['tipo', 'criado_em']),
        ]

    def __str__(self):
        return f'{self.titulo} - {self.usuario.username}'