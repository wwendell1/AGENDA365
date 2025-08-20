from django.urls import path
from .views import auth, dashboard, tarefas, grupos, financas, notificacoes

urlpatterns = [
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
    
    # Tarefas
    path('tarefas/', tarefas.semana_tarefas, name='semana_tarefas'),
    path('tarefas/criar/', tarefas.criar_tarefa, name='criar_tarefa'),
    path('tarefas/<int:tarefa_id>/', tarefas.detalhe_tarefa, name='detalhe_tarefa'),
    path('tarefas/<int:tarefa_id>/editar/', tarefas.editar_tarefa, name='editar_tarefa'),
    path('tarefas/<int:tarefa_id>/excluir/', tarefas.excluir_tarefa, name='excluir_tarefa'),
    path('tarefas/<int:tarefa_id>/status/', tarefas.atualizar_status_tarefa, name='atualizar_status_tarefa'),
    path('tarefas/<int:tarefa_id>/comentar/', tarefas.adicionar_comentario, name='adicionar_comentario'),
    
    # Grupos
    path('grupos/', grupos.lista_grupos, name='lista_grupos'),
    path('grupos/criar/', grupos.criar_grupo, name='criar_grupo'),
    path('grupos/<int:grupo_id>/', grupos.detalhe_grupo, name='detalhe_grupo'),
    path('grupos/<int:grupo_id>/editar/', grupos.editar_grupo, name='editar_grupo'),
    path('grupos/<int:grupo_id>/excluir/', grupos.excluir_grupo, name='excluir_grupo'),
    path('grupos/<int:grupo_id>/membros/adicionar/', grupos.adicionar_membro, name='adicionar_membro'),
    path('grupos/<int:grupo_id>/membros/<int:membro_id>/remover/', grupos.remover_membro, name='remover_membro'),
    
    # Finanças
    path('financas/', financas.lista_transacoes, name='lista_transacoes'),
    path('financas/criar/', financas.nova_transacao, name='criar_transacao'),
    path('financas/<int:transacao_id>/editar/', financas.editar_transacao, name='editar_transacao'),
    path('financas/<int:transacao_id>/excluir/', financas.excluir_transacao, name='excluir_transacao'),
    path('financas/relatorio/', financas.relatorio_mensal, name='relatorio_mensal'),
    path('financas/exportar/excel/', financas.exportar_excel, name='exportar_excel'),
    path('financas/exportar/pdf/', financas.exportar_pdf, name='exportar_pdf'),
    path('notificacoes/', notificacoes.lista_notificacoes, name='lista_notificacoes'),
    path('notificacoes/marcar-lida/<int:pk>/', notificacoes.marcar_como_lida, name='marcar_notificacao_lida'),
    path('notificacoes/configuracoes/', notificacoes.configurar_notificacoes, name='configurar_notificacoes'),
]