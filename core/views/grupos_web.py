from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.utils import timezone
import uuid

from core.models import Grupo, MembroGrupo, TarefaGrupo, ConviteGrupo
from core.services import GrupoService, TarefaService
from core.serializers import GrupoSerializer, TarefaKanbanSerializer

@login_required
def lista_grupos(request):
    """Lista todos os grupos do usuário"""
    grupos = Grupo.objects.filter(
        membros=request.user,
        membrogrupo__ativo=True,
        ativo=True
    ).select_related('criador').prefetch_related('membros').annotate(
        total_membros=Count('membros', filter=Q(membrogrupo__ativo=True)),
        tarefas_abertas=Count('tarefas', filter=~Q(tarefas__status='concluido')),
        tarefas_concluidas=Count('tarefas', filter=Q(tarefas__status='concluido'))
    )
    
    context = {
        'grupos': grupos,
        'total_grupos': grupos.count()
    }
    return render(request, 'grupos/lista.html', context)

@login_required
def criar_grupo(request):
    """Cria um novo grupo"""
    if request.method == 'POST':
        try:
            dados_grupo = {
                'nome': request.POST.get('nome'),
                'descricao': request.POST.get('descricao'),
                'cor_personalizada': request.POST.get('cor_personalizada', '#3498db')
            }
            
            if 'avatar' in request.FILES:
                dados_grupo['avatar'] = request.FILES['avatar']
            
            grupo = GrupoService.criar_grupo(dados_grupo, request.user)
            messages.success(request, f'Grupo "{grupo.nome}" criado com sucesso!')
            return redirect('detalhe_grupo', grupo_id=grupo.id)
            
        except ValueError as e:
            messages.error(request, str(e))
    
    return render(request, 'grupos/criar.html')

def detalhe_grupo_teste(request, grupo_id):
    """Teste simples sem decorators"""
    from django.http import HttpResponse
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste Grupo {grupo_id}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .btn {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎉 FUNCIONOU! Grupo ID: {grupo_id}</h1>
            <p><strong>Usuário:</strong> {request.user}</p>
            <p><strong>Autenticado:</strong> {request.user.is_authenticated}</p>
            <p><strong>URL acessada:</strong> {request.path}</p>
            <hr>
            <a href="/grupos/" class="btn">← Voltar para Grupos</a>
            <a href="/grupos/teste/{grupo_id}/" class="btn">🔄 Recarregar</a>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)

@login_required
def detalhe_grupo(request, grupo_id):
    """Exibe detalhes do grupo"""
    grupo = get_object_or_404(Grupo, id=grupo_id, ativo=True)
    
    # Verifica se usuário é membro
    if not grupo.membros.filter(id=request.user.id, membrogrupo__ativo=True).exists():
        messages.error(request, 'Você não tem acesso a este grupo.')
        return redirect('lista_grupos')
    
    # Busca membros ativos com seus papéis
    membros = MembroGrupo.objects.filter(
        grupo=grupo, 
        ativo=True
    ).select_related('usuario').order_by('papel')
    
    # Busca todas as tarefas do grupo para estatísticas
    todas_tarefas = TarefaGrupo.objects.filter(grupo=grupo)
    
    # Busca tarefas recentes
    tarefas_recentes = todas_tarefas.select_related('responsavel_principal').order_by('-criado_em')[:5]
    
    # Busca estatísticas de tarefas
    stats_tarefas = {
        'total': todas_tarefas.count(),
        'a_fazer': todas_tarefas.filter(status='a_fazer').count(),
        'em_andamento': todas_tarefas.filter(status='em_andamento').count(),
        'concluidas': todas_tarefas.filter(status='concluido').count(),
    }
    
    context = {
        'grupo': grupo,
        'membros': membros,
        'tarefas_recentes': tarefas_recentes,
        'stats_tarefas': stats_tarefas,
        'papel_usuario': grupo.get_papel_usuario(request.user),
        'is_admin': grupo.is_admin(request.user)
    }
    return render(request, 'grupos/detalhe.html', context)

@login_required
def kanban_view(request, grupo_id):
    """Visualização Kanban do grupo"""
    grupo = get_object_or_404(Grupo, id=grupo_id, ativo=True)
    
    # Verifica se usuário é membro
    if not grupo.membros.filter(id=request.user.id, membrogrupo__ativo=True).exists():
        messages.error(request, 'Você não tem acesso a este grupo.')
        return redirect('lista_grupos')
    
    # Busca tarefas organizadas por coluna
    kanban_data = TarefaService.get_tarefas_kanban(grupo, request.user)
    
    # Membros para filtros
    membros = grupo.membros.filter(membrogrupo__ativo=True)
    
    context = {
        'grupo': grupo,
        'kanban_data': kanban_data,
        'membros': membros,
        'papel_usuario': grupo.get_papel_usuario(request.user),
        'pode_gerenciar': grupo.can_manage_tasks(request.user)
    }
    return render(request, 'grupos/kanban.html', context)

