from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from datetime import timedelta
from ..models import Tarefa, Grupo, TransacaoFinanceira, QuadroKanban, CartaoKanban

@login_required
def dashboard(request):
    hoje = timezone.now()
    proxima_semana = hoje + timedelta(days=7)
    
    # Buscar todas as tarefas pendentes e atrasadas (A Fazer)
    tarefas_queryset = Tarefa.objects.filter(
        Q(responsavel=request.user) | 
        Q(criado_por=request.user) |
        Q(grupo__membros=request.user),
        Q(status='pendente') | Q(status='atrasada')
    ).distinct().order_by('data_limite')
    
    # Implementar paginação - 3 tarefas por página
    paginator = Paginator(tarefas_queryset, 3)
    page_number = request.GET.get('page')
    tarefas_page = paginator.get_page(page_number)
    
    # Buscar quadros Kanban do usuário
    quadros_kanban = QuadroKanban.objects.filter(
        grupo__membros=request.user
    ).select_related('grupo').prefetch_related(
        'colunas__cartoes__responsaveis'
    ).distinct()[:6]  # Limitar a 6 quadros no dashboard
    
    context = {
        'tarefas_pendentes': tarefas_page,
        'atividade_grupos': Grupo.objects.filter(
            membros=request.user
        ).annotate(
            tarefas_pendentes=Count('tarefa', filter=Q(tarefa__status='pendente') | Q(tarefa__status='atrasada'))
        ),
        'resumo_financeiro': TransacaoFinanceira.objects.filter(
            usuario=request.user,
            data__month=hoje.month
        ).aggregate(
            receitas=Sum('valor', filter=Q(tipo='receita')),
            despesas=Sum('valor', filter=Q(tipo='despesa'))
        ),
        'quadros_kanban': quadros_kanban
    }
    return render(request, 'core/dashboard/home.html', context)