from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import auth, dashboard, tarefas, financas, notificacoes
from .views.grupo_views import GrupoViewSet, ConviteViewSet
from .views.tarefa_views import TarefaViewSet, ChecklistItemViewSet
from .views import grupos_web

# Configuração da API REST
router = DefaultRouter()
router.register(r'grupos', GrupoViewSet, basename='grupo')
router.register(r'convites', ConviteViewSet, basename='convite')
router.register(r'tarefas', TarefaViewSet, basename='tarefa')
router.register(r'checklist', ChecklistItemViewSet, basename='checklist')

urlpatterns = [
    # API REST
    path('api/', include(router.urls)),
    path('api/grupos/<int:grupo_pk>/tarefas/', TarefaViewSet.as_view({'get': 'list', 'post': 'create'}), name='grupo-tarefas'),
    path('api/grupos/<int:grupo_pk>/kanban/', TarefaViewSet.as_view({'get': 'kanban'}), name='grupo-kanban'),
    
    # Autenticação
    path('login/', auth.login_view, name='login'),
    path('logout/', auth.logout_view, name='logout'),
    path('registro/', auth.registro_view, name='registro'),
    path('perfil/', auth.perfil_view, name='perfil'),
    path('excluir-conta/', auth.excluir_conta_view, name='excluir_conta'),
    path('recuperar-senha/', auth.recuperar_senha_view, name='recuperar_senha'),
    path('recuperar-senha/<uidb64>/<token>/', auth.redefinir_senha_view, name='redefinir_senha'),
    
    # Dashboard
    path('', dashboard.dashboard, name='dashboard'),
    
    # Grupos - Interface Web
    path('grupos/', grupos_web.lista_grupos, name='lista_grupos'),
    path('grupos/criar/', grupos_web.criar_grupo, name='criar_grupo'),
    path('grupos/<int:grupo_id>/', grupos_web.detalhe_grupo, name='detalhe_grupo'),
    path('grupos/<int:grupo_id>/kanban/', grupos_web.kanban_view, name='grupo_kanban'),
    path('grupos/<int:grupo_id>/editar/', grupos_web.editar_grupo, name='editar_grupo'),
    path('grupos/<int:grupo_id>/membros/', grupos_web.gerenciar_membros, name='gerenciar_membros'),
    path('grupos/convite/<uuid:token>/', grupos_web.processar_convite, name='processar_convite'),
    path('grupos/<int:grupo_id>/mover-tarefa/', grupos_web.mover_tarefa_ajax, name='mover_tarefa_ajax'),
    path('grupos/<int:grupo_id>/stats/', grupos_web.estatisticas_grupo_ajax, name='stats_grupo_ajax'),
    
    # Tarefas - Interface Web  
    path('tarefas/', tarefas.semana_tarefas, name='semana_tarefas'),
    path('tarefas/criar/', tarefas.criar_tarefa, name='criar_tarefa'),
    path('tarefas/<int:tarefa_id>/', tarefas.detalhe_tarefa, name='detalhe_tarefa'),
    path('tarefas/<int:tarefa_id>/editar/', tarefas.editar_tarefa, name='editar_tarefa'),
    path('tarefas/<int:tarefa_id>/excluir/', tarefas.excluir_tarefa, name='excluir_tarefa'),
    
    # Finanças
    path('financas/', financas.lista_transacoes, name='lista_transacoes'),
    path('financas/criar/', financas.nova_transacao, name='criar_transacao'),
    path('financas/<int:transacao_id>/editar/', financas.editar_transacao, name='editar_transacao'),
    path('financas/<int:transacao_id>/excluir/', financas.excluir_transacao, name='excluir_transacao'),
    path('financas/relatorio/', financas.relatorio_mensal, name='relatorio_mensal'),
    path('financas/exportar/excel/', financas.exportar_excel, name='exportar_excel'),
    path('financas/exportar/pdf/', financas.exportar_pdf, name='exportar_pdf'),
    
    # Notificações
    path('notificacoes/', notificacoes.lista_notificacoes, name='lista_notificacoes'),
    path('notificacoes/marcar-lida/<int:pk>/', notificacoes.marcar_como_lida, name='marcar_notificacao_lida'),
    path('notificacoes/configuracoes/', notificacoes.configurar_notificacoes, name='configurar_notificacoes'),
]