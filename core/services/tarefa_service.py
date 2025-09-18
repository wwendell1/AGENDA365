from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from django.db import models
from core.models import TarefaGrupo, ChecklistItem, ComentarioTarefa, AnexoTarefa

class TarefaService:
    
    @staticmethod
    @transaction.atomic
    def criar_tarefa(dados_tarefa, grupo, criador):
        """
        Cria nova tarefa com validações e notificações
        
        Args:
            dados_tarefa (dict): Dados da tarefa
            grupo (Grupo): Grupo da tarefa
            criador (User): Usuário criador
            
        Returns:
            TarefaGrupo: Tarefa criada
        """
        # Verifica permissão
        if not grupo.can_manage_tasks(criador):
            raise PermissionError("Você não tem permissão para criar tarefas neste grupo")
        
        # Validações obrigatórias
        if not dados_tarefa.get('titulo'):
            raise ValueError("Título da tarefa é obrigatório")
        
        if not dados_tarefa.get('descricao'):
            raise ValueError("Descrição da tarefa é obrigatória")
        
        # Valida responsável principal se fornecido
        responsavel_principal = None
        if dados_tarefa.get('responsavel_principal_id'):
            try:
                responsavel_principal = User.objects.get(id=dados_tarefa['responsavel_principal_id'])
                # Verifica se é membro do grupo
                if not grupo.membros.filter(id=responsavel_principal.id, membrogrupo__ativo=True).exists():
                    raise ValueError("Responsável deve ser membro do grupo")
            except User.DoesNotExist:
                raise ValueError("Responsável principal não encontrado")
        
        # Calcula ordem no Kanban
        max_ordem = TarefaGrupo.objects.filter(
            grupo=grupo,
            coluna_kanban='a_fazer'
        ).aggregate(max_ordem=models.Max('ordem_kanban'))['max_ordem'] or 0
        
        # Cria a tarefa
        tarefa = TarefaGrupo.objects.create(
            titulo=dados_tarefa['titulo'],
            descricao=dados_tarefa['descricao'],
            grupo=grupo,
            responsavel_principal=responsavel_principal,
            criado_por=criador,
            prazo=dados_tarefa.get('prazo'),
            prioridade=dados_tarefa.get('prioridade', 'media'),
            ordem_kanban=max_ordem + 1
        )
        
        # Adiciona colaboradores se fornecidos
        colaboradores_ids = dados_tarefa.get('colaboradores', [])
        if colaboradores_ids:
            colaboradores = User.objects.filter(
                id__in=colaboradores_ids,
                grupos_participando=grupo,
                membrogrupo__ativo=True
            )
            tarefa.colaboradores.set(colaboradores)
        
        # Cria itens do checklist se fornecidos
        checklist_items = dados_tarefa.get('checklist', [])
        for i, item_texto in enumerate(checklist_items):
            if item_texto.strip():
                ChecklistItem.objects.create(
                    tarefa=tarefa,
                    texto=item_texto.strip(),
                    ordem=i
                )
        
        # Cria notificações
        from .notificacao_service import NotificacaoService
        
        # Notifica responsável principal
        if responsavel_principal and responsavel_principal != criador:
            NotificacaoService.criar_notificacao(
                usuario=responsavel_principal,
                grupo=grupo,
                tipo='tarefa_atribuida',
                titulo='Nova tarefa atribuída',
                conteudo=f'Você foi definido como responsável pela tarefa "{tarefa.titulo}"',
                tarefa=tarefa
            )
        
        # Notifica colaboradores
        for colaborador in tarefa.colaboradores.all():
            if colaborador != criador:
                NotificacaoService.criar_notificacao(
                    usuario=colaborador,
                    grupo=grupo,
                    tipo='tarefa_atribuida',
                    titulo='Você foi adicionado como colaborador',
                    conteudo=f'Você foi adicionado como colaborador na tarefa "{tarefa.titulo}"',
                    tarefa=tarefa
                )
        
        return tarefa
    
    @staticmethod
    @transaction.atomic
    def mover_tarefa_kanban(tarefa, nova_coluna, movido_por):
        """
        Move tarefa no Kanban com histórico
        
        Args:
            tarefa (TarefaGrupo): Tarefa a ser movida
            nova_coluna (str): Nova coluna de destino
            movido_por (User): Usuário que está movendo
            
        Returns:
            TarefaGrupo: Tarefa atualizada
        """
        # Verifica permissão
        if not tarefa.grupo.membros.filter(id=movido_por.id, membrogrupo__ativo=True).exists():
            raise PermissionError("Você não é membro deste grupo")
        
        # Valida nova coluna
        colunas_validas = [choice[0] for choice in TarefaGrupo.STATUS_CHOICES]
        if nova_coluna not in colunas_validas:
            raise ValueError(f"Coluna inválida. Deve ser uma de: {colunas_validas}")
        
        # Move a tarefa
        status_anterior = tarefa.status
        tarefa.status = nova_coluna
        tarefa.coluna_kanban = nova_coluna
        
        # Reordena na nova coluna (coloca no final)
        from django.db.models import Max
        max_ordem = TarefaGrupo.objects.filter(
            grupo=tarefa.grupo,
            coluna_kanban=nova_coluna
        ).aggregate(Max('ordem_kanban'))['ordem_kanban__max'] or 0
        
        tarefa.ordem_kanban = max_ordem + 1
        tarefa.save()
        
        # Registra no histórico se houve mudança
        if status_anterior != nova_coluna:
            if not isinstance(tarefa.historico_status, list):
                tarefa.historico_status = []
            
            entrada_historico = {
                'de': status_anterior,
                'para': nova_coluna,
                'data': timezone.now().isoformat(),
                'usuario': movido_por.username if movido_por else 'sistema'
            }
            
            tarefa.historico_status.append(entrada_historico)
            # Salva apenas o histórico para evitar loops
            TarefaGrupo.objects.filter(pk=tarefa.pk).update(historico_status=tarefa.historico_status)
        
        # Cria notificações para interessados
        from .notificacao_service import NotificacaoService
        
        interessados = set()
        if tarefa.responsavel_principal:
            interessados.add(tarefa.responsavel_principal)
        interessados.update(tarefa.colaboradores.all())
        interessados.add(tarefa.criado_por)
        
        # Remove quem moveu da lista de notificações
        interessados.discard(movido_por)
        
        for usuario in interessados:
            NotificacaoService.criar_notificacao(
                usuario=usuario,
                grupo=tarefa.grupo,
                tipo='status_alterado',
                titulo='Status da tarefa alterado',
                conteudo=f'{movido_por.get_full_name() or movido_por.username} moveu a tarefa "{tarefa.titulo}" para "{dict(TarefaGrupo.STATUS_CHOICES)[nova_coluna]}"',
                tarefa=tarefa
            )
        
        return tarefa
    
    @staticmethod
    def atribuir_responsavel(tarefa, novo_responsavel, atribuido_por):
        """
        Atribui responsável com notificação
        
        Args:
            tarefa (TarefaGrupo): Tarefa
            novo_responsavel (User): Novo responsável
            atribuido_por (User): Quem está atribuindo
            
        Returns:
            TarefaGrupo: Tarefa atualizada
        """
        # Verifica permissão
        if not tarefa.grupo.can_manage_tasks(atribuido_por):
            raise PermissionError("Você não tem permissão para atribuir responsáveis")
        
        # Verifica se novo responsável é membro do grupo
        if not tarefa.grupo.membros.filter(id=novo_responsavel.id, membrogrupo__ativo=True).exists():
            raise ValueError("Responsável deve ser membro do grupo")
        
        responsavel_anterior = tarefa.responsavel_principal
        tarefa.responsavel_principal = novo_responsavel
        tarefa.save()
        
        # Cria notificações
        from .notificacao_service import NotificacaoService
        
        # Notifica novo responsável
        if novo_responsavel != atribuido_por:
            NotificacaoService.criar_notificacao(
                usuario=novo_responsavel,
                grupo=tarefa.grupo,
                tipo='tarefa_atribuida',
                titulo='Você foi definido como responsável',
                conteudo=f'{atribuido_por.get_full_name() or atribuido_por.username} definiu você como responsável pela tarefa "{tarefa.titulo}"',
                tarefa=tarefa
            )
        
        # Notifica responsável anterior se houver
        if responsavel_anterior and responsavel_anterior != atribuido_por and responsavel_anterior != novo_responsavel:
            NotificacaoService.criar_notificacao(
                usuario=responsavel_anterior,
                grupo=tarefa.grupo,
                tipo='status_alterado',
                titulo='Responsabilidade da tarefa alterada',
                conteudo=f'A responsabilidade pela tarefa "{tarefa.titulo}" foi transferida para {novo_responsavel.get_full_name() or novo_responsavel.username}',
                tarefa=tarefa
            )
        
        return tarefa
    
    @staticmethod
    def adicionar_comentario(tarefa, autor, texto, mencoes=None):
        """
        Adiciona comentário com processamento de menções
        
        Args:
            tarefa (TarefaGrupo): Tarefa
            autor (User): Autor do comentário
            texto (str): Texto do comentário
            mencoes (list): Lista de usernames mencionados (opcional)
            
        Returns:
            ComentarioTarefa: Comentário criado
        """
        # Verifica se autor é membro do grupo
        if not tarefa.grupo.membros.filter(id=autor.id, membrogrupo__ativo=True).exists():
            raise PermissionError("Você não é membro deste grupo")
        
        # Cria o comentário
        comentario = ComentarioTarefa.objects.create(
            tarefa=tarefa,
            autor=autor,
            texto=texto
        )
        
        # O processamento de menções é feito automaticamente no save() do model
        
        # Notifica interessados sobre novo comentário
        from .notificacao_service import NotificacaoService
        
        interessados = set()
        if tarefa.responsavel_principal:
            interessados.add(tarefa.responsavel_principal)
        interessados.update(tarefa.colaboradores.all())
        interessados.add(tarefa.criado_por)
        
        # Remove o autor do comentário
        interessados.discard(autor)
        
        for usuario in interessados:
            NotificacaoService.criar_notificacao(
                usuario=usuario,
                grupo=tarefa.grupo,
                tipo='comentario',
                titulo='Novo comentário na tarefa',
                conteudo=f'{autor.get_full_name() or autor.username} comentou na tarefa "{tarefa.titulo}": {texto[:50]}...',
                tarefa=tarefa
            )
        
        return comentario
    
    @staticmethod
    def adicionar_anexo(tarefa, arquivo, usuario):
        """
        Adiciona anexo à tarefa
        
        Args:
            tarefa (TarefaGrupo): Tarefa
            arquivo (File): Arquivo a ser anexado
            usuario (User): Usuário que está anexando
            
        Returns:
            AnexoTarefa: Anexo criado
        """
        # Verifica se usuário é membro do grupo
        if not tarefa.grupo.membros.filter(id=usuario.id, membrogrupo__ativo=True).exists():
            raise PermissionError("Você não é membro deste grupo")
        
        # Cria o anexo
        anexo = AnexoTarefa.objects.create(
            tarefa=tarefa,
            arquivo=arquivo,
            nome_original=arquivo.name,
            tipo_arquivo=arquivo.content_type,
            tamanho=arquivo.size,
            upload_por=usuario
        )
        
        return anexo
    
    @staticmethod
    def atualizar_checklist_item(item_id, concluido, usuario):
        """
        Atualiza status de item do checklist
        
        Args:
            item_id (int): ID do item
            concluido (bool): Status de conclusão
            usuario (User): Usuário que está atualizando
            
        Returns:
            ChecklistItem: Item atualizado
        """
        try:
            item = ChecklistItem.objects.get(id=item_id)
        except ChecklistItem.DoesNotExist:
            raise ValueError("Item do checklist não encontrado")
        
        # Verifica se usuário é membro do grupo
        if not item.tarefa.grupo.membros.filter(id=usuario.id, membrogrupo__ativo=True).exists():
            raise PermissionError("Você não é membro deste grupo")
        
        if concluido:
            item.marcar_concluido(usuario)
        else:
            item.desmarcar_concluido()
        
        return item
    
    @staticmethod
    def get_tarefas_kanban(grupo, usuario):
        """
        Retorna tarefas organizadas para visualização Kanban
        
        Args:
            grupo (Grupo): Grupo das tarefas
            usuario (User): Usuário solicitante
            
        Returns:
            dict: Tarefas organizadas por coluna
        """
        # Verifica se usuário é membro do grupo
        if not grupo.membros.filter(id=usuario.id, membrogrupo__ativo=True).exists():
            raise PermissionError("Você não é membro deste grupo")
        
        # Busca tarefas com otimização
        tarefas = TarefaGrupo.objects.filter(grupo=grupo)\
            .select_related('responsavel_principal', 'criado_por')\
            .prefetch_related('colaboradores', 'checklist')\
            .order_by('coluna_kanban', 'ordem_kanban')
        
        # Organiza por coluna
        kanban = {
            'a_fazer': [],
            'em_andamento': [],
            'aguardando_feedback': [],
            'concluido': []
        }
        
        for tarefa in tarefas:
            kanban[tarefa.coluna_kanban].append(tarefa)
        
        return kanban
    
    @staticmethod
    def reordenar_tarefas_coluna(grupo, coluna, ordem_ids, usuario):
        """
        Reordena tarefas dentro de uma coluna
        
        Args:
            grupo (Grupo): Grupo das tarefas
            coluna (str): Coluna a ser reordenada
            ordem_ids (list): Lista de IDs na nova ordem
            usuario (User): Usuário que está reordenando
            
        Returns:
            bool: True se sucesso
        """
        # Verifica permissão
        if not grupo.membros.filter(id=usuario.id, membrogrupo__ativo=True).exists():
            raise PermissionError("Você não é membro deste grupo")
        
        # Atualiza ordem das tarefas
        for i, tarefa_id in enumerate(ordem_ids):
            TarefaGrupo.objects.filter(
                id=tarefa_id,
                grupo=grupo,
                coluna_kanban=coluna
            ).update(ordem_kanban=i)
        
        return True