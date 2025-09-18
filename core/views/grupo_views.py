from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q

from core.models import Grupo, MembroGrupo, ConviteGrupo
from core.serializers import (
    GrupoSerializer, GrupoCreateSerializer, MembroGrupoSerializer,
    ConviteGrupoSerializer, ConvidarMembroSerializer, AlterarPapelSerializer,
    EstatisticasGrupoSerializer
)
from core.permissions import GrupoPermissions
from core.services import GrupoService

class GrupoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações CRUD em grupos
    """
    serializer_class = GrupoSerializer
    permission_classes = [IsAuthenticated, GrupoPermissions]
    
    def get_queryset(self):
        """Retorna apenas grupos do usuário logado"""
        return Grupo.objects.filter(
            membros=self.request.user,
            membrogrupo__ativo=True,
            ativo=True
        ).select_related('criador').prefetch_related('membros')
    
    def get_serializer_class(self):
        """Retorna serializer apropriado para a ação"""
        if self.action == 'create':
            return GrupoCreateSerializer
        return GrupoSerializer
    
    def perform_create(self, serializer):
        """Cria grupo usando o service"""
        # O GrupoCreateSerializer já usa o service
        pass
    
    @action(detail=True, methods=['post'])
    def convidar_membro(self, request, pk=None):
        """
        Convida um membro para o grupo
        """
        grupo = self.get_object()
        serializer = ConvidarMembroSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Determina se é email ou usuario_id
                if serializer.validated_data.get('email'):
                    email_ou_usuario = serializer.validated_data['email']
                else:
                    from django.contrib.auth.models import User
                    email_ou_usuario = User.objects.get(id=serializer.validated_data['usuario_id'])
                
                resultado = GrupoService.convidar_membro(
                    grupo=grupo,
                    email_ou_usuario=email_ou_usuario,
                    papel=serializer.validated_data['papel'],
                    convidado_por=request.user
                )
                
                # Se foi adicionado diretamente, serializa o membro
                if resultado.get('sucesso') and resultado.get('membro'):
                    membro_serializer = MembroGrupoSerializer(resultado['membro'])
                    return Response({
                        'sucesso': True,
                        'tipo': resultado['tipo'],
                        'membro': membro_serializer.data
                    }, status=status.HTTP_200_OK)
                else:
                    return Response(resultado, status=status.HTTP_200_OK)
                
            except (ValueError, PermissionError) as e:
                return Response(
                    {'erro': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def gerar_convite(self, request, pk=None):
        """
        Gera link de convite para o grupo
        """
        grupo = self.get_object()
        papel = request.data.get('papel', 'colaborador')
        validade_dias = request.data.get('validade_dias', 7)
        
        try:
            convite = GrupoService.gerar_link_convite(
                grupo=grupo,
                papel=papel,
                criado_por=request.user,
                validade_dias=validade_dias
            )
            
            serializer = ConviteGrupoSerializer(convite, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except (ValueError, PermissionError) as e:
            return Response(
                {'erro': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def alterar_papel(self, request, pk=None):
        """
        Altera papel de um membro do grupo
        """
        grupo = self.get_object()
        serializer = AlterarPapelSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                from django.contrib.auth.models import User
                usuario_alvo = User.objects.get(id=serializer.validated_data['usuario_id'])
                
                membro = GrupoService.alterar_papel_membro(
                    grupo=grupo,
                    usuario_alvo=usuario_alvo,
                    novo_papel=serializer.validated_data['novo_papel'],
                    alterado_por=request.user
                )
                
                membro_serializer = MembroGrupoSerializer(membro)
                return Response(membro_serializer.data, status=status.HTTP_200_OK)
                
            except (ValueError, PermissionError) as e:
                return Response(
                    {'erro': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def remover_membro(self, request, pk=None):
        """
        Remove um membro do grupo
        """
        grupo = self.get_object()
        usuario_id = request.data.get('usuario_id')
        
        if not usuario_id:
            return Response(
                {'erro': 'usuario_id é obrigatório'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.contrib.auth.models import User
            usuario_alvo = User.objects.get(id=usuario_id)
            
            GrupoService.remover_membro(
                grupo=grupo,
                usuario_alvo=usuario_alvo,
                removido_por=request.user
            )
            
            return Response(
                {'sucesso': 'Membro removido com sucesso'}, 
                status=status.HTTP_200_OK
            )
            
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
    
    @action(detail=True, methods=['get'])
    def listar_membros(self, request, pk=None):
        """
        Lista membros do grupo
        """
        grupo = self.get_object()
        membros = MembroGrupo.objects.filter(
            grupo=grupo, 
            ativo=True
        ).select_related('usuario').order_by('papel', 'entrou_em')
        
        serializer = MembroGrupoSerializer(membros, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def estatisticas(self, request, pk=None):
        """
        Retorna estatísticas do grupo
        """
        grupo = self.get_object()
        stats = GrupoService.get_estatisticas_grupo(grupo)
        
        serializer = EstatisticasGrupoSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def meus_grupos(self, request):
        """
        Lista grupos do usuário logado com informações resumidas
        """
        grupos = self.get_queryset()
        serializer = self.get_serializer(grupos, many=True)
        return Response(serializer.data)

class ConviteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para visualizar convites (apenas leitura)
    """
    serializer_class = ConviteGrupoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Retorna convites criados pelo usuário"""
        return ConviteGrupo.objects.filter(
            criado_por=self.request.user
        ).select_related('grupo', 'criado_por', 'usado_por')
    
    @action(detail=False, methods=['post'])
    def usar_convite(self, request):
        """
        Usa um convite via token
        """
        token = request.data.get('token')
        
        if not token:
            return Response(
                {'erro': 'Token é obrigatório'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            resultado = GrupoService.processar_convite_link(token, request.user)
            
            if resultado['sucesso']:
                return Response(resultado, status=status.HTTP_200_OK)
            else:
                return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response(
                {'erro': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )