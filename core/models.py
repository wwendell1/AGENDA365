# Todos os models foram organizados em módulos específicos
# Importa todos os models dos módulos organizados
from .models.grupo import *
from .models.tarefa import *
from .models.notificacao import *
from .models.arquivo import *
from .models.legacy import *

class Tarefa(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('concluida', 'Concluída'),
    ]
    titulo = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    data_limite = models.DateTimeField(null=True, blank=True)
