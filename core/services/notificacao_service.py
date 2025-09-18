from django.contrib.auth.models import User
from django.utils import timezone
from core.models import NotificacaoGrupo, TarefaGrupo, Grupo

class NotificacaoService:
    
    @staticmethod
    def criar_notificacao(usuario, grupo, tipo, titulo, conteudo, tarefa=None):
        """
        Cria uma nova notificação
        
        Args:
            usuario (User): Usuário que receberá a notificação
            grupo (Grupo): Grupo relacionado
            tipo (str): Tipo da notificação
            titulo (str): Título da notificação
            conteudo (str): Conteúdo da notificação
            tarefa (TarefaGrupo, optional): Tarefa relacionada
            
        Returns:
            NotificacaoGrupo: Notificação criada
        """
        notificacao = NotificacaoGrupo.objects.create(
            usuario=usuario,
            grupo=grupo,
            tipo=tipo,
            titulo=titulo,
            conteudo=conteudo,
            tarefa=tarefa
        )
        
        return notificacao
    
    @staticmethod
    def enviar_notificacao_atribuicao(tarefa, usuario_atribuido, atribuido_por):
        """
        Envia notificação quando tarefa é atribuída
        
        Args:
            tarefa (TarefaGrupo): Tarefa atribuída
            usuario_atribuido (User): Usuário que recebeu a tarefa
            atribuido_por (User): Usuário que fez a atribuição
        """
        if usuario_atribuido != atribuido_por:
            NotificacaoService.criar_notificacao(
                usuario=usuario_atribuido,
                grupo=tarefa.grupo,
                tipo='tarefa_atribuida',
                titulo='Nova tarefa atribuída',
                conteudo=f'{atribuido_por.get_full_name() or atribuido_por.username} atribuiu a tarefa "{tarefa.titulo}" para você',
                tarefa=tarefa
            )
    
    @staticmethod
    def verificar_prazos_proximos():
        """
        Verifica tarefas com prazo próximo (24 horas) e cria notificações
        
        Returns:
            int: Número de notificações criadas
        """
        from datetime import timedelta
        
        # Calcula o range de 24 horas
        agora = timezone.now()
        limite_24h = agora + timedelta(hours=24)
        
        # Busca tarefas com prazo nas próximas 24 horas
        tarefas_proximas = TarefaGrupo.objects.filter(
            prazo__gte=agora,
            prazo__lte=limite_24h,
            status__in=['a_fazer', 'em_andamento', 'aguardando_feedback']
        ).select_related('responsavel_principal', 'grupo')
        
        notificacoes_criadas = 0
        
        for tarefa in tarefas_proximas:
            # Verifica se já foi enviada notificação de prazo próximo hoje
            ja_notificado = NotificacaoGrupo.objects.filter(
                tarefa=tarefa,
                tipo='prazo_proximo',
                criado_em__date=agora.date()
            ).exists()
            
            if not ja_notificado:
                # Notifica responsável principal
                if tarefa.responsavel_principal:
                    NotificacaoService.criar_notificacao(
                        usuario=tarefa.responsavel_principal,
                        grupo=tarefa.grupo,
                        tipo='prazo_proximo',
                        titulo='Prazo da tarefa se aproxima',
                        conteudo=f'A tarefa "{tarefa.titulo}" vence em menos de 24 horas ({tarefa.prazo.strftime("%d/%m/%Y às %H:%M")})',
                        tarefa=tarefa
                    )
                    notificacoes_criadas += 1
                
                # Notifica colaboradores
                for colaborador in tarefa.colaboradores.all():
                    NotificacaoService.criar_notificacao(
                        usuario=colaborador,
                        grupo=tarefa.grupo,
                        tipo='prazo_proximo',
                        titulo='Prazo da tarefa se aproxima',
                        conteudo=f'A tarefa "{tarefa.titulo}" (onde você é colaborador) vence em menos de 24 horas ({tarefa.prazo.strftime("%d/%m/%Y às %H:%M")})',
                        tarefa=tarefa
                    )
                    notificacoes_criadas += 1
        
        return notificacoes_criadas
    
    @staticmethod
    def notificar_prazo_vencido():
        """
        Notifica sobre tarefas com prazo vencido
        
        Returns:
            int: Número de notificações criadas
        """
        agora = timezone.now()
        
        # Busca tarefas vencidas
        tarefas_vencidas = TarefaGrupo.objects.filter(
            prazo__lt=agora,
            status__in=['a_fazer', 'em_andamento', 'aguardando_feedback']
        ).select_related('responsavel_principal', 'grupo')
        
        notificacoes_criadas = 0
        
        for tarefa in tarefas_vencidas:
            # Verifica se já foi enviada notificação de vencimento hoje
            ja_notificado = NotificacaoGrupo.objects.filter(
                tarefa=tarefa,
                tipo='prazo_vencido',
                criado_em__date=agora.date()
            ).exists()
            
            if not ja_notificado:
                # Calcula há quantos dias está vencida
                dias_vencida = (agora.date() - tarefa.prazo.date()).days
                
                # Notifica responsável principal
                if tarefa.responsavel_principal:
                    NotificacaoService.criar_notificacao(
                        usuario=tarefa.responsavel_principal,
                        grupo=tarefa.grupo,
                        tipo='prazo_vencido',
                        titulo='Tarefa com prazo vencido',
                        conteudo=f'A tarefa "{tarefa.titulo}" está vencida há {dias_vencida} dia(s) (prazo era {tarefa.prazo.strftime("%d/%m/%Y às %H:%M")})',
                        tarefa=tarefa
                    )
                    notificacoes_criadas += 1
                
                # Notifica colaboradores
                for colaborador in tarefa.colaboradores.all():
                    NotificacaoService.criar_notificacao(
                        usuario=colaborador,
                        grupo=tarefa.grupo,
                        tipo='prazo_vencido',
                        titulo='Tarefa com prazo vencido',
                        conteudo=f'A tarefa "{tarefa.titulo}" (onde você é colaborador) está vencida há {dias_vencida} dia(s)',
                        tarefa=tarefa
                    )
                    notificacoes_criadas += 1
        
        return notificacoes_criadas
    
    @staticmethod
    def processar_notificacoes_continuas():
        """
        Processa notificações contínuas para tarefas vencidas
        Envia lembretes periódicos para tarefas muito atrasadas
        
        Returns:
            int: Número de notificações criadas
        """
        from datetime import timedelta
        
        agora = timezone.now()
        
        # Busca tarefas vencidas há mais de 3 dias
        limite_continua = agora - timedelta(days=3)
        
        tarefas_muito_atrasadas = TarefaGrupo.objects.filter(
            prazo__lt=limite_continua,
            status__in=['a_fazer', 'em_andamento', 'aguardando_feedback']
        ).select_related('responsavel_principal', 'grupo')
        
        notificacoes_criadas = 0
        
        for tarefa in tarefas_muito_atrasadas:
            # Verifica se já foi enviada notificação contínua esta semana
            inicio_semana = agora - timedelta(days=7)
            ja_notificado_semana = NotificacaoGrupo.objects.filter(
                tarefa=tarefa,
                tipo='prazo_vencido',
                criado_em__gte=inicio_semana
            ).exists()
            
            if not ja_notificado_semana:
                dias_vencida = (agora.date() - tarefa.prazo.date()).days
                
                # Notifica apenas o responsável principal para evitar spam
                if tarefa.responsavel_principal:
                    NotificacaoService.criar_notificacao(
                        usuario=tarefa.responsavel_principal,
                        grupo=tarefa.grupo,
                        tipo='prazo_vencido',
                        titulo='Lembrete: Tarefa muito atrasada',
                        conteudo=f'A tarefa "{tarefa.titulo}" está vencida há {dias_vencida} dias. Por favor, atualize o status ou prazo.',
                        tarefa=tarefa
                    )
                    notificacoes_criadas += 1
        
        return notificacoes_criadas
    
    @staticmethod
    def marcar_notificacoes_como_lidas(usuario, grupo=None, tarefa=None):
        """
        Marca notificações como lidas
        
        Args:
            usuario (User): Usuário das notificações
            grupo (Grupo, optional): Filtrar por grupo específico
            tarefa (TarefaGrupo, optional): Filtrar por tarefa específica
            
        Returns:
            int: Número de notificações marcadas como lidas
        """
        queryset = NotificacaoGrupo.objects.filter(
            usuario=usuario,
            lida=False
        )
        
        if grupo:
            queryset = queryset.filter(grupo=grupo)
        
        if tarefa:
            queryset = queryset.filter(tarefa=tarefa)
        
        count = queryset.count()
        queryset.update(lida=True, lida_em=timezone.now())
        
        return count
    
    @staticmethod
    def get_notificacoes_nao_lidas(usuario, limite=10):
        """
        Retorna notificações não lidas do usuário
        
        Args:
            usuario (User): Usuário
            limite (int): Limite de notificações a retornar
            
        Returns:
            QuerySet: Notificações não lidas
        """
        return NotificacaoGrupo.objects.filter(
            usuario=usuario,
            lida=False
        ).select_related('grupo', 'tarefa').order_by('-criado_em')[:limite]
    
    @staticmethod
    def limpar_notificacoes_antigas(dias=30):
        """
        Remove notificações antigas para manter a base limpa
        
        Args:
            dias (int): Número de dias para manter notificações
            
        Returns:
            int: Número de notificações removidas
        """
        from datetime import timedelta
        
        limite = timezone.now() - timedelta(days=dias)
        
        # Remove apenas notificações lidas e antigas
        count, _ = NotificacaoGrupo.objects.filter(
            lida=True,
            criado_em__lt=limite
        ).delete()
        
        return count