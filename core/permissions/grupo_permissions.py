from rest_framework.permissions import BasePermission
from core.models import Grupo, MembroGrupo

class GrupoPermissions(BasePermission):
    """
    Permissões para operações em grupos
    """
    
    def has_permission(self, request, view):
        """Verifica permissões gerais"""
        # Usuário deve estar autenticado
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Para criação de grupos, qualquer usuário autenticado pode
        if view.action == 'create':
            return True
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Verifica permissões específicas do grupo"""
        if not isinstance(obj, Grupo):
            return False
        
        # Verifica se usuário é membro do grupo
        papel = obj.get_papel_usuario(request.user)
        if not papel:
            return False
        
        # Permissões por ação
        if view.action in ['retrieve', 'list']:
            # Qualquer membro pode visualizar
            return True
        
        elif view.action in ['update', 'partial_update']:
            # Apenas administradores podem editar grupo
            return papel == 'administrador'
        
        elif view.action == 'destroy':
            # Apenas administradores podem excluir grupo
            return papel == 'administrador'
        
        elif view.action in ['convidar_membro', 'gerar_convite']:
            # Administradores e moderadores podem convidar
            return papel in ['administrador', 'moderador']
        
        elif view.action in ['alterar_papel', 'remover_membro']:
            # Apenas administradores podem alterar papéis e remover membros
            return papel == 'administrador'
        
        elif view.action in ['listar_membros', 'estatisticas']:
            # Qualquer membro pode ver membros e estatísticas
            return True
        
        return False

class TarefaPermissions(BasePermission):
    """
    Permissões para operações em tarefas
    """
    
    def has_permission(self, request, view):
        """Verifica permissões gerais"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Para criação, verifica se é membro do grupo
        if view.action == 'create':
            grupo_id = request.data.get('grupo') or view.kwargs.get('grupo_pk')
            if grupo_id:
                try:
                    grupo = Grupo.objects.get(id=grupo_id)
                    return grupo.membros.filter(
                        id=request.user.id, 
                        membrogrupo__ativo=True
                    ).exists()
                except Grupo.DoesNotExist:
                    return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Verifica permissões específicas da tarefa"""
        from core.models import TarefaGrupo
        
        if not isinstance(obj, TarefaGrupo):
            return False
        
        # Verifica se usuário é membro do grupo da tarefa
        papel = obj.grupo.get_papel_usuario(request.user)
        if not papel:
            return False
        
        # Permissões por ação
        if view.action in ['retrieve', 'list']:
            # Qualquer membro pode visualizar tarefas do grupo
            return True
        
        elif view.action in ['update', 'partial_update']:
            # Administradores, moderadores podem editar
            # Responsável e colaboradores podem editar campos específicos
            if papel in ['administrador', 'moderador']:
                return True
            
            # Responsável ou colaborador pode editar alguns campos
            if (request.user == obj.responsavel_principal or 
                request.user in obj.colaboradores.all()):
                # Pode editar apenas campos permitidos (implementar lógica específica)
                return True
            
            return False
        
        elif view.action == 'destroy':
            # Apenas administradores e moderadores podem excluir tarefas
            return papel in ['administrador', 'moderador']
        
        elif view.action in ['mover_kanban', 'adicionar_comentario', 'upload_anexo']:
            # Qualquer membro do grupo pode mover tarefas, comentar e anexar arquivos
            return True
        
        elif view.action in ['atribuir_responsavel', 'adicionar_colaborador']:
            # Apenas administradores e moderadores podem atribuir responsáveis
            return papel in ['administrador', 'moderador']
        
        return False

class MembroGrupoPermissions(BasePermission):
    """
    Permissões para operações em membros de grupo
    """
    
    def has_permission(self, request, view):
        """Verifica permissões gerais"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Verifica permissões específicas do membro"""
        if not isinstance(obj, MembroGrupo):
            return False
        
        # Verifica se usuário é membro do mesmo grupo
        papel_solicitante = obj.grupo.get_papel_usuario(request.user)
        if not papel_solicitante:
            return False
        
        # Permissões por ação
        if view.action in ['retrieve', 'list']:
            # Qualquer membro pode ver outros membros
            return True
        
        elif view.action in ['update', 'partial_update']:
            # Apenas administradores podem alterar membros
            # Ou o próprio usuário pode alterar alguns campos seus
            if papel_solicitante == 'administrador':
                return True
            
            # Usuário pode editar apenas seus próprios dados (campos limitados)
            if request.user == obj.usuario:
                # Implementar lógica para campos que o usuário pode editar
                return True
            
            return False
        
        elif view.action == 'destroy':
            # Administradores podem remover membros
            # Usuários podem se remover (com validações)
            if papel_solicitante == 'administrador':
                return True
            
            if request.user == obj.usuario:
                # Validar se não é o último administrador
                if obj.papel == 'administrador':
                    admins_count = MembroGrupo.objects.filter(
                        grupo=obj.grupo,
                        papel='administrador',
                        ativo=True
                    ).count()
                    return admins_count > 1
                return True
            
            return False
        
        return False

class IsGrupoMember(BasePermission):
    """
    Permissão simples para verificar se usuário é membro do grupo
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Obtém grupo_id da URL ou dos dados
        grupo_id = view.kwargs.get('grupo_pk') or request.data.get('grupo')
        
        if not grupo_id:
            return False
        
        try:
            grupo = Grupo.objects.get(id=grupo_id)
            return grupo.membros.filter(
                id=request.user.id,
                membrogrupo__ativo=True
            ).exists()
        except Grupo.DoesNotExist:
            return False

class CanManageGrupoTasks(BasePermission):
    """
    Permissão para verificar se usuário pode gerenciar tarefas do grupo
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        grupo_id = view.kwargs.get('grupo_pk') or request.data.get('grupo')
        
        if not grupo_id:
            return False
        
        try:
            grupo = Grupo.objects.get(id=grupo_id)
            return grupo.can_manage_tasks(request.user)
        except Grupo.DoesNotExist:
            return False