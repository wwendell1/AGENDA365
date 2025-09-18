from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json

from core.models import Grupo, MembroGrupo, TarefaGrupo
from core.services import GrupoService


class GrupoAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='membro',
            email='membro@test.com',
            password='testpass123'
        )
        
        # Cria um grupo para testes
        self.grupo = GrupoService.criar_grupo(
            {
                'nome': 'Grupo API Test',
                'descricao': 'Grupo para testes da API',
                'cor_personalizada': '#3498db'
            },
            self.user1
        )
    
    def test_listar_grupos_autenticado(self):
        """Testa listagem de grupos para usuário autenticado"""
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('grupo-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nome'], 'Grupo API Test')
        self.assertEqual(response.data[0]['papel_usuario'], 'administrador')
    
    def test_listar_grupos_nao_autenticado(self):
        """Testa listagem de grupos para usuário não autenticado"""
        url = reverse('grupo-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_criar_grupo_via_api(self):
        """Testa criação de grupo via API"""
        self.client.force_authenticate(user=self.user2)
        
        url = reverse('grupo-list')
        data = {
            'nome': 'Novo Grupo API',
            'descricao': 'Grupo criado via API',
            'cor_personalizada': '#ff0000'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nome'], 'Novo Grupo API')
        self.assertEqual(response.data['criador'], self.user2.id)
        
        # Verifica se grupo foi criado no banco
        grupo = Grupo.objects.get(nome='Novo Grupo API')
        self.assertEqual(grupo.criador, self.user2)
        
        # Verifica se criador foi adicionado como administrador
        membro = MembroGrupo.objects.get(usuario=self.user2, grupo=grupo)
        self.assertEqual(membro.papel, 'administrador')
    
    def test_criar_grupo_nome_duplicado(self):
        """Testa erro ao criar grupo com nome duplicado via API"""
        self.client.force_authenticate(user=self.user2)
        
        url = reverse('grupo-list')
        data = {
            'nome': 'Grupo API Test',  # Nome já existe
            'descricao': 'Teste duplicado'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('nome', response.data)
    
    def test_detalhar_grupo(self):
        """Testa detalhamento de grupo específico"""
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('grupo-detail', kwargs={'pk': self.grupo.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nome'], 'Grupo API Test')
        self.assertEqual(response.data['membros_count'], 1)
        self.assertEqual(response.data['papel_usuario'], 'administrador')
    
    def test_detalhar_grupo_sem_acesso(self):
        """Testa erro ao detalhar grupo sem acesso"""
        self.client.force_authenticate(user=self.user2)
        
        url = reverse('grupo-detail', kwargs={'pk': self.grupo.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_convidar_membro_via_api(self):
        """Testa convite de membro via API"""
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('grupo-convidar-membro', kwargs={'pk': self.grupo.id})
        data = {
            'usuario_id': self.user2.id,
            'papel': 'moderador'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['sucesso'])
        
        # Verifica se membro foi adicionado
        membro = MembroGrupo.objects.get(usuario=self.user2, grupo=self.grupo)
        self.assertEqual(membro.papel, 'moderador')
    
    def test_gerar_convite_via_api(self):
        """Testa geração de convite via API"""
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('grupo-gerar-convite', kwargs={'pk': self.grupo.id})
        data = {
            'papel': 'colaborador',
            'validade_dias': 5
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('link_convite', response.data)
        self.assertEqual(response.data['papel'], 'colaborador')
    
    def test_alterar_papel_via_api(self):
        """Testa alteração de papel via API"""
        # Adiciona user2 como colaborador
        GrupoService.convidar_membro(self.grupo, self.user2, 'colaborador', self.user1)
        
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('grupo-alterar-papel', kwargs={'pk': self.grupo.id})
        data = {
            'usuario_id': self.user2.id,
            'novo_papel': 'moderador'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['papel'], 'moderador')
        
        # Verifica no banco
        membro = MembroGrupo.objects.get(usuario=self.user2, grupo=self.grupo)
        self.assertEqual(membro.papel, 'moderador')
    
    def test_listar_membros_via_api(self):
        """Testa listagem de membros via API"""
        # Adiciona user2 como membro
        GrupoService.convidar_membro(self.grupo, self.user2, 'colaborador', self.user1)
        
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('grupo-listar-membros', kwargs={'pk': self.grupo.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Verifica dados dos membros
        usernames = [membro['usuario_username'] for membro in response.data]
        self.assertIn('admin', usernames)
        self.assertIn('membro', usernames)
    
    def test_estatisticas_grupo_via_api(self):
        """Testa endpoint de estatísticas do grupo"""
        # Cria algumas tarefas
        TarefaGrupo.objects.create(
            titulo='Tarefa 1',
            descricao='Teste',
            grupo=self.grupo,
            criado_por=self.user1,
            status='a_fazer'
        )
        TarefaGrupo.objects.create(
            titulo='Tarefa 2',
            descricao='Teste',
            grupo=self.grupo,
            criado_por=self.user1,
            status='concluido'
        )
        
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('grupo-estatisticas', kwargs={'pk': self.grupo.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verifica estrutura das estatísticas
        self.assertIn('tarefas', response.data)
        self.assertIn('membros', response.data)
        self.assertEqual(response.data['tarefas']['total'], 2)
        self.assertEqual(response.data['tarefas']['a_fazer'], 1)
        self.assertEqual(response.data['tarefas']['concluidas'], 1)
    
    def test_usar_convite_via_api(self):
        """Testa uso de convite via API"""
        # Gera convite
        convite = GrupoService.gerar_link_convite(
            self.grupo, 'colaborador', self.user1
        )
        
        self.client.force_authenticate(user=self.user2)
        
        url = reverse('convite-usar-convite')
        data = {'token': str(convite.token)}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['sucesso'])
        self.assertEqual(response.data['grupo']['id'], self.grupo.id)
        
        # Verifica se membro foi adicionado
        membro = MembroGrupo.objects.get(usuario=self.user2, grupo=self.grupo)
        self.assertEqual(membro.papel, 'colaborador')
        
        # Verifica se convite foi marcado como usado
        convite.refresh_from_db()
        self.assertTrue(convite.usado)


class TarefaAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='membro',
            email='membro@test.com',
            password='testpass123'
        )
        
        # Cria grupo e adiciona membros
        self.grupo = GrupoService.criar_grupo(
            {'nome': 'Grupo Teste', 'descricao': 'Teste'},
            self.user1
        )
        GrupoService.convidar_membro(self.grupo, self.user2, 'colaborador', self.user1)
    
    def test_criar_tarefa_via_api(self):
        """Testa criação de tarefa via API"""
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('tarefa-list')
        data = {
            'titulo': 'Nova Tarefa API',
            'descricao': 'Tarefa criada via API',
            'grupo': self.grupo.id,
            'responsavel_principal_id': self.user2.id,
            'prioridade': 'alta'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['titulo'], 'Nova Tarefa API')
        self.assertEqual(response.data['grupo'], self.grupo.id)
        self.assertEqual(response.data['prioridade'], 'alta')
        
        # Verifica se tarefa foi criada no banco
        tarefa = TarefaGrupo.objects.get(titulo='Nova Tarefa API')
        self.assertEqual(tarefa.responsavel_principal, self.user2)
    
    def test_listar_tarefas_kanban(self):
        """Testa listagem de tarefas no formato Kanban"""
        # Cria algumas tarefas
        TarefaGrupo.objects.create(
            titulo='Tarefa A Fazer',
            descricao='Teste',
            grupo=self.grupo,
            criado_por=self.user1,
            status='a_fazer'
        )
        TarefaGrupo.objects.create(
            titulo='Tarefa Concluída',
            descricao='Teste',
            grupo=self.grupo,
            criado_por=self.user1,
            status='concluido'
        )
        
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('grupo-kanban', kwargs={'grupo_pk': self.grupo.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verifica estrutura do Kanban
        self.assertIn('a_fazer', response.data)
        self.assertIn('concluido', response.data)
        self.assertEqual(len(response.data['a_fazer']), 1)
        self.assertEqual(len(response.data['concluido']), 1)
        self.assertEqual(response.data['a_fazer'][0]['titulo'], 'Tarefa A Fazer')
    
    def test_mover_tarefa_kanban_via_api(self):
        """Testa movimentação de tarefa no Kanban via API"""
        tarefa = TarefaGrupo.objects.create(
            titulo='Tarefa Teste',
            descricao='Teste',
            grupo=self.grupo,
            criado_por=self.user1,
            status='a_fazer'
        )
        
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('tarefa-mover-kanban', kwargs={'pk': tarefa.id})
        data = {'nova_coluna': 'em_andamento'}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verifica se tarefa foi movida
        tarefa.refresh_from_db()
        self.assertEqual(tarefa.status, 'em_andamento')
        self.assertEqual(tarefa.coluna_kanban, 'em_andamento')