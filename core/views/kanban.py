from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ..models import Grupo, QuadroKanban, ColunaKanban, CartaoKanban

@login_required
def visualizar_quadro(request, grupo_id, quadro_id):
    """Visualiza um quadro Kanban específico"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    quadro = get_object_or_404(QuadroKanban, id=quadro_id, grupo=grupo)
    
    # Verifica se o usuário é membro do grupo
    if not grupo.membro_set.filter(usuario=request.user).exists():
        return redirect('listar_grupos')
    
    # Obtém as colunas ordenadas
    colunas = quadro.colunas.order_by('ordem')
    
    # Obtém os cartões por coluna
    cartoes = {}
    for coluna in colunas:
        cartoes[coluna.id] = coluna.cartoes.order_by('ordem')
    
    context = {
        'grupo': grupo,
        'quadro': quadro,
        'colunas': colunas,
        'cartoes': cartoes
    }
    
    return render(request, 'core/grupos/kanban.html', context)

@login_required
def criar_quadro_kanban(request, grupo_id):
    """Cria um novo quadro Kanban para o grupo"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    
    # Verifica se o usuário é membro do grupo
    if not grupo.membro_set.filter(usuario=request.user).exists():
        return redirect('listar_grupos')
    
    if request.method == 'POST':
        nome = request.POST.get('nome')
        descricao = request.POST.get('descricao', '')
        
        if nome:
            # Cria o quadro
            quadro = QuadroKanban.objects.create(
                nome=nome,
                descricao=descricao,
                grupo=grupo,
                criado_por=grupo.membro_set.get(usuario=request.user)
            )
            
            # Cria as colunas padrão
            colunas_padrao = [
                ('A Fazer', 0),
                ('Em Andamento', 1),
                ('Aguardando Feedback', 2),
                ('Concluído', 3)
            ]
            
            for nome_coluna, ordem in colunas_padrao:
                ColunaKanban.objects.create(
                    nome=nome_coluna,
                    quadro=quadro,
                    ordem=ordem
                )
            
            return redirect('visualizar_quadro_kanban', grupo_id=grupo.id, quadro_id=quadro.id)
    
    return render(request, 'grupos/criar_quadro_kanban.html', {'grupo': grupo})