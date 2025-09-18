from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.urls import reverse

User = get_user_model()

class Group(models.Model):
    """Modelo principal para grupos de trabalho."""
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('moderator', 'Moderador'),
        ('collaborator', 'Colaborador'),
    ]

    name = models.CharField('Nome', max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField('Descrição', blank=True)
    avatar = models.ImageField('Avatar', upload_to='grupos/avatars/', blank=True)
    color = models.CharField('Cor', max_length=7, default='#3273dc')  # Formato: #RRGGBB
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        related_name='created_groups',
        verbose_name='Criado por'
    )
    members = models.ManyToManyField(
        User,
        through='GroupMembership',
        related_name='groups',
        verbose_name='Membros'
    )
    is_active = models.BooleanField('Ativo', default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('group_detail', kwargs={'slug': self.slug})

    class Meta:
        verbose_name = 'Grupo'
        verbose_name_plural = 'Grupos'
        ordering = ['name']

    def __str__(self):
        return self.name

class GroupMembership(models.Model):
    """Modelo para controlar associação e papéis dos membros no grupo."""
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('moderator', 'Moderador'),
        ('collaborator', 'Colaborador'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    role = models.CharField(
        'Papel',
        max_length=20,
        choices=ROLE_CHOICES,
        default='collaborator'
    )
    joined_at = models.DateTimeField('Entrou em', auto_now_add=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='invitations_sent',
        verbose_name='Convidado por'
    )

    class Meta:
        unique_together = ['user', 'group']
        verbose_name = 'Membro do Grupo'
        verbose_name_plural = 'Membros dos Grupos'

    def __str__(self):
        return f'{self.user.username} em {self.group.name} ({self.role})'

class GroupInvitation(models.Model):
    """Modelo para convites pendentes para grupos."""
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    email = models.EmailField('E-mail')
    token = models.CharField(max_length=100, unique=True)
    role = models.CharField(
        'Papel',
        max_length=20,
        choices=GroupMembership.ROLE_CHOICES,
        default='collaborator'
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='group_invitations_sent'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_accepted = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Convite para Grupo'
        verbose_name_plural = 'Convites para Grupos'

class Task(models.Model):
    """Modelo para tarefas dentro dos grupos."""
    STATUS_CHOICES = [
        ('todo', 'A Fazer'),
        ('in_progress', 'Em Andamento'),
        ('waiting', 'Aguardando Feedback'),
        ('done', 'Concluído'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    title = models.CharField('Título', max_length=200)
    description = models.TextField('Descrição', blank=True)
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='todo'
    )
    priority = models.CharField(
        'Prioridade',
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_tasks'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_tasks',
        verbose_name='Responsável'
    )
    collaborators = models.ManyToManyField(
        User,
        related_name='collaborative_tasks',
        blank=True,
        verbose_name='Colaboradores'
    )
    due_date = models.DateTimeField('Prazo', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'done' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'done':
            self.completed_at = None
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Tarefa'
        verbose_name_plural = 'Tarefas'
        ordering = ['-created_at']

class SubTask(models.Model):
    """Modelo para subtarefas (checklist items)."""
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='subtasks'
    )
    description = models.CharField('Descrição', max_length=200)
    is_completed = models.BooleanField('Concluída', default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='completed_subtasks'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Subtarefa'
        verbose_name_plural = 'Subtarefas'

class Comment(models.Model):
    """Modelo para comentários em tarefas."""
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_comments'
    )
    content = models.TextField('Conteúdo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    mentioned_users = models.ManyToManyField(
        User,
        related_name='mentions',
        blank=True
    )

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'

class TaskFile(models.Model):
    """Modelo para arquivos anexados às tarefas."""
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='files'
    )
    file = models.FileField(upload_to='grupos/tasks/files/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_task_files'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.PositiveIntegerField()  # em bytes

    class Meta:
        verbose_name = 'Arquivo de Tarefa'
        verbose_name_plural = 'Arquivos de Tarefas'

class TaskStatusHistory(models.Model):
    """Modelo para histórico de mudanças de status das tarefas."""
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(
        max_length=20,
        choices=Task.STATUS_CHOICES
    )
    new_status = models.CharField(
        max_length=20,
        choices=Task.STATUS_CHOICES
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_status_changes'
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Histórico de Status'
        verbose_name_plural = 'Históricos de Status'

class Notification(models.Model):
    """Modelo para notificações relacionadas a grupos e tarefas."""
    NOTIFICATION_TYPES = [
        ('task_assigned', 'Tarefa Atribuída'),
        ('task_due_soon', 'Tarefa Próxima do Prazo'),
        ('task_overdue', 'Tarefa Atrasada'),
        ('mentioned', 'Mencionado em Comentário'),
        ('status_changed', 'Status Alterado'),
        ('comment_added', 'Novo Comentário'),
        ('daily_digest', 'Resumo Diário'),
        ('task_completed', 'Tarefa Concluída'),
        ('group_update', 'Atualização do Grupo'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='group_notifications'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        null=True
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'

    def __str__(self):
        return f'{self.get_notification_type_display()} para {self.user.username}'

    def mark_as_read(self):
        """Marca a notificação como lida."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()