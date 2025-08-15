from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from ..models import Tarefa, Grupo, Comentario, User
from ..forms import TarefaForm, ComentarioForm
from datetime import datetime
import json

@login_required
def semana_tarefas(request):
    # Filtros
    grupo_id = request.GET.get('grupo')
    status = request.GET.get('status')
    responsavel_id = request.GET.get('responsavel')
    
    # Query base
    tarefas = Tarefa.objects.filter(
        Q(responsavel=request.user) | 
        Q(grupo__membros=request.user)
    ).distinct()
    
    # Aplicar filtros
    if grupo_id:
        tarefas = tarefas.filter(grupo_id=grupo_id)
    if status:
        tarefas = tarefas.filter(status=status)
    if responsavel_id:
        tarefas = tarefas.filter(responsavel_id=responsavel_id)
    
    # Organizar por dias da semana
    from datetime import datetime, timedelta
    dias_semana = []
    hoje = timezone.now().date()
    
    # Nomes dos dias em português
    nomes_dias = {
        'Monday': 'Segunda',
        'Tuesday': 'Terça',
        'Wednesday': 'Quarta',
        'Thursday': 'Quinta',
        'Friday': 'Sexta',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    
    for i in range(7):
        dia = hoje + timedelta(days=i)
        tarefas_dia = tarefas.filter(data_limite__date=dia).order_by('prioridade', 'data_limite')
        
        # Atualizar status de tarefas atrasadas
        for tarefa in tarefas_dia:
            if tarefa.status != 'concluida' and tarefa.data_limite < timezone.now():
                tarefa.status = 'atrasada'
                tarefa.save()
        
        dias_semana.append({
            'data': dia,
            'nome': nomes_dias[dia.strftime('%A')],
            'tarefas': tarefas_dia
        })
    
    # Dados para os filtros
    grupos = Grupo.objects.filter(membros=request.user)
    usuarios = User.objects.filter(
        Q(tarefas_criadas__grupo__membros=request.user) |
        Q(tarefas_atribuidas__grupo__membros=request.user)
    ).distinct()
    
    context = {
        'dias_semana': dias_semana,
        'grupos': grupos,
        'users': usuarios,
        'filtro_grupo': grupo_id,
        'filtro_status': status,
        'filtro_responsavel': responsavel_id
    }
    
    return render(request, 'core/tarefas/semana.html', context)

@login_required
def detalhe_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    
    # Verificar permissão
    if not (request.user == tarefa.criado_por or 
            request.user == tarefa.responsavel or 
            (tarefa.grupo and request.user in tarefa.grupo.membros.all())):
        return redirect('semana_tarefas')
    
    # Obter histórico completo
    historico = tarefa.get_historico_completo()
    
    # Obter usuários para menções
    if tarefa.grupo:
        users = tarefa.grupo.membros.all()
    else:
        users = User.objects.filter(
            Q(id=tarefa.criado_por.id) |
            Q(id=tarefa.responsavel.id if tarefa.responsavel else None)
        ).distinct()
    
    context = {
        'tarefa': tarefa,
        'historico': historico,
        'users': users
    }
    
    return render(request, 'core/tarefas/detalhe.html', context)

@login_required
def atualizar_status_tarefa(request, tarefa_id):
    if request.method == 'POST':
        try:
            tarefa = get_object_or_404(Tarefa, id=tarefa_id)
            data = json.loads(request.body)
            novo_status = data.get('status')
            
            if novo_status in ['pendente', 'concluida']:
                tarefa.status = novo_status
                tarefa.save()
                return JsonResponse({'success': True})
            
            return JsonResponse({'success': False, 'error': 'Status inválido'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

@login_required
def adicionar_comentario(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    
    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.tarefa = tarefa
            comentario.autor = request.user
            comentario.save()
            
            # Processar menções
            form.save_m2m()  # Salva as relações ManyToMany
            
            return redirect('detalhe_tarefa', tarefa_id=tarefa.id)
    
    return redirect('detalhe_tarefa', tarefa_id=tarefa.id)

@login_required
def criar_tarefa(request):
    if request.method == 'POST':
        form = TarefaForm(request.POST, request.FILES)
        if form.is_valid():
            tarefa = form.save(commit=False)
            tarefa.criado_por = request.user
            
            # Combinar data e hora
            data = form.cleaned_data['data']
            hora = form.cleaned_data['hora']
            tarefa.data_limite = timezone.make_aware(
                datetime.combine(data, hora)
            )
            
            tarefa.save()
            
            # Processar anexos
            for arquivo in request.FILES.getlist('anexos'):
                Anexo.objects.create(
                    tarefa=tarefa,
                    arquivo=arquivo,
                    nome=arquivo.name
                )
            
            return redirect('semana_tarefas')
    else:
        form = TarefaForm()
    
    return redirect('semana_tarefas')

@login_required
def editar_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    
    # Verificar permissão
    if not (request.user == tarefa.criado_por or 
            request.user == tarefa.responsavel or 
            (tarefa.grupo and request.user in tarefa.grupo.membros.all())):
        return redirect('semana_tarefas')
    
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Requisição AJAX para atualizar data
            data = json.loads(request.body)
            nova_data = datetime.strptime(data['nova_data'], '%d/%m/%Y').date()
            hora_atual = tarefa.data_limite.time()
            
            tarefa.data_limite = timezone.make_aware(
                datetime.combine(nova_data, hora_atual)
            )
            tarefa.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Data atualizada com sucesso'
            })
        else:
            # Requisição normal do formulário
            form = TarefaForm(request.POST, request.FILES, instance=tarefa)
            if form.is_valid():
                tarefa = form.save(commit=False)
                
                # Combinar data e hora
                data = form.cleaned_data['data']
                hora = form.cleaned_data['hora']
                tarefa.data_limite = timezone.make_aware(
                    datetime.combine(data, hora)
                )
                
                tarefa.save()
                
                # Processar anexos
                for arquivo in request.FILES.getlist('anexos'):
                    Anexo.objects.create(
                        tarefa=tarefa,
                        arquivo=arquivo,
                        nome=arquivo.name
                    )
                
                return redirect('detalhe_tarefa', tarefa_id=tarefa.id)
    else:
        initial = {
            'data': tarefa.data_limite.date(),
            'hora': tarefa.data_limite.time()
        }
        form = TarefaForm(instance=tarefa, initial=initial)
    
    context = {
        'form': form,
        'tarefa': tarefa
    }
    
    return render(request, 'core/tarefas/editar.html', context)

@login_required
def excluir_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    
    # Verificar permissão
    if request.user == tarefa.criado_por or \
       (tarefa.grupo and request.user in tarefa.grupo.membros.all()):
        tarefa.delete()
    
    return redirect('semana_tarefas')