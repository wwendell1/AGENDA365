from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from ..models import (
    Grupo, 
    MensagemChat, 
    ArquivoGrupo, 
    ConfiguracaoGrupo, 
    MembroGrupo
)
from ..forms import (
    MensagemChatForm, 
    ArquivoGrupoForm, 
    ConfiguracaoGrupoForm
)
from ..permissions import (
    membro_grupo_required,
    moderador_grupo_required
)

@login_required
@membro_grupo_required
def chat_grupo(request, grupo_id):
    """
    Visualização do chat do grupo
    """
    grupo = get_object_or_404(Grupo, pk=grupo_id)
    
    # Verifica configurações de chat
    try:
        configuracao = grupo.configuracoes
        if not configuracao.habilitar_chat:
            messages.warning(request, 'O chat deste grupo está desativado.')
            return redirect('detalhes_grupo', grupo_id=grupo.pk)
    except ConfiguracaoGrupo.DoesNotExist:
        # Cria configurações padrão se não existirem
        configuracao = ConfiguracaoGrupo.objects.create(grupo=grupo)

    # Verifica permissão do usuário
    try:
        membro = MembroGrupo.objects.get(user=request.user, grupo=grupo)
    except MembroGrupo.DoesNotExist:
        messages.error(request, 'Você não tem permissão para acessar este chat.')
        return redirect('listar_grupos')

    # Processamento de nova mensagem
    if request.method == 'POST':
        form = MensagemChatForm(request.POST, grupo=grupo)
        if form.is_valid():
            mensagem = form.save(commit=False)
            mensagem.grupo = grupo
            mensagem.remetente = request.user
            mensagem.save()

            # Salva menções
            if form.cleaned_data.get('mencoes'):
                mensagem.mencoes.set(form.cleaned_data['mencoes'])

            messages.success(request, 'Mensagem enviada com sucesso!')
            return redirect('chat_grupo', grupo_id=grupo.pk)
    else:
        form = MensagemChatForm(grupo=grupo)

    # Busca mensagens com paginação
    mensagens_list = MensagemChat.objects.filter(
        grupo=grupo, 
        resposta_de__isnull=True
    ).order_by('-data_envio')

    paginator = Paginator(mensagens_list, 20)  # 20 mensagens por página
    page = request.GET.get('page')

    try:
        mensagens = paginator.page(page)
    except PageNotAnInteger:
        mensagens = paginator.page(1)
    except EmptyPage:
        mensagens = paginator.page(paginator.num_pages)

    context = {
        'grupo': grupo,
        'mensagens': mensagens,
        'form': form,
        'user_role': membro.role
    }

    return render(request, 'core/grupos/subtabs/chat.html', context)

@login_required
@membro_grupo_required
def arquivos_grupo(request, grupo_id):
    """
    Visualização e upload de arquivos do grupo
    """
    grupo = get_object_or_404(Grupo, pk=grupo_id)
    
    # Verifica permissão do usuário
    try:
        membro = MembroGrupo.objects.get(user=request.user, grupo=grupo)
    except MembroGrupo.DoesNotExist:
        messages.error(request, 'Você não tem permissão para acessar os arquivos.')
        return redirect('listar_grupos')

    # Upload de arquivo
    if request.method == 'POST' and membro.role in ['admin', 'moderador']:
        form = ArquivoGrupoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.save(commit=False)
            arquivo.grupo = grupo
            arquivo.enviado_por = request.user
            
            # Define o nome do arquivo se não for fornecido
            if not arquivo.nome:
                arquivo.nome = arquivo.arquivo.name
            
            arquivo.save()
            messages.success(request, 'Arquivo enviado com sucesso!')
            return redirect('arquivos_grupo', grupo_id=grupo.pk)
    else:
        form = ArquivoGrupoForm()

    # Busca arquivos com filtro e paginação
    filtro = request.GET.get('filtro', '')
    arquivos_list = ArquivoGrupo.objects.filter(grupo=grupo)
    
    if filtro:
        arquivos_list = arquivos_list.filter(
            Q(nome__icontains=filtro) | 
            Q(descricao__icontains=filtro)
        )

    paginator = Paginator(arquivos_list, 15)  # 15 arquivos por página
    page = request.GET.get('page')

    try:
        arquivos = paginator.page(page)
    except PageNotAnInteger:
        arquivos = paginator.page(1)
    except EmptyPage:
        arquivos = paginator.page(paginator.num_pages)

    context = {
        'grupo': grupo,
        'arquivos': arquivos,
        'form': form,
        'filtro': filtro,
        'user_role': membro.role
    }

    return render(request, 'core/grupos/subtabs/arquivos.html', context)

@login_required
@moderador_grupo_required
def configuracoes_grupo(request, grupo_id):
    """
    Configurações do grupo (apenas para administradores e moderadores)
    """
    grupo = get_object_or_404(Grupo, pk=grupo_id)
    
    # Obtém ou cria configurações do grupo
    configuracao, criada = ConfiguracaoGrupo.objects.get_or_create(grupo=grupo)

    # Verifica permissão do usuário
    try:
        membro = MembroGrupo.objects.get(user=request.user, grupo=grupo)
        if membro.role not in ['admin', 'moderador']:
            messages.error(request, 'Você não tem permissão para alterar configurações.')
            return redirect('detalhes_grupo', grupo_id=grupo.pk)
    except MembroGrupo.DoesNotExist:
        messages.error(request, 'Você não é membro deste grupo.')
        return redirect('listar_grupos')

    # Processamento do formulário de configurações
    if request.method == 'POST':
        form = ConfiguracaoGrupoForm(request.POST, instance=configuracao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações atualizadas com sucesso!')
            return redirect('configuracoes_grupo', grupo_id=grupo.pk)
    else:
        form = ConfiguracaoGrupoForm(instance=configuracao)

    context = {
        'grupo': grupo,
        'form': form,
        'user_role': membro.role
    }

    return render(request, 'core/grupos/subtabs/configuracoes.html', context)