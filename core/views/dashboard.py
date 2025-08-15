from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import timedelta
from ..models import Tarefa, Grupo, TransacaoFinanceira

@login_required
def dashboard(request):
    hoje = timezone.now()
    proxima_semana = hoje + timedelta(days=7)
    
    context = {
        'tarefas_pendentes': Tarefa.objects.filter(
            Q(responsavel=request.user) | 
            Q(grupo__membros=request.user),
            status='pendente',
            data_limite__lte=proxima_semana
        ),
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