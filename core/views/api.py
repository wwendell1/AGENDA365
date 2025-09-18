from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.shortcuts import get_object_or_404
import json

from ..models import CartaoKanban, ColunaKanban, QuadroKanban, Grupo

@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def cartao_kanban_detail(request, cartao_id):
    """API para obter, atualizar ou excluir um cartão Kanban"""
    cartao = get_object_or_404(CartaoKanban, id=cartao_id)
    
    # Verifica permissão
    if not cartao.quadro.grupo.membro_set.filter(usuario=request.user).exists():
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    if request.method == 'GET':
        return JsonResponse({
            'id': cartao.id,
            'titulo': cartao.titulo,
            'descricao': cartao.descricao,
            'responsaveis': [r.id for r in cartao.responsaveis.all()],
            'data_limite': cartao.data_limite.strftime('%Y-%m-%d') if cartao.data_limite else None
        })
    
    elif request.method == 'PUT':
        data = json.loads(request.body)
        cartao.titulo = data.get('titulo', cartao.titulo)
        cartao.descricao = data.get('descricao', cartao.descricao)
        cartao.data_limite = data.get('data_limite', cartao.data_limite)
        cartao.save()
        
        # Atualiza responsáveis
        if 'responsaveis' in data:
            cartao.responsaveis.set(data['responsaveis'])
        
        return JsonResponse({'success': True})
    
    elif request.method == 'DELETE':
        cartao.delete()
        return JsonResponse({'success': True})

@login_required
@require_POST
def criar_cartao_kanban(request):
    """API para criar um novo cartão Kanban"""
    data = json.loads(request.body)
    
    # Obtém o quadro e verifica permissão
    quadro = get_object_or_404(QuadroKanban, id=data['quadro_id'])
    if not quadro.grupo.membro_set.filter(usuario=request.user).exists():
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    # Obtém a primeira coluna do quadro
    coluna = quadro.colunas.order_by('ordem').first()
    if not coluna:
        return JsonResponse({'error': 'Quadro sem colunas'}, status=400)
    
    # Cria o cartão
    cartao = CartaoKanban.objects.create(
        titulo=data['titulo'],
        descricao=data.get('descricao', ''),
        coluna=coluna,
        data_limite=data.get('data_limite'),
        ordem=CartaoKanban.objects.filter(coluna=coluna).count()
    )
    
    # Adiciona responsáveis
    if 'responsaveis' in data:
        cartao.responsaveis.set(data['responsaveis'])
    
    return JsonResponse({
        'success': True,
        'cartao': {
            'id': cartao.id,
            'titulo': cartao.titulo
        }
    })

@login_required
@require_POST
def mover_cartao_kanban(request, cartao_id):
    """API para mover um cartão entre colunas"""
    cartao = get_object_or_404(CartaoKanban, id=cartao_id)
    data = json.loads(request.body)
    
    # Verifica permissão
    if not cartao.quadro.grupo.membro_set.filter(usuario=request.user).exists():
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    # Obtém a nova coluna
    nova_coluna = get_object_or_404(ColunaKanban, id=data['coluna_id'])
    
    # Verifica se a coluna pertence ao mesmo quadro
    if nova_coluna.quadro_id != cartao.coluna.quadro_id:
        return JsonResponse({'error': 'Coluna inválida'}, status=400)
    
    # Atualiza a ordem dos cartões na coluna antiga
    CartaoKanban.objects.filter(
        coluna=cartao.coluna,
        ordem__gt=cartao.ordem
    ).update(ordem=models.F('ordem') - 1)
    
    # Atualiza a ordem dos cartões na nova coluna
    nova_ordem = CartaoKanban.objects.filter(coluna=nova_coluna).count()
    
    # Move o cartão
    cartao.coluna = nova_coluna
    cartao.ordem = nova_ordem
    cartao.save()
    
    return JsonResponse({'success': True})