from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .grupo import Grupo
import os

class ArquivoGrupo(models.Model):
    TIPOS_ORGANIZACAO = [
        ('tarefa', 'Por Tarefa'),
        ('mes', 'Por Mês'),
        ('categoria', 'Por Categoria'),
        ('livre', 'Livre'),
    ]
    
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name='arquivos')
    nome = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to='grupos/arquivos/')
    tipo_arquivo = models.CharField(max_length=100)
    tamanho = models.PositiveIntegerField()  # em bytes
    
    # Organização
    pasta = models.CharField(max_length=200, blank=True)
    tipo_organizacao = models.CharField(max_length=20, choices=TIPOS_ORGANIZACAO, default='livre')
    
    # Controle de versão
    versao = models.PositiveIntegerField(default=1)
    arquivo_pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='versoes')
    
    # Metadados
    upload_por = models.ForeignKey(User, on_delete=models.CASCADE)
    upload_em = models.DateTimeField(auto_now_add=True)
    ultima_modificacao = models.DateTimeField(auto_now=True)
    descricao = models.TextField(blank=True)
    
    # Referências opcionais (será adicionada após migração inicial)
    # tarefa_relacionada = models.ForeignKey('core.TarefaGrupo', on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            # Novo arquivo - organiza automaticamente
            self.organizar_automaticamente()
            
        super().save(*args, **kwargs)

    def organizar_automaticamente(self):
        """Organiza arquivo automaticamente baseado no tipo de organização"""
        if self.tipo_organizacao == 'tarefa' and self.tarefa_relacionada:
            self.pasta = f'Tarefa_{self.tarefa_relacionada.id}_{self.tarefa_relacionada.titulo[:30]}'
        elif self.tipo_organizacao == 'mes':
            mes_ano = timezone.now().strftime('%Y_%m')
            self.pasta = f'Arquivos_{mes_ano}'
        elif self.tipo_organizacao == 'categoria':
            categoria = self.detectar_categoria()
            self.pasta = f'Categoria_{categoria}'

    def detectar_categoria(self):
        """Detecta categoria baseada na extensão do arquivo"""
        extensao = os.path.splitext(self.nome)[1].lower()
        
        categorias = {
            'Documentos': ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
            'Planilhas': ['.xls', '.xlsx', '.csv'],
            'Apresentações': ['.ppt', '.pptx'],
            'Imagens': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
            'Videos': ['.mp4', '.avi', '.mov', '.wmv', '.flv'],
            'Audios': ['.mp3', '.wav', '.flac', '.aac'],
            'Compactados': ['.zip', '.rar', '.7z', '.tar', '.gz'],
        }
        
        for categoria, extensoes in categorias.items():
            if extensao in extensoes:
                return categoria
        
        return 'Outros'

    def criar_nova_versao(self, novo_arquivo, usuario):
        """Cria uma nova versão do arquivo"""
        nova_versao = ArquivoGrupo.objects.create(
            grupo=self.grupo,
            nome=self.nome,
            arquivo=novo_arquivo,
            tipo_arquivo=self.tipo_arquivo,
            tamanho=novo_arquivo.size,
            pasta=self.pasta,
            tipo_organizacao=self.tipo_organizacao,
            versao=self.versao + 1,
            arquivo_pai=self.arquivo_pai or self,
            upload_por=usuario,
            tarefa_relacionada=self.tarefa_relacionada
        )
        return nova_versao

    @property
    def tamanho_formatado(self):
        """Retorna tamanho formatado"""
        if self.tamanho < 1024:
            return f'{self.tamanho} B'
        elif self.tamanho < 1024 * 1024:
            return f'{self.tamanho / 1024:.1f} KB'
        else:
            return f'{self.tamanho / (1024 * 1024):.1f} MB'

    @property
    def extensao(self):
        """Retorna extensão do arquivo"""
        return os.path.splitext(self.nome)[1].lower()

    @property
    def icone(self):
        """Retorna ícone baseado no tipo de arquivo"""
        extensao = self.extensao
        
        icones = {
            '.pdf': 'fas fa-file-pdf text-danger',
            '.doc': 'fas fa-file-word text-primary',
            '.docx': 'fas fa-file-word text-primary',
            '.xls': 'fas fa-file-excel text-success',
            '.xlsx': 'fas fa-file-excel text-success',
            '.ppt': 'fas fa-file-powerpoint text-warning',
            '.pptx': 'fas fa-file-powerpoint text-warning',
            '.jpg': 'fas fa-file-image text-info',
            '.jpeg': 'fas fa-file-image text-info',
            '.png': 'fas fa-file-image text-info',
            '.gif': 'fas fa-file-image text-info',
            '.mp4': 'fas fa-file-video text-dark',
            '.avi': 'fas fa-file-video text-dark',
            '.mp3': 'fas fa-file-audio text-purple',
            '.wav': 'fas fa-file-audio text-purple',
            '.zip': 'fas fa-file-archive text-secondary',
            '.rar': 'fas fa-file-archive text-secondary',
        }
        
        return icones.get(extensao, 'fas fa-file text-muted')

    def get_versoes(self):
        """Retorna todas as versões do arquivo"""
        if self.arquivo_pai:
            return ArquivoGrupo.objects.filter(arquivo_pai=self.arquivo_pai).order_by('-versao')
        else:
            return ArquivoGrupo.objects.filter(
                models.Q(arquivo_pai=self) | models.Q(id=self.id)
            ).order_by('-versao')

    class Meta:
        verbose_name = 'Arquivo do Grupo'
        verbose_name_plural = 'Arquivos dos Grupos'
        ordering = ['-upload_em']
        indexes = [
            models.Index(fields=['grupo', 'pasta']),
            models.Index(fields=['upload_em']),
            models.Index(fields=['tipo_organizacao']),
        ]

    def __str__(self):
        return f'{self.nome} (v{self.versao}) - {self.grupo.nome}'