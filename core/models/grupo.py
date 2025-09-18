from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator
import uuid

class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatares/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    tema = models.CharField(max_length=20, default='light')
    notificacoes_email = models.BooleanField(default=True)
    preferencias_notificacao = models.JSONField(default=dict)

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return '/static/img/default-avatar.png'
    
    def toggle_tema(self):
        self.tema = 'dark' if self.tema == 'light' else 'light'
        self.save()
    
    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'

class Grupo(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField()
    avatar = models.ImageField(upload_to='grupos/avatares/', null=True, blank=True)
    cor_personalizada = models.CharField(
        max_length=7, 
        default='#3498db',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Cor deve estar no formato hexadecimal #RRGGBB')]
    )
    criador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grupos_criados')
    membros = models.ManyToManyField(User, through='MembroGrupo', related_name='grupos_participando')
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return '/static/img/default-group-avatar.png'

    def get_papel_usuario(self, usuario):
        """Retorna o papel do usuário no grupo"""
        try:
            membro = self.membrogrupo_set.get(usuario=usuario, ativo=True)
            return membro.papel
        except MembroGrupo.DoesNotExist:
            return None

    def is_admin(self, usuario):
        """Verifica se usuário é administrador do grupo"""
        return self.get_papel_usuario(usuario) == 'administrador'

    def is_moderador(self, usuario):
        """Verifica se usuário é moderador do grupo"""
        return self.get_papel_usuario(usuario) == 'moderador'

    def can_manage_tasks(self, usuario):
        """Verifica se usuário pode gerenciar tarefas"""
        papel = self.get_papel_usuario(usuario)
        return papel in ['administrador', 'moderador']

    class Meta:
        verbose_name = 'Grupo'
        verbose_name_plural = 'Grupos'
        indexes = [
            models.Index(fields=['ativo']),
            models.Index(fields=['criado_em']),
        ]

    def __str__(self):
        return self.nome

class MembroGrupo(models.Model):
    PAPEIS = [
        ('administrador', 'Administrador'),
        ('moderador', 'Moderador'),
        ('colaborador', 'Colaborador'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    papel = models.CharField(max_length=20, choices=PAPEIS, default='colaborador')
    entrou_em = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Membro do Grupo'
        verbose_name_plural = 'Membros dos Grupos'
        unique_together = ['usuario', 'grupo']
        indexes = [
            models.Index(fields=['grupo', 'ativo']),
            models.Index(fields=['usuario', 'ativo']),
        ]

    def __str__(self):
        return f'{self.usuario.username} - {self.grupo.nome} ({self.get_papel_display()})'

class ConviteGrupo(models.Model):
    """Model para gerenciar convites de grupo via link único"""
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name='convites')
    papel = models.CharField(max_length=20, choices=MembroGrupo.PAPEIS, default='colaborador')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField()
    usado = models.BooleanField(default=False)
    usado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='convites_usados')
    usado_em = models.DateTimeField(null=True, blank=True)

    @property
    def is_valido(self):
        """Verifica se o convite ainda é válido"""
        return not self.usado and timezone.now() < self.expira_em

    def usar_convite(self, usuario):
        """Marca o convite como usado"""
        if not self.is_valido:
            raise ValueError("Convite inválido ou expirado")
        
        self.usado = True
        self.usado_por = usuario
        self.usado_em = timezone.now()
        self.save()

    class Meta:
        verbose_name = 'Convite de Grupo'
        verbose_name_plural = 'Convites de Grupos'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expira_em', 'usado']),
        ]

    def __str__(self):
        return f'Convite para {self.grupo.nome} - {self.get_papel_display()}'