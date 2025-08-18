from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.template.loader import render_to_string
from ..models import Tarefa, Grupo, Comentario, User, Anexo
from ..forms import TarefaForm, ComentarioForm
from datetime import datetime
import json

@login_required
def semana_tarefas(request):
    # Filtros
    grupo_id = request.GET.get('grupo')
    status = request.GET.get('status')
    responsavel_id = request.GET.get('responsavel')
    
    # Query base - Incluir tarefas criadas pelo usuário
    tarefas = Tarefa.objects.filter(
        Q(responsavel=request.user) | 
        Q(grupo__membros=request.user) |
        Q(criado_por=request.user)
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
    
    # Obter a data da última tarefa agendada ou usar hoje + 30 dias como padrão
    ultima_data = tarefas.order_by('-data_limite').values_list('data_limite', flat=True).first()
    if ultima_data:
        ultima_data = ultima_data.date()
        dias_para_mostrar = max((ultima_data - hoje).days + 1, 30)
    else:
        dias_para_mostrar = 30
    
    for i in range(dias_para_mostrar):
        dia = hoje + timedelta(days=i)
        # Filtrar tarefas do dia e ordenar por prioridade e data
        tarefas_dia = tarefas.filter(data_limite__date=dia).order_by(
            'prioridade',
            'data_limite'
        ).select_related('responsavel', 'grupo')
        
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
    
    # Dados para os filtros - Incluir grupos e usuários relacionados
    grupos = Grupo.objects.filter(
        Q(membros=request.user)
    ).distinct()
    
    usuarios = User.objects.filter(
        Q(grupos__membros=request.user) |
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
            
            if novo_status in ['pendente', 'concluida', 'atrasada']:
                tarefa.status = novo_status
                tarefa.save()
                return JsonResponse({
                    'success': True,
                    'status': novo_status
                })
            
            return JsonResponse({
                'success': False,
                'error': 'Status inválido'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Método não permitido'
    })

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
            try:
                # Criar a tarefa com os dados do formulário
                tarefa = form.save(commit=False)
                tarefa.criado_por = request.user
                
                # Combinar data e hora
                data = form.cleaned_data['data']
                hora = form.cleaned_data['hora']
                tarefa.data_limite = timezone.make_aware(
                    datetime.combine(data, hora)
                )
                
                # Salvar a tarefa no banco de dados
                tarefa.save()
                form.save_m2m()  # Salvar relações ManyToMany
                
                # Processar anexos
                for arquivo in request.FILES.getlist('anexos'):
                    Anexo.objects.create(
                        tarefa=tarefa,
                        arquivo=arquivo,
                        nome=arquivo.name,
                        tipo=arquivo.content_type,
                        tamanho=arquivo.size,
                        upload_por=request.user
                    )
                
                # Retornar sucesso
                return JsonResponse({
                    'success': True,
                    'message': 'Tarefa criada com sucesso!',
                    'tarefa': {
                        'id': tarefa.id,
                        'titulo': tarefa.titulo,
                        'descricao': tarefa.descricao,
                        'data_limite': tarefa.data_limite.strftime('%Y-%m-%dT%H:%M:%S'),
                        'responsavel': tarefa.responsavel.username if tarefa.responsavel else None,
                        'status': tarefa.status,
                        'prioridade': tarefa.prioridade
                    }
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Erro ao criar tarefa: {str(e)}'
                })
        else:
            erros = {campo: erros[0] for campo, erros in form.errors.items()}
            return JsonResponse({
                'success': False,
                'message': 'Formulário inválido',
                'errors': erros
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    })

@login_required
def editar_tarefa(request, tarefa_id):
    try:
        tarefa = get_object_or_404(Tarefa, id=tarefa_id)
        
        # Verificar permissão
        if request.user != tarefa.criado_por and \
           (not tarefa.grupo or request.user not in tarefa.grupo.membros.all()):
            return JsonResponse({
                'success': False,
                'message': 'Você não tem permissão para editar esta tarefa'
            })
        
        if request.method == 'POST':
            # Verificar se é uma requisição AJAX para atualizar a data
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                try:
                    nova_data = datetime.strptime(
                        request.POST.get('nova_data'), '%Y-%m-%d'
                    ).date()
                    hora_atual = tarefa.data_limite.time()
                    
                    tarefa.data_limite = timezone.make_aware(
                        datetime.combine(nova_data, hora_atual)
                    )
                    tarefa.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Data atualizada com sucesso'
                    })
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'message': 'Formato de data inválido'
                    })
            else:
                # Requisição normal para edição completa
                form = TarefaForm(request.POST, request.FILES, instance=tarefa)
                if form.is_valid():
                    try:
                        tarefa = form.save(commit=False)
                        
                        # Combinar data e hora
                        data = form.cleaned_data['data']
                        hora = form.cleaned_data['hora']
                        tarefa.data_limite = timezone.make_aware(
                            datetime.combine(data, hora)
                        )
                        
                        tarefa.save()
                        form.save_m2m()
                        
                        # Processar anexos
                        for arquivo in request.FILES.getlist('anexos'):
                            Anexo.objects.create(
                                tarefa=tarefa,
                                arquivo=arquivo,
                                nome=arquivo.name,
                                tipo=arquivo.content_type,
                                tamanho=arquivo.size,
                                upload_por=request.user
                            )
                        
                        return JsonResponse({
                            'success': True,
                            'message': 'Tarefa atualizada com sucesso!'
                        })
                    except Exception as e:
                        return JsonResponse({
                            'success': False,
                            'message': f'Erro ao atualizar tarefa: {str(e)}'
                        })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Formulário inválido',
                        'errors': form.errors
                    })
        else:
            initial = {
                'data': tarefa.data_limite.date(),
                'hora': tarefa.data_limite.time(),
                'grupo': tarefa.grupo.id if tarefa.grupo else None,
                'responsaveis': tarefa.responsaveis.all(),
                'status': tarefa.status
            }
            form = TarefaForm(instance=tarefa, initial=initial)
            
            context = {
                'form': form,
                'tarefa': tarefa
            }
            
            return JsonResponse({
                'success': True,
                'html': render_to_string('core/tarefas/editar.html', context, request=request)
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao processar tarefa: {str(e)}'
        })

@login_required
def excluir_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    
    # Verificar permissão
    if not (request.user == tarefa.criado_por or 
            request.user == tarefa.responsavel or 
            (tarefa.grupo and request.user in tarefa.grupo.membros.all())):
        return JsonResponse({'success': False, 'message': 'Sem permissão para excluir esta tarefa'})
    
    if request.method == 'POST':
        try:
            tarefa.delete()
            return JsonResponse({
                'success': True,
                'message': 'Tarefa excluída com sucesso!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao excluir tarefa: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    })