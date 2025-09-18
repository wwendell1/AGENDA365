from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import (
    Grupo, 
    MembroGrupo, 
    Tarefa, 
    ConviteGrupo, 
    MensagemChat, 
    ArquivoGrupo, 
    ConfiguracaoGrupo
)
from core.forms import (
    GrupoForm, 
    TarefaForm, 
    ConviteMembroForm, 
    MensagemChatForm, 
    ArquivoGrupoForm, 
    ConfiguracaoGrupoForm
)

class GrupoModelTests(TestCase):
    def setUp(self):
        # Criar usuários de teste
        self.usuario_admin = User.objects.create_user(
            username='admin', 
            email='admin@test.com', 
            password='testpass123'
        )
        self.usuario_membro = User.objects.create_user(
            username='membro', 
            email='membro@test.com', 
            password='testpass123'
        )

    def test_criar_grupo(self):
        """Teste de criação de grupo"""
        grupo = Grupo.objects.create(
            nome='Grupo Teste',
            descricao='Descrição do grupo de teste',
            criado_por=self.usuario_admin,
            cor='#FF6B6B'
        )
        
        # Verifica criação do grupo
        self.assertEqual(grupo.nome, 'Grupo Teste')
        self.assertEqual(grupo.criado_por, self.usuario_admin)

    def test_adicionar_membro_grupo(self):
        """Teste de adição de membro ao grupo"""
        grupo = Grupo.objects.create(
            nome='Grupo Teste', 
            criado_por=self.usuario_admin
        )
        
        # Adiciona membro ao grupo
        membro = MembroGrupo.objects.create(
            user=self.usuario_membro,
            grupo=grupo,
            role='colaborador'
        )
        
        # Verifica adição do membro
        self.assertEqual(membro.user, self.usuario_membro)
        self.assertEqual(membro.grupo, grupo)
        self.assertEqual(membro.role, 'colaborador')

class GrupoPermissoesTests(TestCase):
    def setUp(self):
        # Criar usuários de teste
        self.usuario_admin = User.objects.create_user(
            username='admin', 
            email='admin@test.com', 
            password='testpass123'
        )
        self.usuario_moderador = User.objects.create_user(
            username='moderador', 
            email='moderador@test.com', 
            password='testpass123'
        )
        self.usuario_colaborador = User.objects.create_user(
            username='colaborador', 
            email='colaborador@test.com', 
            password='testpass123'
        )

        # Criar grupo
        self.grupo = Grupo.objects.create(
            nome='Grupo Teste', 
            criado_por=self.usuario_admin
        )

        # Adicionar membros com diferentes papéis
        MembroGrupo.objects.create(
            user=self.usuario_admin, 
            grupo=self.grupo, 
            role='admin'
        )
        MembroGrupo.objects.create(
            user=self.usuario_moderador, 
            grupo=self.grupo, 
            role='moderador'
        )
        MembroGrupo.objects.create(
            user=self.usuario_colaborador, 
            grupo=self.grupo, 
            role='colaborador'
        )

    def test_permissoes_criacao_tarefa(self):
        """Teste de permissões para criação de tarefa"""
        # Admin pode criar tarefa
        self.client.login(username='admin', password='testpass123')
        tarefa_data = {
            'titulo': 'Tarefa de Teste',
            'descricao': 'Descrição da tarefa de teste',
            'responsavel_principal': self.usuario_colaborador.id,
            'prioridade': 'media',
            'status': 'a_fazer'
        }
        response = self.client.post(
            reverse('criar_tarefa', kwargs={'grupo_id': self.grupo.id}), 
            data=tarefa_data
        )
        self.assertEqual(response.status_code, 302)  # Redirecionamento após criação

        # Moderador pode criar tarefa
        self.client.login(username='moderador', password='testpass123')
        response = self.client.post(
            reverse('criar_tarefa', kwargs={'grupo_id': self.grupo.id}), 
            data=tarefa_data
        )
        self.assertEqual(response.status_code, 302)

        # Colaborador NÃO pode criar tarefa
        self.client.login(username='colaborador', password='testpass123')
        response = self.client.post(
            reverse('criar_tarefa', kwargs={'grupo_id': self.grupo.id}), 
            data=tarefa_data
        )
        self.assertEqual(response.status_code, 403)  # Forbidden

class SubTabsTests(TestCase):
    def setUp(self):
        # Criar usuários de teste
        self.usuario_admin = User.objects.create_user(
            username='admin', 
            email='admin@test.com', 
            password='testpass123'
        )

        # Criar grupo
        self.grupo = Grupo.objects.create(
            nome='Grupo Teste', 
            criado_por=self.usuario_admin
        )

        # Adicionar membro admin
        MembroGrupo.objects.create(
            user=self.usuario_admin, 
            grupo=self.grupo, 
            role='admin'
        )

        # Criar configurações de grupo
        ConfiguracaoGrupo.objects.create(
            grupo=self.grupo,
            habilitar_chat=True,
            limite_tamanho_arquivo=10
        )

    def test_chat_grupo(self):
        """Teste de envio de mensagem no chat"""
        self.client.login(username='admin', password='testpass123')
        
        # Enviar mensagem de chat
        response = self.client.post(
            reverse('chat_grupo', kwargs={'grupo_id': self.grupo.id}),
            data={'mensagem': 'Mensagem de teste'}
        )
        
        # Verifica criação da mensagem
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            MensagemChat.objects.filter(
                grupo=self.grupo, 
                mensagem='Mensagem de teste'
            ).exists()
        )

    def test_upload_arquivo(self):
        """Teste de upload de arquivo"""
        self.client.login(username='admin', password='testpass123')
        
        # Criar arquivo de teste
        arquivo_teste = SimpleUploadedFile(
            "teste.txt", 
            b"Conteúdo de teste", 
            content_type="text/plain"
        )
        
        # Enviar arquivo
        response = self.client.post(
            reverse('arquivos_grupo', kwargs={'grupo_id': self.grupo.id}),
            data={
                'arquivo': arquivo_teste,
                'nome': 'Arquivo de Teste'
            }
        )
        
        # Verifica upload
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ArquivoGrupo.objects.filter(
                grupo=self.grupo, 
                nome='Arquivo de Teste'
            ).exists()
        )

    def test_configuracoes_grupo(self):
        """Teste de atualização de configurações"""
        self.client.login(username='admin', password='testpass123')
        
        # Atualizar configurações
        response = self.client.post(
            reverse('configuracoes_grupo', kwargs={'grupo_id': self.grupo.id}),
            data={
                'notificar_novas_tarefas': False,
                'habilitar_chat': False,
                'limite_tamanho_arquivo': 5,
                'visibilidade': 'privado'
            }
        )
        
        # Verifica atualização
        self.assertEqual(response.status_code, 302)
        configuracao = ConfiguracaoGrupo.objects.get(grupo=self.grupo)
        self.assertFalse(configuracao.notificar_novas_tarefas)
        self.assertFalse(configuracao.habilitar_chat)
        self.assertEqual(configuracao.limite_tamanho_arquivo, 5)
        self.assertEqual(configuracao.visibilidade, 'privado')

class FormValidationTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username='testuser', 
            email='test@example.com', 
            password='testpass123'
        )
        self.grupo = Grupo.objects.create(
            nome='Grupo Teste', 
            criado_por=self.usuario
        )

    def test_grupo_form_validation(self):
        """Teste de validação do formulário de grupo"""
        form_data = {
            'nome': 'Novo Grupo',
            'descricao': 'Descrição do grupo',
            'cor': '#FF6B6B'
        }
        form = GrupoForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_tarefa_form_validation(self):
        """Teste de validação do formulário de tarefa"""
        form_data = {
            'titulo': 'Nova Tarefa',
            'descricao': 'Descrição da tarefa',
            'prioridade': 'media',
            'status': 'a_fazer'
        }
        form = TarefaForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_convite_membro_form_validation(self):
        """Teste de validação do formulário de convite"""
        form_data = {
            'emails': 'teste1@example.com\nteste2@example.com',
            'role': 'colaborador'
        }
        form = ConviteMembroForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.cleaned_data['emails']), 2)

class ConviteGrupoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username='admin', 
            email='admin@test.com', 
            password='testpass123'
        )
        self.grupo = Grupo.objects.create(
            nome='Grupo Teste', 
            criado_por=self.usuario
        )

    def test_criar_convite(self):
        """Teste de criação de convite para grupo"""
        convite = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='convidado@test.com',
            role='colaborador',
            token='teste_token_123'
        )
        
        self.assertEqual(convite.grupo, self.grupo)
        self.assertEqual(convite.email, 'convidado@test.com')
        self.assertEqual(convite.role, 'colaborador')
        self.assertIsNone(convite.usado_em)

    def test_aceitar_convite(self):
        """Teste de aceitação de convite"""
        convite = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='convidado@test.com',
            role='colaborador',
            token='teste_token_123'
        )
        
        # Simular aceitação do convite
        self.client.login(username='convidado', password='testpass123')
        response = self.client.get(
            reverse('aceitar_convite', kwargs={'token': convite.token})
        )
        
        # Verifica redirecionamento e criação de membro
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            MembroGrupo.objects.filter(
                grupo=self.grupo, 
                user__email='convidado@test.com'
            ).exists()
        )