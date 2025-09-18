from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Retorna um item de um dicionário pela chave"""
    return dictionary.get(key, [])