from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from datetime import timedelta
from ..models import Tarefa, Grupo, TransacaoFinanceira

@login_required
def dashboard(request):
    hoje = timezone.now()
    proxima_semana = hoje + timedelta(days=7)
    
    # Buscar todas as tarefas pendentes
    tarefas_queryset = Tarefa.objects.filter(
        Q(responsavel=request.user) | 
        Q(criado_por=request.user) |
        Q(grupo__membros=request.user),
        status__in=['pendente', 'atrasada']
    ).distinct().order_by('data_limite')
    
    # Implementar paginação - 3 tarefas por página
    paginator = Paginator(tarefas_queryset, 3)
    page_number = request.GET.get('page')
    tarefas_page = paginator.get_page(page_number)
    
    context = {
        'tarefas_pendentes': tarefas_page,
        'atividade_grupos': Grupo.objects.filter(
            membros=request.user
        ).annotate(
            tarefas_pendentes=Count('tarefa', filter=Q(tarefa__status='pendente'))
        ),
        'resumo_financeiro': TransacaoFinanceira.objects.filter(
            usuario=request.user,
            data__month=hoje.month
        ).aggregate(
            receitas=Sum('valor', filter=Q(tipo='receita')),
            despesas=Sum('valor', filter=Q(tipo='despesa'))
        )
    }
    return render(request, 'core/dashboard/home.html', context)