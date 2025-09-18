from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from ..models import Grupo, MembroGrupo, Tarefa, QuadroKanban, ColunaKanban, CartaoKanban, HistoricoMovimentacao
from ..forms import GrupoForm, ConviteForm, QuadroKanbanForm, CartaoKanbanForm
from django.contrib.auth.models import User
import json

@login_required
def lista_grupos(request):
    """Lista grupos que o usuário participa"""
    # Grupos que o usuário administra (é criador ou membro admin)
    grupos_admin = Grupo.objects.filter(
        Q(criador=request.user) |
        Q(membro__usuario=request.user, membro__papel='admin')
    ).distinct()
    
    # Grupos que o usuário é membro (não admin)
    grupos_membro = Grupo.objects.filter(
        membro__usuario=request.user,
        membro__papel='member'
    ).distinct()
    
    # Adiciona o formulário vazio para o modal
    form = GrupoForm(initial={'criador': request.user})
    
    context = {
        'grupos_admin': grupos_admin,
        'grupos_membro': grupos_membro,
        'form': form
    }
    return render(request, 'core/grupos/lista.html', context)

@login_required
def criar_grupo(request):
    """Cria um novo grupo"""
    if request.method == 'POST':
        form = GrupoForm(request.POST)
        if form.is_valid():
            # Cria o grupo com o usuário atual como criador
            grupo = form.save(commit=False)
            grupo.criador = request.user
            grupo.save()
            
            # Adiciona o criador como membro admin
            Membro.objects.create(
                usuario=request.user,
                grupo=grupo,
                papel='admin'
            )
            
            messages.success(request, 'Grupo criado com sucesso!')
            return redirect('lista_grupos')
        else:
            messages.error(request, 'Por favor, corrija os erros no formulário.')
            return redirect('lista_grupos')
    
    return redirect('lista_grupos')

