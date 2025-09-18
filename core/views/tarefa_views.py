from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q

from core.models import TarefaGrupo, Grupo, ChecklistItem
from core.serializers import (
    TarefaGrupoSerializer, TarefaCreateSerializer, TarefaKanbanSerializer,
    MoverTarefaSerializer, AdicionarComentarioSerializer, 
    AtualizarChecklistSerializer, ReordenarTarefasSerializer
)
from core.permissions import TarefaPermissions, IsGrupoMember
from core.services import TarefaService

class TarefaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações CRUD em tarefas
    """
    serializer_class = TarefaGrupoSerializer
    permission_classes = [IsAuthenticated, TarefaPermissions]
    
    def get_queryset(self):
        """Retorna tarefas dos grupos do usuário"""
        # Filtra por grupo se fornecido na URL
        grupo_id = self.kwargs.get('grupo_pk')
        
        queryset = TarefaGrupo.objects.filter(
            grupo__membros=self.request.user,
            grupo__membrogrupo__ativo=True
        ).select_related(
            'responsavel_principal', 'criado_por', 'grupo'
        ).prefetch_related(
            'colaboradores', 'checklist', 'comentarios', 'anexos'
        )
        
        if grupo_id:
            queryset = queryset.filter(grupo_id=grupo_id)
        
        return queryset
    
    def get_serializer_class(self):
        """Retorna serializer apropriado para a ação"""
        if self.action == 'create':
            return TarefaCreateSerializer
        elif self.action == 'kanban':
            return TarefaKanbanSerializer
        return TarefaGrupoSerializer
    
    def get_serializer_context(self):
        """Adiciona contexto extra para serializers"""
        context = super().get_serializer_context()
        
        # Adiciona grupo ao contexto se disponível
        grupo_id = self.kwargs.get('grupo_pk')
        if grupo_id:
            try:
                context['grupo'] = Grupo.objects.get(id=grupo_id)
            except Grupo.DoesNotExist:
                pass
        
        return context
    
    def perform_create(self, serializer):
        """Cria tarefa usando o service"""
        # O TarefaCreateSerializer já usa o service
        pass
    
    @action(detail=True, methods=['post'])
    def mover_kanban(self, request, pk=None):
        """
        Move tarefa para nova coluna do Kanban
        """
        tarefa = self.get_object()
        serializer = MoverTarefaSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                tarefa_atualizada = TarefaService.mover_tarefa_kanban(
                    tarefa=tarefa,
                    nova_coluna=serializer.validated_data['nova_coluna'],
                    movido_por=request.user
                )
                
                response_serializer = TarefaKanbanSerializer(tarefa_atualizada)
                return Response(response_serializer.data, status=status.HTTP_200_OK)
                
            except (ValueError, PermissionError) as e:
                return Response(
                    {'erro': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def adicionar_comentario(self, request, pk=None):
        """
        Adiciona comentário à tarefa
        """
        tarefa = self.get_object()
        serializer = AdicionarComentarioSerializer(
            data=request.data,
            context={'request': request, 'tarefa': tarefa}
        )
        
        if serializer.is_valid():
            try:
                comentario = serializer.save()
                
                from core.serializers import ComentarioTarefaSerializer
                response_serializer = ComentarioTarefaSerializer(comentario)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except PermissionError as e:
                return Response(
                    {'erro': str(e)}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def upload_anexo(self, request, pk=None):
        """
        Faz upload de anexo para a tarefa
        """
        tarefa = self.get_object()
        arquivo = request.FILES.get('arquivo')
        
        if not arquivo:
            return Response(
                {'erro': 'Arquivo é obrigatório'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            anexo = TarefaService.adicionar_anexo(
                tarefa=tarefa,
                arquivo=arquivo,
                usuario=request.user
            )
            
            from core.serializers import AnexoTarefaSerializer
            serializer = AnexoTarefaSerializer(anexo)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except PermissionError as e:
            return Response(
                {'erro': str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=True, methods=['post'])
    def atribuir_responsavel(self, request, pk=None):
        """
        Atribui novo responsável à tarefa
        """
        tarefa = self.get_object()
        usuario_id = request.data.get('usuario_id')
        
        if not usuario_id:
            return Response(
                {'erro': 'usuario_id é obrigatório'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.contrib.auth.models import User
            novo_responsavel = User.objects.get(id=usuario_id)
            
            tarefa_atualizada = TarefaService.atribuir_responsavel(
                tarefa=tarefa,
                novo_responsavel=novo_responsavel,
                atribuido_por=request.user
            )
            
            serializer = self.get_serializer(tarefa_atualizada)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except (ValueError, PermissionError) as e:
            return Response(
                {'erro': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except User.DoesNotExist:
            return Response(
                {'erro': 'Usuário não encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def kanban(self, request, grupo_pk=None):
        """
        Retorna tarefas organizadas para visualização Kanban
        """
        grupo_id = grupo_pk or self.kwargs.get('grupo_pk')
        
        if not grupo_id:
            return Response(
                {'erro': 'grupo_pk é obrigatório na URL'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            grupo = Grupo.objects.get(id=grupo_id)
            kanban_data = TarefaService.get_tarefas_kanban(grupo, request.user)
            
            # Serializa cada coluna
            resultado = {}
            for coluna, tarefas in kanban_data.items():
                serializer = TarefaKanbanSerializer(tarefas, many=True)
                resultado[coluna] = serializer.data
            
            return Response(resultado)
            
        except Grupo.DoesNotExist:
            return Response(
                {'erro': 'Grupo não encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionError as e:
            return Response(
                {'erro': str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=False, methods=['post'])
    def reordenar_coluna(self, request):
        """
        Reordena tarefas dentro de uma coluna
        """
        grupo_id = self.kwargs.get('grupo_pk')
        serializer = ReordenarTarefasSerializer(data=request.data)
        
        if not grupo_id:
            return Response(
                {'erro': 'grupo_pk é obrigatório na URL'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if serializer.is_valid():
            try:
                grupo = Grupo.objects.get(id=grupo_id)
                
                TarefaService.reordenar_tarefas_coluna(
                    grupo=grupo,
                    coluna=serializer.validated_data['coluna'],
                    ordem_ids=serializer.validated_data['ordem_ids'],
                    usuario=request.user
                )
                
                return Response(
                    {'sucesso': 'Tarefas reordenadas com sucesso'}, 
                    status=status.HTTP_200_OK
                )
                
            except (Grupo.DoesNotExist, PermissionError) as e:
                return Response(
                    {'erro': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def minhas_tarefas(self, request):
        """
        Retorna tarefas atribuídas ao usuário logado
        """
        tarefas = self.get_queryset().filter(
            Q(responsavel_principal=request.user) | 
            Q(colaboradores=request.user)
        ).distinct()
        
        # Filtros opcionais
        status_filter = request.query_params.get('status')
        if status_filter:
            tarefas = tarefas.filter(status=status_filter)
        
        prioridade_filter = request.query_params.get('prioridade')
        if prioridade_filter:
            tarefas = tarefas.filter(prioridade=prioridade_filter)
        
        serializer = self.get_serializer(tarefas, many=True)
        return Response(serializer.data)

class ChecklistItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações em itens do checklist
    """
    permission_classes = [IsAuthenticated, IsGrupoMember]
    
    def get_queryset(self):
        """Retorna itens do checklist da tarefa"""
        tarefa_id = self.kwargs.get('tarefa_pk')
        return ChecklistItem.objects.filter(
            tarefa_id=tarefa_id,
            tarefa__grupo__membros=self.request.user,
            tarefa__grupo__membrogrupo__ativo=True
        ).order_by('ordem')
    
    @action(detail=True, methods=['post'])
    def toggle_concluido(self, request, pk=None):
        """
        Alterna status de conclusão do item
        """
        item = self.get_object()
        serializer = AtualizarChecklistSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                item_atualizado = TarefaService.atualizar_checklist_item(
                    item_id=item.id,
                    concluido=serializer.validated_data['concluido'],
                    usuario=request.user
                )
                
                from core.serializers import ChecklistItemSerializer
                response_serializer = ChecklistItemSerializer(item_atualizado)
                return Response(response_serializer.data, status=status.HTTP_200_OK)
                
            except (ValueError, PermissionError) as e:
                return Response(
                    {'erro': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)