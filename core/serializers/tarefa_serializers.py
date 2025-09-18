from rest_framework import serializers
from django.contrib.auth.models import User
from core.models import TarefaGrupo, ChecklistItem, ComentarioTarefa, AnexoTarefa

class ChecklistItemSerializer(serializers.ModelSerializer):
    concluido_por_nome = serializers.CharField(source='concluido_por.get_full_name', read_only=True)
    
    class Meta:
        model = ChecklistItem
        fields = ['id', 'texto', 'concluido', 'ordem', 'criado_em', 
                 'concluido_em', 'concluido_por', 'concluido_por_nome']
        read_only_fields = ['id', 'criado_em', 'concluido_em', 'concluido_por']

class AnexoTarefaSerializer(serializers.ModelSerializer):
    upload_por_nome = serializers.CharField(source='upload_por.get_full_name', read_only=True)
    tamanho_formatado = serializers.CharField(read_only=True)
    
    class Meta:
        model = AnexoTarefa
        fields = ['id', 'arquivo', 'nome_original', 'tipo_arquivo', 'tamanho', 
                 'tamanho_formatado', 'upload_por', 'upload_por_nome', 'upload_em']
        read_only_fields = ['id', 'nome_original', 'tipo_arquivo', 'tamanho', 'upload_por', 'upload_em']

class ComentarioTarefaSerializer(serializers.ModelSerializer):
    autor_nome = serializers.CharField(source='autor.get_full_name', read_only=True)
    autor_username = serializers.CharField(source='autor.username', read_only=True)
    mencoes_usernames = serializers.StringRelatedField(source='mencoes', many=True, read_only=True)
    
    class Meta:
        model = ComentarioTarefa
        fields = ['id', 'texto', 'autor', 'autor_nome', 'autor_username', 
                 'mencoes', 'mencoes_usernames', 'criado_em', 'editado_em']
        read_only_fields = ['id', 'autor', 'mencoes', 'criado_em', 'editado_em']

class TarefaGrupoSerializer(serializers.ModelSerializer):
    responsavel_nome = serializers.CharField(source='responsavel_principal.get_full_name', read_only=True)
    responsavel_username = serializers.CharField(source='responsavel_principal.username', read_only=True)
    criado_por_nome = serializers.CharField(source='criado_por.get_full_name', read_only=True)
    colaboradores_nomes = serializers.StringRelatedField(source='colaboradores', many=True, read_only=True)
    grupo_nome = serializers.CharField(source='grupo.nome', read_only=True)
    
    # Campos calculados
    esta_atrasada = serializers.BooleanField(read_only=True)
    progresso_checklist = serializers.IntegerField(read_only=True)
    cor_prioridade = serializers.CharField(read_only=True)
    
    # Status e prioridade com display
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    prioridade_display = serializers.CharField(source='get_prioridade_display', read_only=True)
    
    # Relacionamentos aninhados (opcional)
    checklist = ChecklistItemSerializer(many=True, read_only=True)
    comentarios = ComentarioTarefaSerializer(many=True, read_only=True)
    anexos = AnexoTarefaSerializer(many=True, read_only=True)
    
    class Meta:
        model = TarefaGrupo
        fields = ['id', 'titulo', 'descricao', 'grupo', 'grupo_nome', 
                 'responsavel_principal', 'responsavel_nome', 'responsavel_username',
                 'colaboradores', 'colaboradores_nomes', 'criado_por', 'criado_por_nome',
                 'prazo', 'status', 'status_display', 'prioridade', 'prioridade_display',
                 'coluna_kanban', 'ordem_kanban', 'criado_em', 'atualizado_em',
                 'esta_atrasada', 'progresso_checklist', 'cor_prioridade',
                 'checklist', 'comentarios', 'anexos', 'historico_status']
        read_only_fields = ['id', 'criado_por', 'criado_em', 'atualizado_em', 'historico_status']
    
    def validate_responsavel_principal(self, value):
        """Valida se responsável é membro do grupo"""
        if value:
            grupo = self.initial_data.get('grupo') or (self.instance.grupo if self.instance else None)
            if grupo and not grupo.membros.filter(id=value.id, membrogrupo__ativo=True).exists():
                raise serializers.ValidationError("Responsável deve ser membro do grupo")
        return value
    
    def validate_colaboradores(self, value):
        """Valida se colaboradores são membros do grupo"""
        if value:
            grupo = self.initial_data.get('grupo') or (self.instance.grupo if self.instance else None)
            if grupo:
                for colaborador in value:
                    if not grupo.membros.filter(id=colaborador.id, membrogrupo__ativo=True).exists():
                        raise serializers.ValidationError(f"Colaborador {colaborador.username} deve ser membro do grupo")
        return value

