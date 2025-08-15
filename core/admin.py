from django.contrib import admin
from .models import Perfil, Grupo, Membro, Tarefa, TransacaoFinanceira, Comentario, Notificacao, ConfiguracaoNotificacao

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tema', 'notificacoes_email']
    search_fields = ['usuario__username']

@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'criador', 'criado_em']
    search_fields = ['nome']

@admin.register(Membro)
class MembroAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'grupo', 'papel', 'entrou_em']
    list_filter = ['papel']

@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'responsavel', 'status', 'data_limite']
    list_filter = ['status', 'prioridade']
    search_fields = ['titulo', 'descricao']

@admin.register(TransacaoFinanceira)
class TransacaoFinanceiraAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'valor', 'categoria', 'data']
    list_filter = ['tipo', 'categoria']
    date_hierarchy = 'data'

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ['tarefa', 'autor', 'criado_em']
    search_fields = ['texto']

@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tipo', 'lida', 'criado_em']
    list_filter = ['tipo', 'lida']

@admin.register(ConfiguracaoNotificacao)
class ConfiguracaoNotificacaoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'email_tarefas', 'email_grupos', 'email_financas']
    list_filter = ['email_tarefas', 'email_grupos', 'email_financas']
