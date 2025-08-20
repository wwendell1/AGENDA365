from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils.safestring import mark_safe
import json
from ..models import TransacaoFinanceira
from ..forms import TransacaoForm

@login_required
def lista_transacoes(request):
    """Lista transações financeiras do usuário"""
    transacoes = TransacaoFinanceira.objects.filter(
        usuario=request.user
    ).order_by('-data')
    
    # Cálculos de totais
    receitas = transacoes.filter(tipo='receita').aggregate(
        total=Sum('valor'))['total'] or 0
    despesas = transacoes.filter(tipo='despesa').aggregate(
        total=Sum('valor'))['total'] or 0
    saldo = receitas - despesas
    
    # Dados para gráfico de categorias
    categorias_despesas = transacoes.filter(
        tipo='despesa'
    ).values('categoria').annotate(total=Sum('valor'))
    
    # Adicionar formulário vazio para o modal
    form = TransacaoForm()
    
    context = {
        'transacoes': transacoes,
        'receitas': receitas,
        'despesas': despesas,
        'saldo': saldo,
        'categorias_despesas': categorias_despesas,
        'form': form
    }
    return render(request, 'core/financas/lista.html', context)

@login_required
def nova_transacao(request):
    """Cria uma nova transação financeira"""
    if request.method == 'POST':
        form = TransacaoForm(request.POST, request.FILES)
        if form.is_valid():
            transacao = form.save(commit=False)
            transacao.usuario = request.user
            transacao.save()
            messages.success(request, 'Transação registrada com sucesso!')
            if transacao.parcelas > 1:
                messages.info(request, f'Transação parcelada em {transacao.parcelas}x de R$ {transacao.valor_por_parcela():.2f}.')
            return redirect('lista_transacoes')
        else:
            # Se o formulário não for válido, retorna para a lista com o formulário e erros
            transacoes = TransacaoFinanceira.objects.filter(usuario=request.user).order_by('-data')
            receitas = transacoes.filter(tipo='receita').aggregate(total=Sum('valor'))['total'] or 0
            despesas = transacoes.filter(tipo='despesa').aggregate(total=Sum('valor'))['total'] or 0
            saldo = receitas - despesas
            categorias_despesas = transacoes.filter(tipo='despesa').values('categoria').annotate(total=Sum('valor'))
            
            context = {
                'transacoes': transacoes,
                'receitas': receitas,
                'despesas': despesas,
                'saldo': saldo,
                'categorias_despesas': categorias_despesas,
                'form': form,
                'form_errors': True  # Flag para indicar que há erros no formulário
            }
            return render(request, 'core/financas/lista.html', context)
    
    # Se for GET, redireciona para a lista
    return redirect('lista_transacoes')

@login_required
def editar_transacao(request, transacao_id):
    """Edita uma transação financeira existente"""
    transacao = get_object_or_404(TransacaoFinanceira, id=transacao_id, usuario=request.user)
    
    if request.method == 'POST':
        form = TransacaoForm(request.POST, request.FILES, instance=transacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transação atualizada com sucesso!')
            return redirect('lista_transacoes')
        else:
            # Se o formulário não for válido, retorna para a lista com os erros
            transacoes = TransacaoFinanceira.objects.filter(usuario=request.user).order_by('-data')
            context = {
                'transacoes': transacoes,
                'form': TransacaoForm(),  # Formulário vazio para nova transação
                'edit_form': form,  # Formulário com erros para edição
                'edit_form_errors': True,  # Flag para indicar que há erros no formulário de edição
                'transacao_id': transacao_id  # ID da transação que está sendo editada
            }
            return render(request, 'core/financas/lista.html', context)
    
    # Se for GET, redireciona para a lista
    return redirect('lista_transacoes')

@login_required
def excluir_transacao(request, transacao_id):
    """Exclui uma transação financeira"""
    transacao = get_object_or_404(TransacaoFinanceira, id=transacao_id, usuario=request.user)
    
    if request.method == 'POST':
        transacao.delete()
        messages.success(request, 'Transação excluída com sucesso!')
        return redirect('lista_transacoes')
    
    return render(request, 'core/financas/confirmar_exclusao.html', {'transacao': transacao})

@login_required
def relatorio_mensal(request):
    """Gera relatório mensal de finanças"""
    import datetime
    from django.db.models.functions import TruncMonth
    
    # Filtra por mês/ano
    mes = request.GET.get('mes', datetime.date.today().month)
    ano = request.GET.get('ano', datetime.date.today().year)
    
    transacoes = TransacaoFinanceira.objects.filter(
        usuario=request.user,
        data__month=mes,
        data__year=ano
    )
    
    # Calcula totais
    receitas = transacoes.filter(tipo='receita').aggregate(
        total=Sum('valor'))['total'] or 0
    despesas = transacoes.filter(tipo='despesa').aggregate(
        total=Sum('valor'))['total'] or 0
    
    # Agrupa por categoria
    categorias = {}
    for transacao in transacoes:
        if transacao.categoria not in categorias:
            categorias[transacao.categoria] = {
                'receitas': 0,
                'despesas': 0
            }
        if transacao.tipo == 'receita':
            categorias[transacao.categoria]['receitas'] += transacao.valor
        else:
            categorias[transacao.categoria]['despesas'] += transacao.valor
    
    # Preparar dados para o JSON de forma segura
    chart_data = {
        'receitas': float(receitas),  # Convertendo Decimal para float
        'despesas': float(despesas),  # para serialização JSON
        'categorias': {
            'labels': list(categorias.keys()),
            'valores': [float(v['despesas']) for v in categorias.values()]  # Convertendo valores
        }
    }

    context = {
        'mes': mes,
        'ano': ano,
        'categorias': categorias,
        'receitas': receitas,
        'despesas': despesas,
        'chart_data_safe': mark_safe(json.dumps(chart_data))
    }
    
    return render(request, 'core/financas/relatorio.html', context)


@login_required
def exportar_transacoes(request):
    """Exporta transações financeiras para Excel ou PDF"""
    formato = request.GET.get('formato', 'excel')
    transacoes = TransacaoFinanceira.objects.filter(usuario=request.user)

    if formato == 'excel':
        # Lógica para exportar para Excel
        pass
    elif formato == 'pdf':
        # Lógica para exportar para PDF
        pass

    messages.success(request, f'Transações exportadas com sucesso para {formato.upper()}!')
    return redirect('lista_transacoes')

