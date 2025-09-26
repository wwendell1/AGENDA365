from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class TarefaGrupo(models.Model):
    STATUS_CHOICES = [
        ('a_fazer', 'A Fazer'),
        ('em_andamento', 'Em andamento'),
        ('aguardando_feedback', 'Aguardando feedback'),
        ('concluido', 'Concluído'),
    ]
    
    PRIORIDADE_CHOICES = [
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    # Campos básicos
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    grupo = models.ForeignKey('core.Grupo', on_delete=models.CASCADE, related_name='tarefas')
    responsavel_principal = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tarefas_responsavel'
    )
    colaboradores = models.ManyToManyField(User, related_name='tarefas_colaborando', blank=True)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tarefas_grupo_criadas')
    
    # Campos de controle
    prazo = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='a_fazer')
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default='media')
    
    # Campos Kanban
    coluna_kanban = models.CharField(max_length=20, default='a_fazer')
    ordem_kanban = models.PositiveIntegerField(default=0)
    
    # Timestamps
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    # Histórico de mudanças
    historico_status = models.JSONField(default=list, blank=True)

    def save(self, *args, **kwargs):
        # Verifica se é uma criação nova
        is_new = not self.pk
        old_status = None
        
        if not is_new:
            # Obtém o estado anterior
            try:
                old_instance = TarefaGrupo.objects.get(pk=self.pk)
                old_status = old_instance.status
            except TarefaGrupo.DoesNotExist:
                pass
        
        # Atualiza status se estiver atrasada
        if self.status != 'concluido' and self.prazo and self.prazo < timezone.now():
            # Não muda automaticamente para atrasada, mas pode ser usado para relatórios
            pass
        
        # Lógica mais inteligente para sincronização de coluna
        if self.status == 'concluido':
            self.coluna_kanban = 'concluido'
        elif self.status == 'a_fazer':
            self.coluna_kanban = 'a_fazer'
        elif self.status == 'em_andamento':
            self.coluna_kanban = 'em_andamento'
        elif self.status == 'aguardando_feedback':
            self.coluna_kanban = 'aguardando_feedback'
        
        super().save(*args, **kwargs)
        
        # Se houve mudança de status, registra no histórico
        if not is_new and old_status and old_status != self.status:
            self.registrar_mudanca_status(old_status, self.status)

    def registrar_mudanca_status(self, status_anterior, status_novo, usuario=None):
        """Registra mudança de status no histórico"""
        if not isinstance(self.historico_status, list):
            self.historico_status = []
        
        entrada_historico = {
            'de': status_anterior,
            'para': status_novo,
            'data': timezone.now().isoformat(),
            'usuario': usuario.username if usuario else 'sistema'
        }
        
        self.historico_status.append(entrada_historico)
        # Salva sem triggerar o save() novamente
        TarefaGrupo.objects.filter(pk=self.pk).update(historico_status=self.historico_status)

    def mover_para_coluna(self, nova_coluna, usuario=None):
        """Move tarefa para nova coluna do Kanban"""
        if nova_coluna not in dict(self.STATUS_CHOICES):
            raise ValueError(f"Coluna inválida: {nova_coluna}")
        
        status_anterior = self.status
        self.status = nova_coluna
        self.coluna_kanban = nova_coluna
        
        # Reordena na nova coluna (coloca no final)
        max_ordem = TarefaGrupo.objects.filter(
            grupo=self.grupo,
            coluna_kanban=nova_coluna
        ).aggregate(models.Max('ordem_kanban'))['ordem_kanban__max'] or 0
        
        self.ordem_kanban = max_ordem + 1
        self.save()
        
        # Registra no histórico
        if status_anterior != nova_coluna:
            self.registrar_mudanca_status(status_anterior, nova_coluna, usuario)

    @property
    def esta_atrasada(self):
        """Verifica se a tarefa está atrasada"""
        if not self.prazo or self.status == 'concluido':
            return False
        return self.prazo < timezone.now()

    @property
    def progresso_checklist(self):
        """Calcula o progresso do checklist em porcentagem"""
        total_itens = self.checklist.count()
        if total_itens == 0:
            return 100
        
        itens_concluidos = self.checklist.filter(concluido=True).count()
        return int((itens_concluidos / total_itens) * 100)

    @property
    def cor_prioridade(self):
        """Retorna cor baseada na prioridade"""
        cores = {
            'baixa': '#28a745',    # Verde
            'media': '#ffc107',    # Amarelo
            'alta': '#fd7e14',     # Laranja
            'urgente': '#dc3545'   # Vermelho
        }
        return cores.get(self.prioridade, '#6c757d')

    def get_historico_completo(self):
        """Retorna histórico completo incluindo comentários"""
        from datetime import datetime
        
        historico = []
        
        # Adiciona criação da tarefa
        historico.append({
            'tipo': 'criacao',
            'data': self.criado_em,
            'usuario': self.criado_por.username,
            'descricao': f'Tarefa criada por {self.criado_por.get_full_name() or self.criado_por.username}'
        })
        
        # Adiciona mudanças de status
        for mudanca in self.historico_status:
            try:
                data = datetime.fromisoformat(mudanca['data'].replace('Z', '+00:00'))
                historico.append({
                    'tipo': 'status',
                    'data': data,
                    'usuario': mudanca['usuario'],
                    'descricao': f'Status alterado de "{dict(self.STATUS_CHOICES).get(mudanca["de"], mudanca["de"])}" para "{dict(self.STATUS_CHOICES).get(mudanca["para"], mudanca["para"])}"'
                })
            except (KeyError, ValueError):
                continue
        
        # Adiciona comentários
        for comentario in self.comentarios.all().select_related('autor'):
            historico.append({
                'tipo': 'comentario',
                'data': comentario.criado_em,
                'usuario': comentario.autor.username,
                'descricao': comentario.texto[:100] + ('...' if len(comentario.texto) > 100 else ''),
                'comentario_completo': comentario.texto,
                'mencoes': [user.username for user in comentario.mencoes.all()]
            })
        
        # Ordena por data (mais recente primeiro)
        return sorted(historico, key=lambda x: x['data'], reverse=True)

    class Meta:
        verbose_name = 'Tarefa do Grupo'
        verbose_name_plural = 'Tarefas dos Grupos'
        ordering = ['ordem_kanban', '-criado_em']
        indexes = [
            models.Index(fields=['grupo', 'status']),
            models.Index(fields=['status', 'prazo']),
            models.Index(fields=['grupo', 'coluna_kanban', 'ordem_kanban']),
            models.Index(fields=['responsavel_principal']),
            models.Index(fields=['criado_em']),
        ]

    def __str__(self):
        return f'{self.titulo} ({self.grupo.nome})'

