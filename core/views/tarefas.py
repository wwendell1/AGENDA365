from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.template.loader import render_to_string
from ..models import Tarefa, Grupo, ComentarioTarefa, AnexoTarefa, TarefaGrupo
from django.contrib.auth.models import User
from ..forms import TarefaForm, ComentarioForm
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def semana_tarefas(request):
    # Filtros
    grupo_id = request.GET.get('grupo')
    status_list = request.GET.getlist('status')
    responsavel_id = request.GET.get('responsavel')
    
    # Query base - Incluir tarefas de ambos os modelos
    tarefas_grupo = TarefaGrupo.objects.filter(
        Q(responsavel_principal=request.user) | 
        Q(grupo__membros=request.user) |
        Q(criado_por=request.user)
    ).distinct()
    
    # Incluir tarefas do modelo antigo
    tarefas_antigas = Tarefa.objects.filter(
        Q(responsavel=request.user) | 
        Q(grupo__membros=request.user) |
        Q(criado_por=request.user)
    ).distinct()
    
    # Combinar tarefas
    tarefas = list(tarefas_grupo) + list(tarefas_antigas)
    
    # Aplicar filtros
    if grupo_id:
        tarefas = [t for t in tarefas if 
                   (hasattr(t, 'grupo') and t.grupo and str(t.grupo.id) == grupo_id)]
    
    if status_list:
        tarefas = [t for t in tarefas if 
                   (hasattr(t, 'status') and t.status in status_list)]
    
    if responsavel_id:
        tarefas = [t for t in tarefas if 
                   (hasattr(t, 'responsavel_principal') and t.responsavel_principal and str(t.responsavel_principal.id) == responsavel_id) or
                   (hasattr(t, 'responsavel') and t.responsavel and str(t.responsavel.id) == responsavel_id)]
    
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
    
    # Obter a primeira e última data das tarefas para definir o range
    datas = [
        t.prazo.date() if hasattr(t, 'prazo') else 
        t.data_limite.date() if hasattr(t, 'data_limite') else 
        hoje 
        for t in tarefas
    ]
    
    primeira_data = min(datas) if datas else hoje
    ultima_data = max(datas) if datas else hoje
    
    # Garantir que mostramos pelo menos 30 dias a partir de hoje
    data_inicio = min(primeira_data, hoje - timedelta(days=7))  # Incluir 7 dias atrás
    data_fim = max(ultima_data, hoje + timedelta(days=30))
    dias_para_mostrar = (data_fim - data_inicio).days + 1
    data_inicial = data_inicio
    
    for i in range(dias_para_mostrar):
        dia = data_inicial + timedelta(days=i)
        # Filtrar tarefas do dia
        tarefas_dia = [
            t for t in tarefas 
            if (hasattr(t, 'prazo') and t.prazo and t.prazo.date() == dia) or
               (hasattr(t, 'data_limite') and t.data_limite and t.data_limite.date() == dia)
        ]
        
        # Calcular tarefas concluídas
        tarefas_concluidas = sum(1 for t in tarefas_dia if 
            (hasattr(t, 'status') and t.status in ['concluido', 'concluida']))
        
        dias_semana.append({
            'data': dia,
            'nome': nomes_dias[dia.strftime('%A')],
            'tarefas': tarefas_dia,
            'tarefas_concluidas': tarefas_concluidas
        })
    
    # Dados para os filtros - Incluir grupos e usuários relacionados
    grupos = Grupo.objects.filter(
        Q(membros=request.user)
    ).distinct()
    
    usuarios = User.objects.filter(
        Q(grupos_participando__membros=request.user) |
        Q(tarefas_grupo_criadas__grupo__membros=request.user) |
        Q(tarefas_responsavel__grupo__membros=request.user) |
        Q(tarefas_criadas__grupo__membros=request.user)
    ).distinct()
    
    context = {
        'dias_semana': dias_semana,
        'grupos': grupos,
        'users': usuarios,
        'filtro_grupo': grupo_id,
        'filtro_status': status_list[0] if len(status_list) == 1 else ('pendente' if 'pendente' in status_list and 'atrasada' in status_list else status_list[0] if status_list else None),
        'filtro_responsavel': responsavel_id
    }
    
    # Se for uma requisição AJAX, retornar apenas o conteúdo das colunas
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'core/tarefas/semana_colunas.html', context)
    
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
            
            # Verificar permissão
            if not (request.user == tarefa.criado_por or 
                    request.user == tarefa.responsavel or 
                    (tarefa.grupo and request.user in tarefa.grupo.membros.all())):
                return JsonResponse({
                    'success': False,
                    'error': 'Sem permissão para atualizar esta tarefa'
                }, status=403)
            
            # Mapeamento de status para garantir consistência
            status_map = {
                'pendente': 'pendente',
                'concluida': 'concluida',
                'concluido': 'concluida',
                'atrasada': 'atrasada',
                'atrasado': 'atrasada'
            }
            
            # Validar e definir o status
            if novo_status in status_map:
                tarefa.status = status_map[novo_status]
                
                # Lógica adicional para tarefas concluídas
                if novo_status == 'concluida':
                    tarefa.data_conclusao = timezone.now()
                else:
                    tarefa.data_conclusao = None
                
                tarefa.save()
                
                return JsonResponse({
                    'success': True,
                    'status': tarefa.status,
                    'message': 'Status da tarefa atualizado com sucesso'
                })
            
            return JsonResponse({
                'success': False,
                'error': 'Status inválido'
            }, status=400)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Método não permitido'
    }, status=405)

