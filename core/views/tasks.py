from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Tarefa
from ..forms import TarefaForm

@login_required
def lista_tarefas(request):
    tarefas = Tarefa.objects.filter(
        criado_por=request.user
    ).order_by('data_limite')
    return render(request, 'tasks/list.html', {'tarefas': tarefas})

@login_required
def criar_tarefa(request):
    if request.method == 'POST':
        form = TarefaForm(request.POST)
        if form.is_valid():
            tarefa = form.save(commit=False)
            tarefa.criado_por = request.user
            tarefa.save()
            messages.success(request, 'Tarefa criada com sucesso!')
            return redirect('lista_tarefas')
    else:
        form = TarefaForm()
    return render(request, 'tasks/form.html', {'form': form})

@login_required
def editar_tarefa(request, pk):
    tarefa = get_object_or_404(Tarefa, pk=pk, criado_por=request.user)
    if request.method == 'POST':
        form = TarefaForm(request.POST, instance=tarefa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tarefa atualizada com sucesso!')
            return redirect('lista_tarefas')
    else:
        form = TarefaForm(instance=tarefa)
    return render(request, 'tasks/form.html', {'form': form, 'tarefa': tarefa})