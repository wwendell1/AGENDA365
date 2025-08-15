from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from ..models import Grupo, Membro, Tarefa
from ..forms import GrupoForm, ConviteForm

@login_required
def lista_grupos(request):
    """Lista grupos que o usuário participa"""
    grupos = Grupo.objects.filter(
        membros=request.user
    ).distinct()
    
    context = {
        'grupos': grupos
    }
    return render(request, 'core/grupos/lista.html', context)

@login_required
def criar_grupo(request):
    """Cria um novo grupo"""
    if request.method == 'POST':
        form = GrupoForm(request.POST)
        if form.is_valid():
            grupo = form.save(commit=False)
            grupo.criado_por = request.user
            grupo.save()
            
            # Adiciona o criador como membro admin
            Membro.objects.create(
                usuario=request.user,
                grupo=grupo,
                papel='admin'
            )
            
            messages.success(request, 'Grupo criado com sucesso!')
            return redirect('detalhe_grupo', grupo_id=grupo.id)
    else:
        form = GrupoForm()
    
    return render(request, 'core/grupos/form.html', {'form': form})

@login_required
def detalhe_grupo(request, grupo_id):
    """Exibe detalhes do grupo e suas tarefas"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    
    # Verifica se o usuário é membro do grupo
    if not grupo.membros.filter(id=request.user.id).exists():
        messages.error(request, 'Você não tem permissão para acessar este grupo.')
        return redirect('lista_grupos')
    
    # Obtém as tarefas do grupo
    tarefas = Tarefa.objects.filter(grupo=grupo).order_by('-data_limite')
    
    # Verifica se o usuário é admin
    is_admin = grupo.membro_set.filter(usuario=request.user, papel='admin').exists()
    
    context = {
        'grupo': grupo,
        'tarefas': tarefas,
        'membros': grupo.membro_set.all(),
        'is_admin': is_admin
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
    
    if request.method == 'POST':
        form = ConviteForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            # Lógica para adicionar membro
            messages.success(request, f'Membro {email} adicionado com sucesso!')
            return redirect('detalhe_grupo', grupo_id=grupo.id)
    else:
        form = ConviteForm()
    
    return render(request, 'core/grupos/adicionar_membro.html', {'form': form, 'grupo': grupo})

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