@login_required
def editar_grupo(request, grupo_id):
    """Edita configurações do grupo"""
    grupo = get_object_or_404(Grupo, id=grupo_id, ativo=True)
    
    # Verifica se usuário é administrador
    if not grupo.is_admin(request.user):
        messages.error(request, 'Apenas administradores podem editar o grupo.')
        return redirect('detalhe_grupo', grupo_id=grupo.id)
    
    if request.method == 'POST':
        try:
            grupo.nome = request.POST.get('nome', grupo.nome)
            grupo.descricao = request.POST.get('descricao', grupo.descricao)
            grupo.cor_personalizada = request.POST.get('cor_personalizada', grupo.cor_personalizada)
            
            if 'avatar' in request.FILES:
                grupo.avatar = request.FILES['avatar']
            
            grupo.save()
            messages.success(request, 'Grupo atualizado com sucesso!')
            return redirect('detalhe_grupo', grupo_id=grupo.id)
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar grupo: {str(e)}')
    
    context = {'grupo': grupo}
    return render(request, 'grupos/editar.html', context)

@login_required
def gerenciar_membros(request, grupo_id):
    """Gerencia membros do grupo"""
    grupo = get_object_or_404(Grupo, id=grupo_id, ativo=True)
    
    # Verifica se usuário pode gerenciar membros
    if not grupo.can_manage_tasks(request.user):
        messages.error(request, 'Você não tem permissão para gerenciar membros.')
        return redirect('detalhe_grupo', grupo_id=grupo.id)
    
    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'convidar':
            try:
                email = request.POST.get('email')
                papel = request.POST.get('papel', 'colaborador')
                
                resultado = GrupoService.convidar_membro(grupo, email, papel, request.user)
                
                if resultado['sucesso']:
                    messages.success(request, 'Membro convidado com sucesso!')
                else:
                    messages.warning(request, resultado.get('mensagem', 'Erro ao convidar membro'))
                    
            except Exception as e:
                messages.error(request, str(e))
        
        elif acao == 'gerar_link':
            try:
                papel = request.POST.get('papel', 'colaborador')
                convite = GrupoService.gerar_link_convite(grupo, papel, request.user)
                
                link = request.build_absolute_uri(f'/grupos/convite/{convite.token}/')
                messages.success(request, f'Link de convite gerado: {link}')
                
            except Exception as e:
                messages.error(request, str(e))
        
        elif acao == 'alterar_papel':
            try:
                usuario_id = request.POST.get('usuario_id')
                novo_papel = request.POST.get('novo_papel')
                
                from django.contrib.auth.models import User
                usuario_alvo = User.objects.get(id=usuario_id)
                
                GrupoService.alterar_papel_membro(grupo, usuario_alvo, novo_papel, request.user)
                messages.success(request, 'Papel alterado com sucesso!')
                
            except Exception as e:
                messages.error(request, str(e))
        
        elif acao == 'remover':
            try:
                usuario_id = request.POST.get('usuario_id')
                
                from django.contrib.auth.models import User
                usuario_alvo = User.objects.get(id=usuario_id)
                
                GrupoService.remover_membro(grupo, usuario_alvo, request.user)
                messages.success(request, 'Membro removido com sucesso!')
                
            except Exception as e:
                messages.error(request, str(e))
    
    # Lista membros
    membros = MembroGrupo.objects.filter(
        grupo=grupo, 
        ativo=True
    ).select_related('usuario').order_by('papel', 'entrou_em')
    
    # Convites pendentes
    convites = ConviteGrupo.objects.filter(
        grupo=grupo,
        usado=False,
        expira_em__gt=timezone.now()
    ).order_by('-criado_em')
    
    context = {
        'grupo': grupo,
        'membros': membros,
        'convites': convites,
        'is_admin': grupo.is_admin(request.user),
        'papeis': MembroGrupo.PAPEIS
    }
    return render(request, 'grupos/membros.html', context)

def processar_convite(request, token):
    """Processa convite via link único"""
    if not request.user.is_authenticated:
        messages.info(request, 'Faça login para aceitar o convite.')
        return redirect('login')
    
    try:
        resultado = GrupoService.processar_convite_link(token, request.user)
        
        if resultado['sucesso']:
            messages.success(request, f'Bem-vindo ao grupo {resultado["grupo"].nome}!')
            return redirect('detalhe_grupo', grupo_id=resultado['grupo'].id)
        else:
            messages.error(request, resultado['erro'])
            
    except Exception as e:
        messages.error(request, f'Erro ao processar convite: {str(e)}')
    
    return redirect('lista_grupos')

# AJAX Views para interações dinâmicas

@login_required
@require_http_methods(["POST"])
def mover_tarefa_ajax(request, grupo_id):
    """Move tarefa no Kanban via AJAX"""
    try:
        grupo = get_object_or_404(Grupo, id=grupo_id, ativo=True)
        
        tarefa_id = request.POST.get('tarefa_id')
        nova_coluna = request.POST.get('nova_coluna')
        
        tarefa = get_object_or_404(TarefaGrupo, id=tarefa_id, grupo=grupo)
        
        TarefaService.mover_tarefa_kanban(tarefa, nova_coluna, request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Tarefa movida com sucesso!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def estatisticas_grupo_ajax(request, grupo_id):
    """Retorna estatísticas do grupo via AJAX"""
    try:
        grupo = get_object_or_404(Grupo, id=grupo_id, ativo=True)
        
        if not grupo.membros.filter(id=request.user.id, membrogrupo__ativo=True).exists():
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        
        stats = GrupoService.get_estatisticas_grupo(grupo)
        return JsonResponse(stats)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)