@login_required
def atualizar_status_tarefa_grupo(request, tarefa_id):
    if request.method == 'POST':
        try:
            # Log de depuração detalhado
            logger.info(f"Recebida solicitação de atualização de status para tarefa {tarefa_id}")
            logger.info(f"Corpo da requisição: {request.body}")
            logger.info(f"Tipo de conteúdo: {request.content_type}")
            logger.info(f"Método: {request.method}")
            
            # Tentar parse do JSON com tratamento de erro
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON: {e}")
                return JsonResponse({
                    'success': False,
                    'error': 'Formato de dados inválido'
                }, status=400)
            
            novo_status = data.get('status')
            
            # Log de depuração
            logger.info(f"Novo status solicitado: {novo_status}")
            
            # Verificar se a tarefa existe
            try:
                tarefa = TarefaGrupo.objects.get(id=tarefa_id)
            except TarefaGrupo.DoesNotExist:
                logger.error(f"Tarefa com ID {tarefa_id} não encontrada")
                return JsonResponse({
                    'success': False,
                    'error': 'Tarefa não encontrada'
                }, status=404)
            
            # Verificar permissão
            if not (request.user == tarefa.criado_por or 
                    request.user == tarefa.responsavel_principal or 
                    (tarefa.grupo and request.user in tarefa.grupo.membros.all())):
                logger.warning(f"Usuário {request.user} sem permissão para atualizar tarefa {tarefa_id}")
                return JsonResponse({
                    'success': False,
                    'error': 'Sem permissão para atualizar esta tarefa'
                }, status=403)
            
            # Mapeamento de status para garantir consistência
            status_map = {
                'a_fazer': 'a_fazer',
                'em_andamento': 'em_andamento',
                'concluido': 'concluido',
                'aguardando_feedback': 'aguardando_feedback'
            }
            
            # Validar e definir o status
            if novo_status in status_map:
                status_anterior = tarefa.status
                tarefa.status = status_map[novo_status]
                
                # Log de depuração
                logger.info(f"Status anterior: {status_anterior}, Novo status: {tarefa.status}")
                
                # Registrar mudança de status
                tarefa.registrar_mudanca_status(status_anterior, novo_status, request.user)
                
                try:
                    tarefa.save()
                except Exception as save_error:
                    logger.error(f"Erro ao salvar tarefa: {save_error}")
                    return JsonResponse({
                        'success': False,
                        'error': 'Erro ao salvar a tarefa'
                    }, status=500)
                
                # Log de depuração
                logger.info(f"Tarefa {tarefa_id} atualizada com sucesso")
                
                return JsonResponse({
                    'success': True,
                    'status': tarefa.status,
                    'message': 'Status da tarefa atualizado com sucesso'
                })
            
            # Log de depuração
            logger.warning(f"Status inválido: {novo_status}")
            
            return JsonResponse({
                'success': False,
                'error': 'Status inválido'
            }, status=400)
            
        except Exception as e:
            # Log de depuração
            logger.error(f"Erro ao atualizar status da tarefa {tarefa_id}: {str(e)}")
            
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    # Log de depuração
    logger.warning("Método não permitido para atualização de status")
    
    return JsonResponse({
        'success': False,
        'error': 'Método não permitido'
    }, status=405)

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