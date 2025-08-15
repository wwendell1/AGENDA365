from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import Tarefa, Grupo, TransacaoFinanceira

class TarefaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_criar_tarefa(self):
        tarefa = Tarefa.objects.create(
            titulo='Teste',
            criado_por=self.user,
            data_limite=timezone.now() + timedelta(days=1)
        )
        self.assertEqual(tarefa.status, 'pendente')
        
    def test_tarefa_atrasada(self):
        tarefa = Tarefa.objects.create(
            titulo='Teste Atrasado',
            criado_por=self.user,
            data_limite=timezone.now() - timedelta(days=1)
        )
        self.assertEqual(tarefa.status, 'atrasada')

class TransacaoFinanceiraTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_criar_transacao(self):
        transacao = TransacaoFinanceira.objects.create(
            usuario=self.user,
            tipo='receita',
            valor=100.00,
            categoria='Salário',
            data=timezone.now().date()
        )
        self.assertEqual(transacao.valor, 100.00)
