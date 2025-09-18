from rest_framework import serializers
from django.contrib.auth.models import User
from core.models import Grupo, MembroGrupo, ConviteGrupo

class MembroGrupoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source='usuario.get_full_name', read_only=True)
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    usuario_email = serializers.CharField(source='usuario.email', read_only=True)
    papel_display = serializers.CharField(source='get_papel_display', read_only=True)
    
    class Meta:
        model = MembroGrupo
        fields = ['id', 'usuario', 'usuario_nome', 'usuario_username', 'usuario_email', 
                 'papel', 'papel_display', 'entrou_em', 'ativo']
        read_only_fields = ['id', 'entrou_em']

class GrupoSerializer(serializers.ModelSerializer):
    membros_count = serializers.SerializerMethodField()
    tarefas_abertas = serializers.SerializerMethodField()
    tarefas_concluidas = serializers.SerializerMethodField()
    papel_usuario = serializers.SerializerMethodField()
    criador_nome = serializers.CharField(source='criador.get_full_name', read_only=True)
    avatar_url = serializers.CharField(source='get_avatar_url', read_only=True)
    
    class Meta:
        model = Grupo
        fields = ['id', 'nome', 'descricao', 'avatar', 'avatar_url', 'cor_personalizada', 
                 'criador', 'criador_nome', 'membros_count', 'tarefas_abertas', 
                 'tarefas_concluidas', 'papel_usuario', 'ativo', 'criado_em', 'atualizado_em']
        read_only_fields = ['id', 'criador', 'criado_em', 'atualizado_em']
    
    def get_membros_count(self, obj):
        """Retorna número de membros ativos"""
        return obj.membros.filter(membrogrupo__ativo=True).count()
    
    def get_tarefas_abertas(self, obj):
        """Retorna número de tarefas abertas"""
        return obj.tarefas.exclude(status='concluido').count()
    
    def get_tarefas_concluidas(self, obj):
        """Retorna número de tarefas concluídas"""
        return obj.tarefas.filter(status='concluido').count()
    
    def get_papel_usuario(self, obj):
        """Retorna papel do usuário logado no grupo"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_papel_usuario(request.user)
        return None
    
    def validate_nome(self, value):
        """Valida nome único"""
        if self.instance:
            # Editando - verifica se nome mudou e se já existe
            if self.instance.nome != value and Grupo.objects.filter(nome=value).exists():
                raise serializers.ValidationError("Já existe um grupo com este nome.")
        else:
            # Criando - verifica se já existe
            if Grupo.objects.filter(nome=value).exists():
                raise serializers.ValidationError("Já existe um grupo com este nome.")
        return value

class GrupoCreateSerializer(serializers.ModelSerializer):
    """Serializer específico para criação de grupos"""
    
    class Meta:
        model = Grupo
        fields = ['nome', 'descricao', 'avatar', 'cor_personalizada']
    
    def validate_nome(self, value):
        """Valida nome único"""
        if Grupo.objects.filter(nome=value).exists():
            raise serializers.ValidationError("Já existe um grupo com este nome.")
        return value
    
    def create(self, validated_data):
        """Cria grupo usando o service"""
        from core.services import GrupoService
        
        request = self.context.get('request')
        return GrupoService.criar_grupo(validated_data, request.user)

class ConviteGrupoSerializer(serializers.ModelSerializer):
    grupo_nome = serializers.CharField(source='grupo.nome', read_only=True)
    criado_por_nome = serializers.CharField(source='criado_por.get_full_name', read_only=True)
    papel_display = serializers.CharField(source='get_papel_display', read_only=True)
    link_convite = serializers.SerializerMethodField()
    
    class Meta:
        model = ConviteGrupo
        fields = ['id', 'grupo', 'grupo_nome', 'papel', 'papel_display', 'token', 
                 'criado_por', 'criado_por_nome', 'criado_em', 'expira_em', 
                 'usado', 'usado_por', 'usado_em', 'link_convite']
        read_only_fields = ['id', 'token', 'criado_por', 'criado_em', 'usado', 'usado_por', 'usado_em']
    
    def get_link_convite(self, obj):
        """Gera URL completa do convite"""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/grupos/convite/{obj.token}/')
        return f'/grupos/convite/{obj.token}/'

class ConvidarMembroSerializer(serializers.Serializer):
    """Serializer para convidar membros"""
    email = serializers.EmailField(required=False)
    usuario_id = serializers.IntegerField(required=False)
    papel = serializers.ChoiceField(choices=MembroGrupo.PAPEIS, default='colaborador')
    
    def validate(self, data):
        """Valida que pelo menos email ou usuario_id foi fornecido"""
        if not data.get('email') and not data.get('usuario_id'):
            raise serializers.ValidationError("Forneça email ou usuario_id")
        
        if data.get('email') and data.get('usuario_id'):
            raise serializers.ValidationError("Forneça apenas email OU usuario_id, não ambos")
        
        # Valida se usuário existe quando usuario_id é fornecido
        if data.get('usuario_id'):
            try:
                User.objects.get(id=data['usuario_id'])
            except User.DoesNotExist:
                raise serializers.ValidationError("Usuário não encontrado")
        
        return data

class AlterarPapelSerializer(serializers.Serializer):
    """Serializer para alterar papel de membro"""
    usuario_id = serializers.IntegerField()
    novo_papel = serializers.ChoiceField(choices=MembroGrupo.PAPEIS)
    
    def validate_usuario_id(self, value):
        """Valida se usuário existe"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Usuário não encontrado")
        return value

class EstatisticasGrupoSerializer(serializers.Serializer):
    """Serializer para estatísticas do grupo"""
    tarefas = serializers.DictField()
    membros = serializers.DictField()
    grupo = serializers.DictField()