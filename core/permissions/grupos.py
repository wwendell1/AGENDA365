from rest_framework import permissions
from core.models.grupos import GroupMembership

class IsGroupMember(permissions.BasePermission):
    """
    Permissão que verifica se o usuário é membro do grupo.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # obj pode ser um grupo ou um objeto relacionado a um grupo
        if hasattr(obj, 'group'):
            group = obj.group
        else:
            group = obj

        return GroupMembership.objects.filter(
            user=request.user,
            group=group
        ).exists()

class IsGroupAdmin(permissions.BasePermission):
    """
    Permissão que verifica se o usuário é administrador do grupo.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'group'):
            group = obj.group
        else:
            group = obj

        return GroupMembership.objects.filter(
            user=request.user,
            group=group,
            role='admin'
        ).exists()

class IsGroupModerator(permissions.BasePermission):
    """
    Permissão que verifica se o usuário é moderador ou admin do grupo.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'group'):
            group = obj.group
        else:
            group = obj

        return GroupMembership.objects.filter(
            user=request.user,
            group=group,
            role__in=['admin', 'moderator']
        ).exists()

class CanManageTask(permissions.BasePermission):
    """
    Permissão que verifica se o usuário pode gerenciar uma tarefa.
    - Admins e moderadores podem criar, editar e excluir tarefas
    - Responsáveis e colaboradores podem editar tarefas
    - Membros podem visualizar tarefas
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Verificar se o usuário é membro do grupo
        if not GroupMembership.objects.filter(
            user=request.user,
            group=obj.group
        ).exists():
            return False

        # GET requests (visualização) são permitidos para todos os membros
        if request.method in permissions.SAFE_METHODS:
            return True

        # Para outros métodos, verificar o papel do usuário
        membership = GroupMembership.objects.get(
            user=request.user,
            group=obj.group
        )

        # Admins e moderadores podem fazer tudo
        if membership.role in ['admin', 'moderator']:
            return True

        # Responsáveis e colaboradores podem editar
        if request.method in ['PUT', 'PATCH']:
            return (
                request.user == obj.assigned_to or
                request.user in obj.collaborators.all()
            )

        # DELETE só é permitido para admins e moderadores
        return False

class CanManageFiles(permissions.BasePermission):
    """
    Permissão que verifica se o usuário pode gerenciar arquivos.
    - Todos os membros podem fazer upload
    - Apenas o uploader, admins e moderadores podem excluir
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Verificar se o usuário é membro do grupo
        if not GroupMembership.objects.filter(
            user=request.user,
            group=obj.task.group
        ).exists():
            return False

        # GET requests (visualização) são permitidos para todos os membros
        if request.method in permissions.SAFE_METHODS:
            return True

        # Para DELETE, verificar se é o uploader ou tem permissão especial
        if request.method == 'DELETE':
            membership = GroupMembership.objects.get(
                user=request.user,
                group=obj.task.group
            )
            return (
                request.user == obj.uploaded_by or
                membership.role in ['admin', 'moderator']
            )

        # POST (upload) é permitido para todos os membros
        return True

class CanManageComments(permissions.BasePermission):
    """
    Permissão que verifica se o usuário pode gerenciar comentários.
    - Todos os membros podem comentar
    - Apenas o autor, admins e moderadores podem editar/excluir
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Verificar se o usuário é membro do grupo
        if not GroupMembership.objects.filter(
            user=request.user,
            group=obj.task.group
        ).exists():
            return False

        # GET requests (visualização) são permitidos para todos os membros
        if request.method in permissions.SAFE_METHODS:
            return True

        # Para edição/exclusão, verificar se é o autor ou tem permissão especial
        membership = GroupMembership.objects.get(
            user=request.user,
            group=obj.task.group
        )
        return (
            request.user == obj.author or
            membership.role in ['admin', 'moderator']
        )