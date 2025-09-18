from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from core.models import Grupo, MembroGrupo, ConviteGrupo
from core.services import GrupoService


class GrupoServiceTest(TestCase):
    def setUp(self):
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
        
    def test_criar_grupo_com_dados_validos(self):
        """Testa criação de grupo com dados válidos"""
        dados_grupo = {
            'nome': 'Grupo Teste',
            'descricao': 'Descrição do grupo teste',
            'cor_personalizada': '#ff0000'
        }
        
        grupo = GrupoService.criar_grupo(dados_grupo, self.user1)
        
        self.assertEqual(grupo.nome, 'Grupo Teste')
        self.assertEqual(grupo.descricao, 'Descrição do grupo teste')
        self.assertEqual(grupo.cor_personalizada, '#ff0000')
        self.assertEqual(grupo.criador, self.user1)
        self.assertTrue(grupo.ativo)
        
        # Verifica se criador foi adicionado como administrador
        membro = MembroGrupo.objects.get(usuario=self.user1, grupo=grupo)
        self.assertEqual(membro.papel, 'administrador')
        self.assertTrue(membro.ativo)
    
    def test_criar_grupo_nome_duplicado(self):
        """Testa erro ao criar grupo com nome duplicado"""
        dados_grupo = {'nome': 'Grupo Teste', 'descricao': 'Teste'}
        
        GrupoService.criar_grupo(dados_grupo, self.user1)
        
        with self.assertRaises(ValueError) as context:
            GrupoService.criar_grupo(dados_grupo, self.user2)
        
        self.assertIn('Já existe um grupo com este nome', str(context.exception))
    
    def test_criar_grupo_sem_nome(self):
        """Testa erro ao criar grupo sem nome"""
        dados_grupo = {'descricao': 'Teste'}
        
        with self.assertRaises(ValueError) as context:
            GrupoService.criar_grupo(dados_grupo, self.user1)
        
        self.assertIn('Nome do grupo é obrigatório', str(context.exception))
    
    def test_convidar_membro_por_usuario(self):
        """Testa convite de membro por instância de usuário"""
        grupo = GrupoService.criar_grupo(
            {'nome': 'Grupo Teste', 'descricao': 'Teste'}, 
            self.user1
        )
        
        resultado = GrupoService.convidar_membro(
            grupo, self.user2, 'moderador', self.user1
        )
        
        self.assertTrue(resultado['sucesso'])
        self.assertEqual(resultado['tipo'], 'adicionado_diretamente')
        
        # Verifica se membro foi adicionado
        membro = MembroGrupo.objects.get(usuario=self.user2, grupo=grupo)
        self.assertEqual(membro.papel, 'moderador')
        self.assertTrue(membro.ativo)
    
    def test_convidar_membro_sem_permissao(self):
        """Testa erro ao convidar membro sem permissão"""
        grupo = GrupoService.criar_grupo(
            {'nome': 'Grupo Teste', 'descricao': 'Teste'}, 
            self.user1
        )
        
        # user2 não é membro do grupo
        with self.assertRaises(PermissionError):
            GrupoService.convidar_membro(grupo, self.user2, 'colaborador', self.user2)
    
    def test_convidar_membro_ja_existente(self):
        """Testa erro ao convidar membro que já existe"""
        grupo = GrupoService.criar_grupo(
            {'nome': 'Grupo Teste', 'descricao': 'Teste'}, 
            self.user1
        )
        
        # Adiciona user2 como membro
        GrupoService.convidar_membro(grupo, self.user2, 'colaborador', self.user1)
        
        # Tenta adicionar novamente
        with self.assertRaises(ValueError) as context:
            GrupoService.convidar_membro(grupo, self.user2, 'colaborador', self.user1)
        
        self.assertIn('já é membro do grupo', str(context.exception))
    
    def test_gerar_link_convite(self):
        """Testa geração de link de convite"""
        grupo = GrupoService.criar_grupo(
            {'nome': 'Grupo Teste', 'descricao': 'Teste'}, 
            self.user1
        )
        
        convite = GrupoService.gerar_link_convite(
            grupo, 'colaborador', self.user1, validade_dias=3
        )
        
        self.assertEqual(convite.grupo, grupo)
        self.assertEqual(convite.papel, 'colaborador')
        self.assertEqual(convite.criado_por, self.user1)
        self.assertFalse(convite.usado)
        self.assertTrue(convite.is_valido)
        
        # Verifica data de expiração
        esperado = timezone.now() + timedelta(days=3)
        diferenca = abs((convite.expira_em - esperado).total_seconds())
        self.assertLess(diferenca, 60)  # Diferença menor que 1 minuto
    
    def test_processar_convite_link_valido(self):
        """Testa processamento de convite válido"""
        grupo = GrupoService.criar_grupo(
            {'nome': 'Grupo Teste', 'descricao': 'Teste'}, 
            self.user1
        )
        
        convite = GrupoService.gerar_link_convite(
            grupo, 'colaborador', self.user1
        )
        
        resultado = GrupoService.processar_convite_link(convite.token, self.user2)
        
        self.assertTrue(resultado['sucesso'])
        self.assertEqual(resultado['grupo'], grupo)
        
        # Verifica se convite foi marcado como usado
        convite.refresh_from_db()
        self.assertTrue(convite.usado)
        self.assertEqual(convite.usado_por, self.user2)
        
        # Verifica se membro foi adicionado
        membro = MembroGrupo.objects.get(usuario=self.user2, grupo=grupo)
        self.assertEqual(membro.papel, 'colaborador')
    
    def test_processar_convite_link_invalido(self):
        """Testa processamento de convite inválido"""
        import uuid
        token_inexistente = uuid.uuid4()
        
        resultado = GrupoService.processar_convite_link(token_inexistente, self.user2)
        
        self.assertFalse(resultado['sucesso'])
        self.assertIn('não encontrado', resultado['erro'])
    
    def test_alterar_papel_membro(self):
        """Testa alteração de papel de membro"""
        grupo = GrupoService.criar_grupo(
            {'nome': 'Grupo Teste', 'descricao': 'Teste'}, 
            self.user1
        )
        
        # Adiciona user2 como colaborador
        GrupoService.convidar_membro(grupo, self.user2, 'colaborador', self.user1)
        
        # Altera para moderador
        membro = GrupoService.alterar_papel_membro(
            grupo, self.user2, 'moderador', self.user1
        )
        
        self.assertEqual(membro.papel, 'moderador')
        
        # Verifica no banco
        membro.refresh_from_db()
        self.assertEqual(membro.papel, 'moderador')
    
    def test_alterar_papel_sem_permissao(self):
        """Testa erro ao alterar papel sem permissão"""
        grupo = GrupoService.criar_grupo(
            {'nome': 'Grupo Teste', 'descricao': 'Teste'}, 
            self.user1
        )
        
        GrupoService.convidar_membro(grupo, self.user2, 'colaborador', self.user1)
        
        # user2 (colaborador) tenta alterar papel
        with self.assertRaises(PermissionError):
            GrupoService.alterar_papel_membro(grupo, self.user1, 'colaborador', self.user2)
    
    def test_remover_membro(self):
        """Testa remoção de membro"""
        grupo = GrupoService.criar_grupo(
            {'nome': 'Grupo Teste', 'descricao': 'Teste'}, 
            self.user1
        )
        
        GrupoService.convidar_membro(grupo, self.user2, 'colaborador', self.user1)
        
        # Remove membro
        resultado = GrupoService.remover_membro(grupo, self.user2, self.user1)
        
        self.assertTrue(resultado)
        
        # Verifica se membro foi marcado como inativo
        membro = MembroGrupo.objects.get(usuario=self.user2, grupo=grupo)
        self.assertFalse(membro.ativo)
    
    def test_get_estatisticas_grupo(self):
        """Testa cálculo de estatísticas do grupo"""
        grupo = GrupoService.criar_grupo(
            {'nome': 'Grupo Teste', 'descricao': 'Teste'}, 
            self.user1
        )
        
        # Adiciona alguns membros
        GrupoService.convidar_membro(grupo, self.user2, 'moderador', self.user1)
        
        # Cria algumas tarefas (usando o model diretamente para simplicidade)
        from core.models import TarefaGrupo
        TarefaGrupo.objects.create(
            titulo='Tarefa 1',
            descricao='Teste',
            grupo=grupo,
            criado_por=self.user1,
            status='a_fazer'
        )
        TarefaGrupo.objects.create(
            titulo='Tarefa 2',
            descricao='Teste',
            grupo=grupo,
            criado_por=self.user1,
            status='concluido'
        )
        
        stats = GrupoService.get_estatisticas_grupo(grupo)
        
        # Verifica estrutura das estatísticas
        self.assertIn('tarefas', stats)
        self.assertIn('membros', stats)
        self.assertIn('grupo', stats)
        
        # Verifica dados de tarefas
        self.assertEqual(stats['tarefas']['total'], 2)
        self.assertEqual(stats['tarefas']['a_fazer'], 1)
        self.assertEqual(stats['tarefas']['concluidas'], 1)
        
        # Verifica dados de membros
        self.assertEqual(stats['membros']['total'], 2)
        self.assertEqual(stats['membros']['administradores'], 1)
        self.assertEqual(stats['membros']['moderadores'], 1)
        self.assertEqual(stats['membros']['colaboradores'], 0)