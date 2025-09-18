from django.contrib import admin

# Importa models básicos
try:
    from .models import Perfil, TransacaoFinanceira, ConfiguracaoNotificacao
    from .models import Grupo, MembroGrupo, ConviteGrupo
    from .models import NotificacaoGrupo, ArquivoGrupo
    BASIC_MODELS_OK = True
except ImportError:
    BASIC_MODELS_OK = False

# Tenta importar models de tarefa
try:
    from .models import TarefaGrupo, ChecklistItem, ComentarioTarefa, AnexoTarefa
    TAREFA_MODELS_OK = True
except ImportError:
    TAREFA_MODELS_OK = False

if BASIC_MODELS_OK:
    @admin.register(Perfil)
    class PerfilAdmin(admin.ModelAdmin):
        list_display = ['usuario', 'tema', 'notificacoes_email']
        search_fields = ['usuario__username']

    # Novos admins para módulo de grupos
    @admin.register(Grupo)
    class GrupoAdmin(admin.ModelAdmin):
        list_display = ['nome', 'criador', 'ativo', 'criado_em']
        search_fields = ['nome', 'descricao']
        list_filter = ['ativo', 'criado_em']
        readonly_fields = ['criado_em', 'atualizado_em']

    @admin.register(MembroGrupo)
    class MembroGrupoAdmin(admin.ModelAdmin):
        list_display = ['usuario', 'grupo', 'papel', 'ativo', 'entrou_em']
        list_filter = ['papel', 'ativo']
        search_fields = ['usuario__username', 'grupo__nome']

    @admin.register(ConviteGrupo)
    class ConviteGrupoAdmin(admin.ModelAdmin):
        list_display = ['grupo', 'papel', 'criado_por', 'usado', 'expira_em']
        list_filter = ['papel', 'usado', 'criado_em']
        readonly_fields = ['token', 'criado_em']

    @admin.register(NotificacaoGrupo)
    class NotificacaoGrupoAdmin(admin.ModelAdmin):
        list_display = ['titulo', 'usuario', 'grupo', 'tipo', 'lida', 'criado_em']
        list_filter = ['tipo', 'lida', 'criado_em']
        search_fields = ['titulo', 'conteudo', 'usuario__username']

    @admin.register(ArquivoGrupo)
    class ArquivoGrupoAdmin(admin.ModelAdmin):
        list_display = ['nome', 'grupo', 'tipo_organizacao', 'versao', 'upload_por', 'upload_em']
        list_filter = ['tipo_organizacao', 'upload_em']
        search_fields = ['nome', 'grupo__nome']

    # Admins existentes
    @admin.register(TransacaoFinanceira)
    class TransacaoFinanceiraAdmin(admin.ModelAdmin):
        list_display = ['tipo', 'valor', 'categoria', 'data']
        list_filter = ['tipo', 'categoria']
        date_hierarchy = 'data'

    @admin.register(ConfiguracaoNotificacao)
    class ConfiguracaoNotificacaoAdmin(admin.ModelAdmin):
        list_display = ['usuario', 'email_tarefas', 'email_grupos', 'email_financas']
        list_filter = ['email_tarefas', 'email_grupos', 'email_financas']

if TAREFA_MODELS_OK:
    @admin.register(TarefaGrupo)
    class TarefaGrupoAdmin(admin.ModelAdmin):
        list_display = ['titulo', 'grupo', 'responsavel_principal', 'status', 'prioridade', 'prazo']
        list_filter = ['status', 'prioridade', 'grupo']
        search_fields = ['titulo', 'descricao']
        readonly_fields = ['criado_em', 'atualizado_em', 'historico_status']

    @admin.register(ChecklistItem)
    class ChecklistItemAdmin(admin.ModelAdmin):
        list_display = ['texto', 'tarefa', 'concluido', 'ordem']
        list_filter = ['concluido']
        search_fields = ['texto', 'tarefa__titulo']

    @admin.register(ComentarioTarefa)
    class ComentarioTarefaAdmin(admin.ModelAdmin):
        list_display = ['tarefa', 'autor', 'criado_em']
        search_fields = ['texto', 'tarefa__titulo']
        readonly_fields = ['criado_em', 'editado_em']

    @admin.register(AnexoTarefa)
    class AnexoTarefaAdmin(admin.ModelAdmin):
        list_display = ['nome_original', 'tarefa', 'upload_por', 'upload_em']
        search_fields = ['nome_original', 'tarefa__titulo']
        readonly_fields = ['upload_em']
