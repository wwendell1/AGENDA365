from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    criador = models.ForeignKey(User, on_delete=models.CASCADE)
    membros = models.ManyToManyField(User, through='Membro', related_name='grupos')
    criado_em = models.DateTimeField(auto_now_add=True)

class Membro(models.Model):
    ROLES = [
        ('admin', 'Administrador'),
        ('member', 'Membro'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    papel = models.CharField(max_length=20, choices=ROLES, default='member')
    entrou_em = models.DateTimeField(auto_now_add=True)

class Tarefa(models.Model):
    """
    Modelo para representar uma tarefa no sistema.
    
    Atributos:
        titulo (str): Título da tarefa
        descricao (str): Descrição detalhada da tarefa
        criado_por (User): Usuário que criou a tarefa
        responsavel (User): Usuário responsável pela tarefa
        grupo (Grupo): Grupo ao qual a tarefa pertence
        data_limite (datetime): Data limite para conclusão
        status (str): Status atual da tarefa
        prioridade (str): Nível de prioridade da tarefa
    """
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('concluida', 'Concluída'),
        ('atrasada', 'Atrasada'),
    )
    PRIORIDADE_CHOICES = (
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
    )
    
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tarefas_criadas')
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tarefas_atribuidas')
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, null=True, blank=True)
    data_limite = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default='media')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    historico_status = models.JSONField(default=list, blank=True)

    def save(self, *args, **kwargs):
        # Verifica se é uma criação nova
        if not self.pk:
            super().save(*args, **kwargs)
            return

        # Obtém o estado anterior
        old_status = Tarefa.objects.get(pk=self.pk).status
        
        # Atualiza status se estiver atrasada
        if self.status != 'concluida' and self.data_limite < timezone.now():
            self.status = 'atrasada'
        
        # Se houve mudança de status, registra no histórico
        if old_status != self.status:
            self.historico_status.append({
                'de': old_status,
                'para': self.status,
                'data': timezone.now().isoformat(),
                'usuario': self.responsavel.username if self.responsavel else 'sistema'
            })
        
        super().save(*args, **kwargs)
    
    @property
    def esta_atrasada(self):
        return self.data_limite < timezone.now()
    
    def notificar_responsavel(self):
        if self.responsavel:
            Notificacao.objects.create(
                usuario=self.responsavel,
                tipo='tarefa_proxima',
                conteudo=f'A tarefa "{self.titulo}" vence em 24 horas'
            )

    def get_historico_completo(self):
        """Retorna o histórico completo da tarefa, incluindo mudanças de status e comentários."""
        historico = []
        
        # Adiciona a criação da tarefa
        historico.append({
            'tipo': 'criacao',
            'data': self.criado_em,
            'usuario': self.criado_por.username,
            'descricao': f'Tarefa criada por {self.criado_por.username}'
        })
        
        # Adiciona mudanças de status do histórico
        for mudanca in self.historico_status:
            historico.append({
                'tipo': 'status',
                'data': datetime.fromisoformat(mudanca['data']),
                'usuario': mudanca['usuario'],
                'descricao': f'Status alterado de {mudanca["de"]} para {mudanca["para"]}'
            })
        
        # Adiciona comentários
        for comentario in self.comentarios.all():
            historico.append({
                'tipo': 'comentario',
                'data': comentario.criado_em,
                'usuario': comentario.autor.username,
                'descricao': comentario.texto,
                'mencoes': [user.username for user in comentario.mencoes.all()]
            })
        
        # Ordena o histórico por data
        return sorted(historico, key=lambda x: x['data'], reverse=True)

class TransacaoFinanceira(models.Model):
    """
    Modelo para representar transações financeiras.
    
    Atributos:
        usuario (User): Usuário que criou a transação
        tipo (str): Tipo da transação (receita/despesa)
        valor (decimal): Valor da transação
        categoria (str): Categoria da transação
        data (date): Data da transação
    """
    TIPOS_TRANSACAO = (
        ('receita', 'Receita'),
        ('despesa', 'Despesa'),
    )
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPOS_TRANSACAO)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=50)
    descricao = models.TextField(blank=True)
    data = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)
    parcelas = models.IntegerField(default=1, help_text="Número de parcelas (1 para pagamento único)")
    anexo = models.FileField(upload_to='transacoes/', null=True, blank=True, help_text="Anexo opcional para a transação")

    def valor_por_parcela(self):
        """Calcula o valor de cada parcela."""
        if self.parcelas > 1:
            return self.valor / self.parcelas
        return self.valor

    def __str__(self):
        return f"{self.tipo.capitalize()} - {self.categoria}: R$ {self.valor_formatado}"
    @property
    def valor_formatado(self):
        return f'R$ {self.valor:,.2f}'
    
    @classmethod
    def get_saldo_total(cls, usuario):
        receitas = cls.objects.filter(
            usuario=usuario, 
            tipo='receita'
        ).aggregate(total=models.Sum('valor'))['total'] or 0
        
        despesas = cls.objects.filter(
            usuario=usuario, 
            tipo='despesa'
        ).aggregate(total=models.Sum('valor'))['total'] or 0
        
        return receitas - despesas

class Comentario(models.Model):
    tarefa = models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    texto = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    mencoes = models.ManyToManyField(User, related_name='mencionado_em')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Processa menções após salvar
        mencoes = [u for u in User.objects.all() if f'@{u.username}' in self.texto]
        self.mencoes.set(mencoes)
        
        # Cria notificações para usuários mencionados
        for usuario in mencoes:
            Notificacao.objects.create(
                usuario=usuario,
                tipo='mencao',
                conteudo=f'{self.autor.username} mencionou você em um comentário'
            )

class Notificacao(models.Model):
    TIPOS_NOTIFICACAO = (
        ('tarefa_proxima', 'Tarefa Próxima'),
        ('mencao', 'Menção'),
        ('atualizacao_tarefa', 'Atualização de Tarefa'),
        ('convite_grupo', 'Convite para Grupo'),
    )
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPOS_NOTIFICACAO)
    conteudo = models.TextField()
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

class Anexo(models.Model):
    tarefa = models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(upload_to='anexos/')
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=100)
    tamanho = models.IntegerField()  # em bytes
    upload_por = models.ForeignKey(User, on_delete=models.CASCADE)
    upload_em = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'

class ConfiguracaoNotificacao(models.Model):
    """
    Modelo para armazenar as configurações de notificação do usuário.
    """
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    email_tarefas = models.BooleanField(default=True)
    email_grupos = models.BooleanField(default=True)
    email_financas = models.BooleanField(default=True)
    notificacao_browser = models.BooleanField(default=True)
    antecedencia_tarefa = models.IntegerField(default=24)  # horas
    
    class Meta:
        verbose_name = 'Configuração de Notificação'
        verbose_name_plural = 'Configurações de Notificações'
    
    def __str__(self):
        return f'Configurações de {self.usuario.username}'
