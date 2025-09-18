from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from core.models import Grupo, MembroGrupo, ConviteGrupo

class GrupoService:
    
    @staticmethod
    @transaction.atomic
    def criar_grupo(dados_grupo, criador):
        """
        Cria um novo grupo com configurações padrão
        
        Args:
            dados_grupo (dict): Dados do grupo (nome, descrição, avatar, cor_personalizada)
            criador (User): Usuário que está criando o grupo
            
        Returns:
            Grupo: Instância do grupo criado
            
        Raises:
            ValueError: Se dados são inválidos
        """
        # Validações
        if not dados_grupo.get('nome'):
            raise ValueError("Nome do grupo é obrigatório")
        
        if Grupo.objects.filter(nome=dados_grupo['nome']).exists():
            raise ValueError("Já existe um grupo com este nome")
        
        # Cria o grupo
        grupo = Grupo.objects.create(
            nome=dados_grupo['nome'],
            descricao=dados_grupo.get('descricao', ''),
            avatar=dados_grupo.get('avatar'),
            cor_personalizada=dados_grupo.get('cor_personalizada', '#3498db'),
            criador=criador
        )
        
        # Adiciona o criador como administrador
        MembroGrupo.objects.create(
            usuario=criador,
            grupo=grupo,
            papel='administrador'
        )
        
        return grupo
    
    @staticmethod
    def convidar_membro(grupo, email_ou_usuario, papel, convidado_por):
        """
        Convida um membro por email ou adiciona usuário existente
        
        Args:
            grupo (Grupo): Grupo para adicionar membro
            email_ou_usuario (str|User): Email ou instância do usuário
            papel (str): Papel do membro (administrador, moderador, colaborador)
            convidado_por (User): Usuário que está fazendo o convite
            
        Returns:
            dict: Resultado da operação
        """
        # Verifica permissão do usuário que está convidando
        if not grupo.can_manage_tasks(convidado_por):
            raise PermissionError("Você não tem permissão para convidar membros")
        
        # Valida papel
        papeis_validos = [choice[0] for choice in MembroGrupo.PAPEIS]
        if papel not in papeis_validos:
            raise ValueError(f"Papel inválido. Deve ser um de: {papeis_validos}")
        
        # Se é uma instância de User
        if isinstance(email_ou_usuario, User):
            usuario = email_ou_usuario
            
            # Verifica se já é membro
            if MembroGrupo.objects.filter(usuario=usuario, grupo=grupo, ativo=True).exists():
                raise ValueError("Usuário já é membro do grupo")
            
            # Adiciona como membro
            membro = MembroGrupo.objects.create(
                usuario=usuario,
                grupo=grupo,
                papel=papel
            )
            
            # Cria notificação
            from .notificacao_service import NotificacaoService
            NotificacaoService.criar_notificacao(
                usuario=usuario,
                grupo=grupo,
                tipo='membro_adicionado',
                titulo=f'Você foi adicionado ao grupo {grupo.nome}',
                conteudo=f'{convidado_por.get_full_name() or convidado_por.username} adicionou você como {membro.get_papel_display()}'
            )
            
            return {
                'sucesso': True,
                'tipo': 'adicionado_diretamente',
                'membro': membro
            }
        
        # Se é um email
        else:
            email = email_ou_usuario
            
            # Verifica se usuário existe
            try:
                usuario = User.objects.get(email=email)
                # Recursivamente chama com o usuário encontrado
                return GrupoService.convidar_membro(grupo, usuario, papel, convidado_por)
            except User.DoesNotExist:
                # Usuário não existe - criar convite por email (implementar futuramente)
                return {
                    'sucesso': False,
                    'tipo': 'email_nao_encontrado',
                    'mensagem': 'Usuário com este email não encontrado no sistema'
                }
    
    @staticmethod
    def gerar_link_convite(grupo, papel, criado_por, validade_dias=7):
        """
        Gera link único de convite com token temporário
        
        Args:
            grupo (Grupo): Grupo para o convite
            papel (str): Papel que será atribuído
            criado_por (User): Usuário que está criando o convite
            validade_dias (int): Dias de validade do convite
            
        Returns:
            ConviteGrupo: Instância do convite criado
        """
        # Verifica permissão
        if not grupo.can_manage_tasks(criado_por):
            raise PermissionError("Você não tem permissão para criar convites")
        
        # Calcula data de expiração
        expira_em = timezone.now() + timedelta(days=int(validade_dias))
        
        # Cria o convite
        convite = ConviteGrupo.objects.create(
            grupo=grupo,
            papel=papel,
            criado_por=criado_por,
            expira_em=expira_em
        )
        
        return convite
    
    @staticmethod
    @transaction.atomic
    def processar_convite_link(token, usuario):
        """
        Processa convite via link único
        
        Args:
            token (str): Token do convite
            usuario (User): Usuário que está usando o convite
            
        Returns:
            dict: Resultado do processamento
        """
        try:
            convite = ConviteGrupo.objects.get(token=token)
        except ConviteGrupo.DoesNotExist:
            return {
                'sucesso': False,
                'erro': 'Convite não encontrado'
            }
        
        # Verifica se convite é válido
        if not convite.is_valido:
            return {
                'sucesso': False,
                'erro': 'Convite expirado ou já utilizado'
            }
        
        # Verifica se usuário já é membro
        if MembroGrupo.objects.filter(usuario=usuario, grupo=convite.grupo, ativo=True).exists():
            return {
                'sucesso': False,
                'erro': 'Você já é membro deste grupo'
            }
        
        # Usa o convite
        convite.usar_convite(usuario)
        
        # Adiciona usuário ao grupo
        membro = MembroGrupo.objects.create(
            usuario=usuario,
            grupo=convite.grupo,
            papel=convite.papel
        )
        
        # Cria notificação
        from .notificacao_service import NotificacaoService
        NotificacaoService.criar_notificacao(
            usuario=usuario,
            grupo=convite.grupo,
            tipo='membro_adicionado',
            titulo=f'Bem-vindo ao grupo {convite.grupo.nome}!',
            conteudo=f'Você entrou no grupo como {membro.get_papel_display()}'
        )
        
        return {
            'sucesso': True,
            'grupo_id': convite.grupo.id,
            'grupo_nome': convite.grupo.nome,
            'membro_id': membro.id,
            'papel': membro.papel
        }
    
    @staticmethod
    def alterar_papel_membro(grupo, usuario_alvo, novo_papel, alterado_por):
        """
        Altera papel de um membro com validação de permissões
        
        Args:
            grupo (Grupo): Grupo do membro
            usuario_alvo (User): Usuário que terá o papel alterado
            novo_papel (str): Novo papel
            alterado_por (User): Usuário que está fazendo a alteração
            
        Returns:
            MembroGrupo: Membro com papel atualizado
        """
        # Verifica se quem está alterando tem permissão
        if not grupo.is_admin(alterado_por):
            raise PermissionError("Apenas administradores podem alterar papéis")
        
        # Não pode alterar próprio papel se for o único admin
        if usuario_alvo == alterado_por:
            admins_count = MembroGrupo.objects.filter(
                grupo=grupo, 
                papel='administrador', 
                ativo=True
            ).count()
            
            if admins_count == 1 and novo_papel != 'administrador':
                raise ValueError("Não é possível alterar seu papel. O grupo deve ter pelo menos um administrador.")
        
        # Busca o membro
        try:
            membro = MembroGrupo.objects.get(usuario=usuario_alvo, grupo=grupo, ativo=True)
        except MembroGrupo.DoesNotExist:
            raise ValueError("Usuário não é membro do grupo")
        
        # Valida novo papel
        papeis_validos = [choice[0] for choice in MembroGrupo.PAPEIS]
        if novo_papel not in papeis_validos:
            raise ValueError(f"Papel inválido. Deve ser um de: {papeis_validos}")
        
        # Atualiza papel
        papel_anterior = membro.papel
        membro.papel = novo_papel
        membro.save()
        
        # Cria notificação
        from .notificacao_service import NotificacaoService
        NotificacaoService.criar_notificacao(
            usuario=usuario_alvo,
            grupo=grupo,
            tipo='status_alterado',
            titulo='Seu papel no grupo foi alterado',
            conteudo=f'Seu papel foi alterado de {dict(MembroGrupo.PAPEIS)[papel_anterior]} para {dict(MembroGrupo.PAPEIS)[novo_papel]} por {alterado_por.get_full_name() or alterado_por.username}'
        )
        
        return membro
    
    @staticmethod
    def remover_membro(grupo, usuario_alvo, removido_por):
        """
        Remove um membro do grupo
        
        Args:
            grupo (Grupo): Grupo do membro
            usuario_alvo (User): Usuário a ser removido
            removido_por (User): Usuário que está removendo
            
        Returns:
            bool: True se removido com sucesso
        """
        # Verifica permissão
        if not grupo.is_admin(removido_por):
            raise PermissionError("Apenas administradores podem remover membros")
        
        # Não pode remover a si mesmo se for o único admin
        if usuario_alvo == removido_por:
            admins_count = MembroGrupo.objects.filter(
                grupo=grupo, 
                papel='administrador', 
                ativo=True
            ).count()
            
            if admins_count == 1:
                raise ValueError("Não é possível se remover. O grupo deve ter pelo menos um administrador.")
        
        # Remove o membro (marca como inativo)
        MembroGrupo.objects.filter(
            usuario=usuario_alvo, 
            grupo=grupo
        ).update(ativo=False)
        
        return True
    
    @staticmethod
    def get_estatisticas_grupo(grupo):
        """
        Calcula estatísticas do grupo
        
        Args:
            grupo (Grupo): Grupo para calcular estatísticas
            
        Returns:
            dict: Estatísticas do grupo
        """
        from django.db.models import Count, Q
        
        # Estatísticas de tarefas
        tarefas_stats = grupo.tarefas.aggregate(
            total=Count('id'),
            a_fazer=Count('id', filter=Q(status='a_fazer')),
            em_andamento=Count('id', filter=Q(status='em_andamento')),
            aguardando_feedback=Count('id', filter=Q(status='aguardando_feedback')),
            concluidas=Count('id', filter=Q(status='concluido')),
            atrasadas=Count('id', filter=Q(
                prazo__lt=timezone.now(),
                status__in=['a_fazer', 'em_andamento', 'aguardando_feedback']
            ))
        )
        
        # Estatísticas de membros
        membros_stats = {
            'total': grupo.membros.filter(membrogrupo__ativo=True).count(),
            'administradores': grupo.membros.filter(
                membrogrupo__papel='administrador',
                membrogrupo__ativo=True
            ).count(),
            'moderadores': grupo.membros.filter(
                membrogrupo__papel='moderador',
                membrogrupo__ativo=True
            ).count(),
            'colaboradores': grupo.membros.filter(
                membrogrupo__papel='colaborador',
                membrogrupo__ativo=True
            ).count(),
        }
        
        return {
            'tarefas': tarefas_stats,
            'membros': membros_stats,
            'grupo': {
                'nome': grupo.nome,
                'criado_em': grupo.criado_em,
                'ativo': grupo.ativo
            }
        }