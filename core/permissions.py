from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from functools import wraps
from django.contrib.auth.decorators import login_required

from .models import Grupo, MembroGrupo

class BaseGrupoPermissionMixin(UserPassesTestMixin):
    """Mixin base para verificação de permissões em grupos"""
    
    def dispatch(self, request, *args, **kwargs):
        # Verifica se o usuário está logado
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Obtém o grupo (assumindo que o primeiro parâmetro após self é o grupo_id ou pk)
        grupo_id = kwargs.get('pk') or kwargs.get('grupo_id')
        
        if not grupo_id:
            raise PermissionDenied("Grupo não especificado")
        
        grupo = get_object_or_404(Grupo, pk=grupo_id)
        
        # Verifica se o usuário é membro do grupo
        try:
            membro = MembroGrupo.objects.get(user=request.user, grupo=grupo)
        except MembroGrupo.DoesNotExist:
            raise PermissionDenied("Você não é membro deste grupo")
        
        return super().dispatch(request, *args, **kwargs)

class AdminGrupoRequiredMixin(BaseGrupoPermissionMixin):
    """Mixin que requer permissão de administrador"""
    
    def test_func(self):
        grupo_id = self.kwargs.get('pk') or self.kwargs.get('grupo_id')
        grupo = get_object_or_404(Grupo, pk=grupo_id)
        
        try:
            membro = MembroGrupo.objects.get(user=self.request.user, grupo=grupo)
            return membro.role == 'admin'
        except MembroGrupo.DoesNotExist:
            return False

class ModeradorGrupoRequiredMixin(BaseGrupoPermissionMixin):
    """Mixin que requer permissão de administrador ou moderador"""
    
    def test_func(self):
        grupo_id = self.kwargs.get('pk') or self.kwargs.get('grupo_id')
        grupo = get_object_or_404(Grupo, pk=grupo_id)
        
        try:
            membro = MembroGrupo.objects.get(user=self.request.user, grupo=grupo)
            return membro.role in ['admin', 'moderador']
        except MembroGrupo.DoesNotExist:
            return False

def admin_grupo_required(view_func):
    """Decorator para verificar permissão de administrador"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        grupo_id = kwargs.get('grupo_id')
        if not grupo_id:
            raise PermissionDenied("Grupo não especificado")
        
        grupo = get_object_or_404(Grupo, pk=grupo_id)
        
        try:
            membro = MembroGrupo.objects.get(user=request.user, grupo=grupo)
            if membro.role != 'admin':
                raise PermissionDenied("Você não tem permissão de administrador neste grupo")
        except MembroGrupo.DoesNotExist:
            raise PermissionDenied("Você não é membro deste grupo")
        
        return view_func(request, *args, **kwargs)
    return wrapper

def moderador_grupo_required(view_func):
    """Decorator para verificar permissão de administrador ou moderador"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        grupo_id = kwargs.get('grupo_id')
        if not grupo_id:
            raise PermissionDenied("Grupo não especificado")
        
        grupo = get_object_or_404(Grupo, pk=grupo_id)
        
        try:
            membro = MembroGrupo.objects.get(user=request.user, grupo=grupo)
            if membro.role not in ['admin', 'moderador']:
                raise PermissionDenied("Você não tem permissão de moderador neste grupo")
        except MembroGrupo.DoesNotExist:
            raise PermissionDenied("Você não é membro deste grupo")
        
        return view_func(request, *args, **kwargs)
    return wrapper

def membro_grupo_required(view_func):
    """Decorator para verificar se o usuário é membro do grupo"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        grupo_id = kwargs.get('grupo_id')
        if not grupo_id:
            raise PermissionDenied("Grupo não especificado")
        
        grupo = get_object_or_404(Grupo, pk=grupo_id)
        
        try:
            MembroGrupo.objects.get(user=request.user, grupo=grupo)
        except MembroGrupo.DoesNotExist:
            raise PermissionDenied("Você não é membro deste grupo")
        
        return view_func(request, *args, **kwargs)
    return wrapper

def verificar_permissao_tarefa(user, tarefa):
    """
    Verifica se o usuário tem permissão para interagir com a tarefa
    
    Regras:
    - Administradores e moderadores têm acesso total
    - Colaboradores podem ver e atualizar suas próprias tarefas
    """
    try:
        # Verifica se o usuário é membro do grupo da tarefa
        membro = MembroGrupo.objects.get(user=user, grupo=tarefa.grupo)
        
        # Administradores e moderadores têm acesso total
        if membro.role in ['admin', 'moderador']:
            return True
        
        # Colaboradores podem interagir com tarefas em que são responsáveis ou colaboradores
        if (tarefa.responsavel_principal == user or 
            user in tarefa.colaboradores.all()):
            return True
        
        return False
    except MembroGrupo.DoesNotExist:
        return False