@login_required
def detalhe_grupo_old(request, grupo_id):
    """Exibe detalhes do grupo e suas tarefas"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    
    # Verifica se o usuário é membro do grupo
    membro = grupo.membro_set.filter(usuario=request.user).first()
    if not membro:
        messages.error(request, 'Você não tem permissão para acessar este grupo.')
        return redirect('lista_grupos')
    
    # Obtém as tarefas do grupo
    tarefas = Tarefa.objects.filter(grupo=grupo).order_by('-data_limite')
    
    # Obtém os quadros Kanban do grupo
    quadros = QuadroKanban.objects.filter(grupo=grupo).order_by('-criado_em')
    
    context = {
        'grupo': grupo,
        'tarefas': tarefas,
        'membros': grupo.membro_set.all(),
        'membro': membro,
        'is_admin': membro.papel == 'admin',
        'quadros': quadros
    }
    return render(request, 'core/grupos/detalhe.html', context)

@login_required
def editar_grupo(request, grupo_id):
    """Edita um grupo existente"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    
    # Verifica se o usuário é admin do grupo
    if not grupo.membro_set.filter(usuario=request.user, papel='admin').exists():
        messages.error(request, 'Você não tem permissão para editar este grupo.')
        return redirect('detalhe_grupo', grupo_id=grupo.id)
    
    if request.method == 'POST':
        form = GrupoForm(request.POST, instance=grupo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grupo atualizado com sucesso!')
            return redirect('detalhe_grupo', grupo_id=grupo.id)
    else:
        form = GrupoForm(instance=grupo)
    
    return render(request, 'core/grupos/form.html', {'form': form, 'grupo': grupo})

@login_required
def excluir_grupo(request, grupo_id):
    """Exclui um grupo"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    
    # Verifica se o usuário é admin do grupo
    if not grupo.membro_set.filter(usuario=request.user, papel='admin').exists():
        messages.error(request, 'Você não tem permissão para excluir este grupo.')
        return redirect('detalhe_grupo', grupo_id=grupo.id)
    
    if request.method == 'POST':
        grupo.delete()
        messages.success(request, 'Grupo excluído com sucesso!')
        return redirect('lista_grupos')
    
    return render(request, 'core/grupos/confirmar_exclusao.html', {'grupo': grupo})

@login_required
def adicionar_membro(request, grupo_id):
    """Adiciona um novo membro ao grupo"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    # Verifica se o usuário é admin do grupo
    if not grupo.membro_set.filter(usuario=request.user, papel='admin').exists():
        messages.error(request, 'Você não tem permissão para adicionar membros.')
        return redirect('detalhe_grupo', grupo_id=grupo.id)

    usernames_disponiveis = list(User.objects.exclude(id__in=grupo.membro_set.values_list('usuario_id', flat=True)).values_list('username', flat=True))

    if request.method == 'POST':
        form = ConviteForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            if username.startswith('@'):
                username = username[1:]
            usuario = User.objects.get(username=username)
            papel = form.cleaned_data['papel']
            Membro.objects.create(usuario=usuario, grupo=grupo, papel=papel)
            messages.success(request, f'Membro {usuario.get_full_name() or usuario.username} adicionado com sucesso!')
            return redirect('detalhe_grupo', grupo_id=grupo.id)
    else:
        form = ConviteForm()

    return render(request, 'core/grupos/adicionar_membro.html', {'form': form, 'grupo': grupo, 'usernames_disponiveis': usernames_disponiveis})

@login_required
def criar_quadro_kanban(request, grupo_id):
    """Cria um novo quadro Kanban para o grupo"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    
    # Verifica se o usuário é admin ou moderador do grupo
    membro = grupo.membro_set.filter(usuario=request.user).first()
    if not membro or membro.papel != 'admin':
        messages.error(request, 'Você não tem permissão para criar quadros neste grupo.')
        return redirect('detalhe_grupo', grupo_id=grupo.id)
    
    if request.method == 'POST':
        nome = request.POST.get('nome')
        descricao = request.POST.get('descricao', '')
        template = request.POST.get('template', 'basico')
        
        if nome:
            # Cria o quadro
            quadro = QuadroKanban.objects.create(
                nome=nome,
                descricao=descricao,
                grupo=grupo,
                criado_por=request.user
            )
            
            # Cria as colunas baseadas no template escolhido
            templates_colunas = {
                'basico': ['A Fazer', 'Em Progresso', 'Concluído'],
                'desenvolvimento': ['Backlog', 'Em Desenvolvimento', 'Teste', 'Concluído'],
                'marketing': ['Ideias', 'Planejamento', 'Execução', 'Análise'],
                'personalizado': ['Nova Coluna']
            }
            
            colunas = templates_colunas.get(template, templates_colunas['basico'])
            
            for i, nome_coluna in enumerate(colunas):
                ColunaKanban.objects.create(
                    nome=nome_coluna,
                    quadro=quadro,
                    ordem=i
                )
            
            messages.success(request, f'Quadro "{nome}" criado com sucesso!')
            return redirect('visualizar_quadro', grupo_id=grupo.id, quadro_id=quadro.id)
        else:
            messages.error(request, 'Nome do quadro é obrigatório.')
    
    return redirect('detalhe_grupo', grupo_id=grupo.id)

@login_required
def visualizar_quadro(request, grupo_id, quadro_id):
    """Visualiza um quadro Kanban específico"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    quadro = get_object_or_404(QuadroKanban, id=quadro_id, grupo=grupo)
    
    # Verifica se o usuário é membro do grupo
    membro = grupo.membro_set.filter(usuario=request.user).first()
    if not membro:
        messages.error(request, 'Você não tem permissão para acessar este quadro.')
        return redirect('lista_grupos')
    
    # Obtém as colunas e cartões do quadro
    colunas = ColunaKanban.objects.filter(quadro=quadro).order_by('ordem')
    
    # Para cada coluna, obtém seus cartões
    for coluna in colunas:
        coluna.cartoes_list = CartaoKanban.objects.filter(coluna=coluna).order_by('ordem')
    
    context = {
        'grupo': grupo,
        'quadro': quadro,
        'colunas': colunas,
        'membro': membro,
        'is_admin': membro.papel == 'admin'
    }
    
    return render(request, 'core/grupos/visualizar_quadro.html', context)

@login_required
def criar_cartao(request, grupo_id, quadro_id, coluna_id=None):
    """Cria um novo cartão em uma coluna do quadro Kanban"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    quadro = get_object_or_404(QuadroKanban, id=quadro_id, grupo=grupo)
    
    # Verifica se o usuário é membro do grupo
    membro = grupo.membro_set.filter(usuario=request.user).first()
    if not membro:
        messages.error(request, 'Você não tem permissão para acessar este quadro.')
        return redirect('lista_grupos')
    
    # Obtém o coluna_id da URL ou do parâmetro de consulta
    if not coluna_id and request.GET.get('coluna_id'):
        coluna_id = request.GET.get('coluna_id')
    
    if request.method == 'POST':
        form = CartaoKanbanForm(request.POST, quadro=quadro)
        if form.is_valid():
            cartao = form.save(commit=False)
            cartao.criado_por = request.user
            
            # Se não foi especificada uma coluna, usa a primeira coluna (A Fazer)
            if not coluna_id:
                coluna = ColunaKanban.objects.filter(quadro=quadro).order_by('ordem').first()
            else:
                coluna = get_object_or_404(ColunaKanban, id=coluna_id, quadro=quadro)
                
            cartao.coluna = coluna
            
            # Define a ordem como a última da coluna
            ultimo_cartao = CartaoKanban.objects.filter(coluna=coluna).order_by('-ordem').first()
            cartao.ordem = (ultimo_cartao.ordem + 1) if ultimo_cartao else 0
            
            cartao.save()
            
            # Adiciona os responsáveis, se houver
            if 'responsaveis' in form.cleaned_data:
                cartao.responsaveis.set(form.cleaned_data['responsaveis'])
            
            messages.success(request, 'Cartão criado com sucesso!')
            return redirect('visualizar_quadro', grupo_id=grupo.id, quadro_id=quadro.id)
    else:
        form = CartaoKanbanForm(quadro=quadro)
    
    return render(request, 'core/grupos/cartao_form.html', {
        'form': form,
        'grupo': grupo,
        'quadro': quadro,
        'titulo': 'Criar Novo Cartão'
    })

@login_required
def mover_cartao(request, grupo_id, quadro_id, cartao_id):
    """Move um cartão para outra coluna via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            coluna_destino_id = data.get('coluna_destino_id')
            nova_ordem = data.get('nova_ordem', 0)
            
            grupo = get_object_or_404(Grupo, id=grupo_id)
            quadro = get_object_or_404(QuadroKanban, id=quadro_id, grupo=grupo)
            cartao = get_object_or_404(CartaoKanban, id=cartao_id)
            coluna_destino = get_object_or_404(ColunaKanban, id=coluna_destino_id, quadro=quadro)
            
            # Verifica se o usuário é membro do grupo
            membro = grupo.membro_set.filter(usuario=request.user).first()
            if not membro:
                return JsonResponse({'error': 'Permissão negada'}, status=403)
            
            # Registra a movimentação no histórico
            HistoricoMovimentacao.objects.create(
                cartao=cartao,
                coluna_origem=cartao.coluna,
                coluna_destino=coluna_destino,
                movido_por=request.user
            )
            
            # Atualiza a coluna e ordem do cartão
            cartao.coluna = coluna_destino
            cartao.ordem = nova_ordem
            cartao.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)