class TarefaCreateSerializer(serializers.ModelSerializer):
    """Serializer específico para criação de tarefas"""
    checklist_items = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = TarefaGrupo
        fields = ['titulo', 'descricao', 'responsavel_principal', 'colaboradores', 
                 'prazo', 'prioridade', 'checklist_items']
    
    def create(self, validated_data):
        """Cria tarefa usando o service"""
        from core.services import TarefaService
        
        checklist_items = validated_data.pop('checklist_items', [])
        validated_data['checklist'] = checklist_items
        
        request = self.context.get('request')
        grupo = self.context.get('grupo')
        
        return TarefaService.criar_tarefa(validated_data, grupo, request.user)

class TarefaKanbanSerializer(serializers.ModelSerializer):
    """Serializer otimizado para visualização Kanban"""
    responsavel_nome = serializers.CharField(source='responsavel_principal.get_full_name', read_only=True)
    colaboradores_count = serializers.SerializerMethodField()
    comentarios_count = serializers.SerializerMethodField()
    anexos_count = serializers.SerializerMethodField()
    progresso_checklist = serializers.IntegerField(read_only=True)
    cor_prioridade = serializers.CharField(read_only=True)
    esta_atrasada = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = TarefaGrupo
        fields = ['id', 'titulo', 'descricao', 'responsavel_principal', 'responsavel_nome',
                 'colaboradores_count', 'prazo', 'status', 'prioridade', 'coluna_kanban',
                 'ordem_kanban', 'progresso_checklist', 'cor_prioridade', 'esta_atrasada',
                 'comentarios_count', 'anexos_count']
    
    def get_colaboradores_count(self, obj):
        """Retorna número de colaboradores"""
        return obj.colaboradores.count()
    
    def get_comentarios_count(self, obj):
        """Retorna número de comentários"""
        return obj.comentarios.count()
    
    def get_anexos_count(self, obj):
        """Retorna número de anexos"""
        return obj.anexos.count()

class MoverTarefaSerializer(serializers.Serializer):
    """Serializer para mover tarefa no Kanban"""
    nova_coluna = serializers.ChoiceField(choices=TarefaGrupo.STATUS_CHOICES)
    nova_ordem = serializers.IntegerField(required=False, min_value=0)

class AdicionarComentarioSerializer(serializers.Serializer):
    """Serializer para adicionar comentário"""
    texto = serializers.CharField(max_length=2000)
    
    def create(self, validated_data):
        """Cria comentário usando o service"""
        from core.services import TarefaService
        
        request = self.context.get('request')
        tarefa = self.context.get('tarefa')
        
        return TarefaService.adicionar_comentario(
            tarefa=tarefa,
            autor=request.user,
            texto=validated_data['texto']
        )

class AtualizarChecklistSerializer(serializers.Serializer):
    """Serializer para atualizar item do checklist"""
    concluido = serializers.BooleanField()

class ReordenarTarefasSerializer(serializers.Serializer):
    """Serializer para reordenar tarefas em uma coluna"""
    coluna = serializers.ChoiceField(choices=TarefaGrupo.STATUS_CHOICES)
    ordem_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )