from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from core.models.grupo import Grupo, MembroGrupo, ConviteGrupo


class GrupoModelTest(TestCase):
    """Testes para o model Grupo"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2', 
            email='test2@example.com',
            password='testpass123'
        )

    def test_criar_grupo_com_dados_validos(self):
        """Testa criação de grupo com dados válidos"""
        grupo = Grupo.objects.create(
            nome='Grupo Teste',
            descricao='Descrição do grupo teste',
            cor_personalizada='#FF5733',
            criador=self.user1
        )
        
        self.assertEqual(grupo.nome, 'Grupo Teste')
        self.assertEqual(grupo.descricao, 'Descrição do grupo teste')
        self.assertEqual(grupo.cor_personalizada, '#FF5733')
        self.assertEqual(grupo.criador, self.user1)
        self.assertTrue(grupo.ativo)
        self.assertIsNotNone(grupo.criado_em)
        self.assertIsNotNone(grupo.atualizado_em)

    def test_validacao_nome_unico(self):
        """Testa validação de nome único"""
        Grupo.objects.create(
            nome='Grupo Único',
            descricao='Primeiro grupo',
            criador=self.user1
        )
        
        # Tenta criar outro grupo com mesmo nome
        grupo2 = Grupo(
            nome='Grupo Único',
            descricao='Segundo grupo',
            criador=self.user2
        )
        
        with self.assertRaises(ValidationError):
            grupo2.full_clean()

    def test_validacao_nome_unico_case_insensitive(self):
        """Testa validação de nome único case-insensitive"""
        Grupo.objects.create(
            nome='Grupo Teste',
            descricao='Primeiro grupo',
            criador=self.user1
        )
        
        grupo2 = Grupo(
            nome='GRUPO TESTE',
            descricao='Segundo grupo',
            criador=self.user2
        )
        
        with self.assertRaises(ValidationError):
            grupo2.full_clean()

    def test_validacao_cor_hexadecimal_valida(self):
        """Testa validação de cor hexadecimal válida"""
        cores_validas = ['#FF5733', '#000000', '#FFFFFF', '#123ABC']
        
        for cor in cores_validas:
            grupo = Grupo(
                nome=f'Grupo {cor}',
                descricao='Teste cor',
                cor_personalizada=cor,
                criador=self.user1
            )
            # Não deve levantar exceção
            grupo.full_clean()

    def test_validacao_cor_hexadecimal_invalida(self):
        """Testa validação de cor hexadecimal inválida"""
        cores_invalidas = ['FF5733', '#FF57', '#GGGGGG', 'azul', '#FF5733XX']
        
        for cor in cores_invalidas:
            grupo = Grupo(
                nome=f'Grupo {cor}',
                descricao='Teste cor',
                cor_personalizada=cor,
                criador=self.user1
            )
            with self.assertRaises(ValidationError):
                grupo.full_clean()

    def test_criador_automaticamente_vira_administrador(self):
        """Testa se criador automaticamente vira administrador"""
        grupo = Grupo.objects.create(
            nome='Grupo Admin',
            descricao='Teste admin automático',
            criador=self.user1
        )
        
        # Verifica se foi criado o MembroGrupo
        membro = MembroGrupo.objects.get(usuario=self.user1, grupo=grupo)
        self.assertEqual(membro.papel, 'administrador')
        self.assertTrue(membro.ativo)

    def test_get_avatar_url_com_avatar(self):
        """Testa get_avatar_url quando há avatar"""
        grupo = Grupo.objects.create(
            nome='Grupo Avatar',
            descricao='Teste avatar',
            criador=self.user1
        )
        # Simula avatar (sem fazer upload real)
        grupo.avatar.name = 'grupos/avatares/test.jpg'
        
        self.assertIn('test.jpg', grupo.get_avatar_url())

    def test_get_avatar_url_sem_avatar(self):
        """Testa get_avatar_url quando não há avatar"""
        grupo = Grupo.objects.create(
            nome='Grupo Sem Avatar',
            descricao='Teste sem avatar',
            criador=self.user1
        )
        
        self.assertEqual(grupo.get_avatar_url(), '/static/img/grupo-default.png')

    def test_get_membros_count(self):
        """Testa contagem de membros"""
        grupo = Grupo.objects.create(
            nome='Grupo Membros',
            descricao='Teste contagem',
            criador=self.user1
        )
        
        # Adiciona mais um membro
        MembroGrupo.objects.create(
            usuario=self.user2,
            grupo=grupo,
            papel='colaborador'
        )
        
        self.assertEqual(grupo.get_membros_count(), 2)

    def test_get_papel_usuario(self):
        """Testa obtenção do papel do usuário"""
        grupo = Grupo.objects.create(
            nome='Grupo Papel',
            descricao='Teste papel',
            criador=self.user1
        )
        
        # Criador deve ser administrador
        self.assertEqual(grupo.get_papel_usuario(self.user1), 'administrador')
        
        # Usuário não membro deve retornar None
        self.assertIsNone(grupo.get_papel_usuario(self.user2))

    def test_usuario_pode_gerenciar(self):
        """Testa verificação de permissão de gerenciamento"""
        grupo = Grupo.objects.create(
            nome='Grupo Gerenciar',
            descricao='Teste gerenciamento',
            criador=self.user1
        )
        
        # Administrador pode gerenciar
        self.assertTrue(grupo.usuario_pode_gerenciar(self.user1))
        
        # Adiciona moderador
        MembroGrupo.objects.create(
            usuario=self.user2,
            grupo=grupo,
            papel='moderador'
        )
        
        # Moderador pode gerenciar
        self.assertTrue(grupo.usuario_pode_gerenciar(self.user2))

    def test_usuario_e_administrador(self):
        """Testa verificação de administrador"""
        grupo = Grupo.objects.create(
            nome='Grupo Admin Check',
            descricao='Teste admin check',
            criador=self.user1
        )
        
        # Criador é administrador
        self.assertTrue(grupo.usuario_e_administrador(self.user1))
        
        # Usuário não membro não é administrador
        self.assertFalse(grupo.usuario_e_administrador(self.user2))


class MembroGrupoModelTest(TestCase):
    """Testes para o model MembroGrupo"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com', 
            password='testpass123'
        )
        self.grupo = Grupo.objects.create(
            nome='Grupo Teste',
            descricao='Grupo para testes',
            criador=self.user1
        )

    def test_criar_membro_grupo_valido(self):
        """Testa criação de membro válido"""
        membro = MembroGrupo.objects.create(
            usuario=self.user2,
            grupo=self.grupo,
            papel='colaborador'
        )
        
        self.assertEqual(membro.usuario, self.user2)
        self.assertEqual(membro.grupo, self.grupo)
        self.assertEqual(membro.papel, 'colaborador')
        self.assertTrue(membro.ativo)
        self.assertIsNotNone(membro.entrou_em)

    def test_validacao_membro_unico_por_grupo(self):
        """Testa validação de membro único por grupo"""
        # Cria primeiro membro
        MembroGrupo.objects.create(
            usuario=self.user2,
            grupo=self.grupo,
            papel='colaborador'
        )
        
        # Tenta criar segundo membro com mesmo usuário e grupo
        membro2 = MembroGrupo(
            usuario=self.user2,
            grupo=self.grupo,
            papel='moderador'
        )
        
        with self.assertRaises(ValidationError):
            membro2.full_clean()

    def test_pode_alterar_papel_administrador(self):
        """Testa se administrador pode alterar qualquer papel"""
        membro_admin = MembroGrupo.objects.get(
            usuario=self.user1,
            grupo=self.grupo
        )
        
        self.assertTrue(membro_admin.pode_alterar_papel_para('moderador'))
        self.assertTrue(membro_admin.pode_alterar_papel_para('colaborador'))

    def test_pode_alterar_papel_moderador(self):
        """Testa se moderador pode alterar apenas para colaborador"""
        membro_mod = MembroGrupo.objects.create(
            usuario=self.user2,
            grupo=self.grupo,
            papel='moderador'
        )
        
        self.assertTrue(membro_mod.pode_alterar_papel_para('colaborador'))
        self.assertFalse(membro_mod.pode_alterar_papel_para('administrador'))

    def test_pode_alterar_papel_colaborador(self):
        """Testa se colaborador não pode alterar papéis"""
        membro_colab = MembroGrupo.objects.create(
            usuario=self.user2,
            grupo=self.grupo,
            papel='colaborador'
        )
        
        self.assertFalse(membro_colab.pode_alterar_papel_para('moderador'))
        self.assertFalse(membro_colab.pode_alterar_papel_para('administrador'))


class ConviteGrupoModelTest(TestCase):
    """Testes para o model ConviteGrupo"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        self.grupo = Grupo.objects.create(
            nome='Grupo Teste',
            descricao='Grupo para testes',
            criador=self.user1
        )

    def test_criar_convite_valido(self):
        """Testa criação de convite válido"""
        convite = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='novo@example.com',
            papel='colaborador',
            convidado_por=self.user1
        )
        
        self.assertEqual(convite.grupo, self.grupo)
        self.assertEqual(convite.email, 'novo@example.com')
        self.assertEqual(convite.papel, 'colaborador')
        self.assertEqual(convite.convidado_por, self.user1)
        self.assertTrue(convite.ativo)
        self.assertIsNotNone(convite.token)
        self.assertIsNotNone(convite.expira_em)

    def test_token_unico_gerado_automaticamente(self):
        """Testa se token único é gerado automaticamente"""
        convite1 = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='user1@example.com',
            convidado_por=self.user1
        )
        
        convite2 = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='user2@example.com',
            convidado_por=self.user1
        )
        
        self.assertNotEqual(convite1.token, convite2.token)
        self.assertEqual(len(convite1.token), 64)
        self.assertEqual(len(convite2.token), 64)

    def test_data_expiracao_automatica(self):
        """Testa se data de expiração é definida automaticamente"""
        convite = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='test@example.com',
            convidado_por=self.user1
        )
        
        # Deve expirar em 7 dias
        esperado = timezone.now() + timedelta(days=7)
        diferenca = abs((convite.expira_em - esperado).total_seconds())
        self.assertLess(diferenca, 60)  # Diferença menor que 1 minuto

    def test_esta_expirado(self):
        """Testa verificação de expiração"""
        # Convite não expirado
        convite_valido = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='valido@example.com',
            convidado_por=self.user1
        )
        self.assertFalse(convite_valido.esta_expirado())
        
        # Convite expirado
        convite_expirado = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='expirado@example.com',
            convidado_por=self.user1,
            expira_em=timezone.now() - timedelta(days=1)
        )
        self.assertTrue(convite_expirado.esta_expirado())

    def test_pode_ser_aceito(self):
        """Testa verificação se convite pode ser aceito"""
        # Convite válido
        convite_valido = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='valido@example.com',
            convidado_por=self.user1
        )
        self.assertTrue(convite_valido.pode_ser_aceito())
        
        # Convite inativo
        convite_inativo = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='inativo@example.com',
            convidado_por=self.user1,
            ativo=False
        )
        self.assertFalse(convite_inativo.pode_ser_aceito())
        
        # Convite expirado
        convite_expirado = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='expirado@example.com',
            convidado_por=self.user1,
            expira_em=timezone.now() - timedelta(days=1)
        )
        self.assertFalse(convite_expirado.pode_ser_aceito())

    def test_aceitar_convite_valido(self):
        """Testa aceitação de convite válido"""
        convite = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email=self.user2.email,
            papel='moderador',
            convidado_por=self.user1
        )
        
        convite.aceitar(self.user2)
        
        # Verifica se membro foi criado
        membro = MembroGrupo.objects.get(
            usuario=self.user2,
            grupo=self.grupo
        )
        self.assertEqual(membro.papel, 'moderador')
        
        # Verifica se convite foi marcado como aceito
        convite.refresh_from_db()
        self.assertIsNotNone(convite.aceito_em)
        self.assertFalse(convite.ativo)

    def test_aceitar_convite_email_diferente(self):
        """Testa erro ao aceitar convite com email diferente"""
        convite = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='outro@example.com',
            convidado_por=self.user1
        )
        
        with self.assertRaises(ValidationError):
            convite.aceitar(self.user2)

    def test_aceitar_convite_usuario_ja_membro(self):
        """Testa erro ao aceitar convite sendo já membro"""
        # Adiciona user2 como membro
        MembroGrupo.objects.create(
            usuario=self.user2,
            grupo=self.grupo,
            papel='colaborador'
        )
        
        convite = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email=self.user2.email,
            convidado_por=self.user1
        )
        
        with self.assertRaises(ValidationError):
            convite.aceitar(self.user2)

    def test_cancelar_convite(self):
        """Testa cancelamento de convite"""
        convite = ConviteGrupo.objects.create(
            grupo=self.grupo,
            email='cancelar@example.com',
            convidado_por=self.user1
        )
        
        convite.cancelar()
        
        convite.refresh_from_db()
        self.assertFalse(convite.ativo)