@login_required
def editar_quadro_kanban(request, grupo_id, quadro_id):
    """Edita um quadro Kanban existente"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    quadro = get_object_or_404(QuadroKanban, id=quadro_id, grupo=grupo)
    
    # Verifica se o usuário tem permissão para editar
    membro = grupo.membro_set.filter(usuario=request.user).first()
    if not membro or (request.user != grupo.criador and membro.papel != 'admin' and quadro.criado_por != request.user):
        messages.error(request, 'Você não tem permissão para editar este quadro.')
        return redirect('detalhe_grupo', grupo_id=grupo.id)
    
    if request.method == 'POST':
        nome = request.POST.get('nome')
        descricao = request.POST.get('descricao', '')
        
        if nome:
            quadro.nome = nome
            quadro.descricao = descricao
            quadro.save()
            messages.success(request, 'Quadro atualizado com sucesso!')
        else:
            messages.error(request, 'Nome do quadro é obrigatório.')
    
    return redirect('detalhe_grupo', grupo_id=grupo.id)

@login_required
def excluir_quadro_kanban(request, grupo_id, quadro_id):
    """Exclui um quadro Kanban"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    quadro = get_object_or_404(QuadroKanban, id=quadro_id, grupo=grupo)
    
    # Verifica se o usuário tem permissão para excluir
    membro = grupo.membro_set.filter(usuario=request.user).first()
    if not membro or (request.user != grupo.criador and membro.papel != 'admin' and quadro.criado_por != request.user):
        messages.error(request, 'Você não tem permissão para excluir este quadro.')
        return redirect('detalhe_grupo', grupo_id=grupo.id)
    
    if request.method == 'POST':
        nome_quadro = quadro.nome
        quadro.delete()
        messages.success(request, f'Quadro "{nome_quadro}" foi excluído com sucesso!')
    
    return redirect('detalhe_grupo', grupo_id=grupo.id)

@login_required
def remover_membro(request, grupo_id, membro_id):
    """Remove um membro do grupo"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    membro = get_object_or_404(Membro, id=membro_id, grupo=grupo)
    
    # Verifica se o usuário é admin do grupo
    if not grupo.membro_set.filter(usuario=request.user, papel='admin').exists():
        messages.error(request, 'Você não tem permissão para remover membros.')
        return redirect('detalhe_grupo', grupo_id=grupo.id)
    
    # Não permite remover o último admin
    if membro.papel == 'admin' and grupo.membro_set.filter(papel='admin').count() == 1:
        messages.error(request, 'Não é possível remover o último administrador do grupo.')
        return redirect('detalhe_grupo', grupo_id=grupo.id)
    
    membro.delete()
    messages.success(request, 'Membro removido com sucesso!')
    return redirect('detalhe_grupo', grupo_id=grupo.id)