class ChecklistItem(models.Model):
    tarefa = models.ForeignKey(TarefaGrupo, on_delete=models.CASCADE, related_name='checklist')
    texto = models.CharField(max_length=200)
    concluido = models.BooleanField(default=False)
    ordem = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    concluido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def marcar_concluido(self, usuario=None):
        """Marca item como concluído"""
        self.concluido = True
        self.concluido_em = timezone.now()
        self.concluido_por = usuario
        self.save()

    def desmarcar_concluido(self):
        """Desmarca item como concluído"""
        self.concluido = False
        self.concluido_em = None
        self.concluido_por = None
        self.save()

    class Meta:
        verbose_name = 'Item do Checklist'
        verbose_name_plural = 'Itens do Checklist'
        ordering = ['ordem', 'criado_em']

    def __str__(self):
        status = '✓' if self.concluido else '○'
        return f'{status} {self.texto}'

class ComentarioTarefa(models.Model):
    tarefa = models.ForeignKey(TarefaGrupo, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    texto = models.TextField()
    mencoes = models.ManyToManyField(User, related_name='mencionado_em_tarefas', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    editado_em = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Processa menções após salvar
        self.processar_mencoes()

    def processar_mencoes(self):
        """Processa @menções no texto do comentário"""
        import re
        
        # Encontra todas as menções no formato @username
        mencoes_encontradas = re.findall(r'@(\w+)', self.texto)
        
        # Busca usuários válidos que são membros do grupo
        usuarios_validos = User.objects.filter(
            username__in=mencoes_encontradas,
            grupos_participando=self.tarefa.grupo
        )
        
        # Atualiza as menções
        self.mencoes.set(usuarios_validos)
        
        # Cria notificações para usuários mencionados
        for usuario in usuarios_validos:
            # Evita import circular - será criado via service
            pass

    class Meta:
        verbose_name = 'Comentário da Tarefa'
        verbose_name_plural = 'Comentários das Tarefas'
        ordering = ['-criado_em']

    def __str__(self):
        return f'Comentário de {self.autor.username} em {self.tarefa.titulo}'

class AnexoTarefa(models.Model):
    tarefa = models.ForeignKey(TarefaGrupo, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(upload_to='tarefas/anexos/')
    nome_original = models.CharField(max_length=255)
    tipo_arquivo = models.CharField(max_length=100)
    tamanho = models.PositiveIntegerField()  # em bytes
    upload_por = models.ForeignKey(User, on_delete=models.CASCADE)
    upload_em = models.DateTimeField(auto_now_add=True)
    comentario = models.ForeignKey(ComentarioTarefa, on_delete=models.CASCADE, null=True, blank=True)

    @property
    def tamanho_formatado(self):
        """Retorna tamanho formatado em KB/MB"""
        if self.tamanho < 1024:
            return f'{self.tamanho} B'
        elif self.tamanho < 1024 * 1024:
            return f'{self.tamanho / 1024:.1f} KB'
        else:
            return f'{self.tamanho / (1024 * 1024):.1f} MB'

    class Meta:
        verbose_name = 'Anexo da Tarefa'
        verbose_name_plural = 'Anexos das Tarefas'
        ordering = ['-upload_em']

    def __str__(self):
        return f'{self.nome_original} ({self.tarefa.titulo})'
