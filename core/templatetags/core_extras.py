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