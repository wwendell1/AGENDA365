from django.core.exceptions import ValidationError
from django.utils import timezone

def validar_data_futura(data):
    if data < timezone.now():
        raise ValidationError('A data não pode ser no passado')

def validar_valor_positivo(valor):
    if valor <= 0:
        raise ValidationError('O valor deve ser maior que zero')

def validar_arquivo_tamanho(arquivo):
    if arquivo.size > 5242880:  # 5MB
        raise ValidationError('O arquivo deve ter no máximo 5MB')