from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def get_range(value, arg):
    return range(int(value), int(arg))

@register.filter
def sub(value, arg):
    """Subtrai dois números"""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except:
        return 0

@register.filter
def tarefa_cor(tarefa):
    """Retorna a cor da tarefa baseada no status e prioridade"""
    if tarefa.status == 'atrasada':
        return 'is-danger'  # Vermelho para atrasadas
    elif tarefa.status == 'concluida':
        return 'is-success'  # Verde para concluídas
    else:  # pendente
        if tarefa.prioridade == 'alta':
            return 'is-warning'  # Amarelo para alta prioridade
        elif tarefa.prioridade == 'media':
            return 'is-info'  # Azul para média prioridade
        else:  # baixa
            return 'is-light'  # Cinza claro para baixa prioridade