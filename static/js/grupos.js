/**
 * JavaScript para funcionalidades dos Grupos Colaborativos
 * Inclui Drag & Drop do Kanban, AJAX calls e interações dinâmicas
 */

class GruposManager {
    constructor() {
        this.initEventListeners();
        this.initKanbanDragDrop();
        this.initTooltips();
    }

    initEventListeners() {
        // Form de nova tarefa
        const formNovaTarefa = document.getElementById('formNovaTarefa');
        if (formNovaTarefa) {
            formNovaTarefa.addEventListener('submit', (e) => this.handleNovaTarefa(e));
        }

        // Filtros do Kanban
        const filtroResponsavel = document.getElementById('filtroResponsavel');
        if (filtroResponsavel) {
            filtroResponsavel.addEventListener('change', (e) => this.filtrarTarefas(e.target.value));
        }

        // Botões de ação rápida
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="ver-detalhes"]')) {
                this.verDetalhesTarefa(e.target.dataset.tarefaId);
            }
            if (e.target.matches('[data-action="editar-tarefa"]')) {
                this.editarTarefa(e.target.dataset.tarefaId);
            }
            if (e.target.matches('[data-action="excluir-tarefa"]')) {
                this.excluirTarefa(e.target.dataset.tarefaId);
            }
        });

        // Auto-save em formulários
        this.initAutoSave();
    }

    initKanbanDragDrop() {
        const kanbanBoard = document.getElementById('kanbanBoard');
        if (!kanbanBoard) return;

        // Configurar drag & drop para cards existentes
        this.setupDragDropForCards();
        
        // Configurar drop zones
        this.setupDropZones();
    }

    setupDragDropForCards() {
        const cards = document.querySelectorAll('.kanban-card');
        
        cards.forEach(card => {
            card.draggable = true;
            
            card.addEventListener('dragstart', (e) => {
                card.classList.add('dragging');
                e.dataTransfer.setData('text/plain', card.dataset.tarefaId);
                e.dataTransfer.effectAllowed = 'move';
                
                // Adiciona dados extras para validação
                e.dataTransfer.setData('application/json', JSON.stringify({
                    tarefaId: card.dataset.tarefaId,
                    statusAtual: card.closest('.kanban-column').dataset.status,
                    responsavel: card.dataset.responsavel
                }));
            });
            
            card.addEventListener('dragend', () => {
                card.classList.remove('dragging');
            });

            // Adiciona efeitos visuais
            card.addEventListener('mouseenter', () => {
                if (!card.classList.contains('dragging')) {
                    card.style.transform = 'translateY(-2px)';
                }
            });

            card.addEventListener('mouseleave', () => {
                if (!card.classList.contains('dragging')) {
                    card.style.transform = '';
                }
            });
        });
    }

    setupDropZones() {
        const columns = document.querySelectorAll('.kanban-cards');
        
        columns.forEach(column => {
            column.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                
                // Adiciona indicador visual
                column.classList.add('drag-over');
            });

            column.addEventListener('dragleave', (e) => {
                // Remove indicador apenas se saiu da coluna
                if (!column.contains(e.relatedTarget)) {
                    column.classList.remove('drag-over');
                }
            });
            
            column.addEventListener('drop', (e) => {
                e.preventDefault();
                column.classList.remove('drag-over');
                
                const tarefaId = e.dataTransfer.getData('text/plain');
                const dadosExtra = JSON.parse(e.dataTransfer.getData('application/json') || '{}');
                const novaColuna = column.id.replace('coluna-', '');
                
                // Valida se a movimentação é válida
                if (dadosExtra.statusAtual !== novaColuna) {
                    this.moverTarefa(tarefaId, novaColuna, dadosExtra);
                }
            });
        });
    }

    async moverTarefa(tarefaId, novaColuna, dadosExtra = {}) {
        try {
            // Mostra loading
            this.showLoading(`Movendo tarefa para ${this.getStatusDisplay(novaColuna)}...`);
            
            const response = await fetch(`/grupos/${window.grupoId}/mover-tarefa/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: `tarefa_id=${tarefaId}&nova_coluna=${novaColuna}`
            });

            const data = await response.json();

            if (data.success) {
                // Atualiza interface sem recarregar
                this.atualizarCardNaInterface(tarefaId, novaColuna);
                this.showSuccess('Tarefa movida com sucesso!');
                
                // Atualiza contadores
                this.atualizarContadores();
                
                // Log da ação
                this.logAction('move_task', {
                    tarefaId,
                    de: dadosExtra.statusAtual,
                    para: novaColuna
                });
            } else {
                this.showError('Erro ao mover tarefa: ' + data.error);
                // Reverte a movimentação visual se houver erro
                this.revertMoveVisual(tarefaId, dadosExtra.statusAtual);
            }
        } catch (error) {
            console.error('Erro ao mover tarefa:', error);
            this.showError('Erro de conexão ao mover tarefa');
            this.revertMoveVisual(tarefaId, dadosExtra.statusAtual);
        } finally {
            this.hideLoading();
        }
    }

    atualizarCardNaInterface(tarefaId, novaColuna) {
        const card = document.querySelector(`[data-tarefa-id="${tarefaId}"]`);
        const novaColunaDom = document.getElementById(`coluna-${novaColuna}`);
        
        if (card && novaColunaDom) {
            // Remove da coluna atual
            card.remove();
            
            // Adiciona na nova coluna
            novaColunaDom.appendChild(card);
            
            // Atualiza dados do card
            card.closest('.kanban-column').dataset.status = novaColuna;
            
            // Adiciona animação
            card.style.opacity = '0';
            card.style.transform = 'scale(0.8)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.3s ease';
                card.style.opacity = '1';
                card.style.transform = 'scale(1)';
            }, 100);
        }
    }

    async handleNovaTarefa(e) {
        e.preventDefault();
        
        const form = e.target;
        const formData = new FormData(form);
        
        try {
            this.showLoading('Criando nova tarefa...');
            
            const response = await fetch('/api/tarefas/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.id) {
                this.showSuccess('Tarefa criada com sucesso!');
                
                // Fecha modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('novaTarefaModal'));
                modal.hide();
                
                // Limpa formulário
                form.reset();
                
                // Adiciona tarefa na interface
                this.adicionarTarefaNaInterface(data);
                
                // Log da ação
                this.logAction('create_task', { tarefaId: data.id, titulo: data.titulo });
            } else {
                this.showError('Erro ao criar tarefa: ' + (data.error || 'Erro desconhecido'));
            }
        } catch (error) {
            console.error('Erro ao criar tarefa:', error);
            this.showError('Erro de conexão ao criar tarefa');
        } finally {
            this.hideLoading();
        }
    }

    async verDetalhesTarefa(tarefaId) {
        try {
            this.showLoading('Carregando detalhes...');
            
            const response = await fetch(`/api/tarefas/${tarefaId}/`);
            const data = await response.json();

            if (response.ok) {
                this.mostrarModalDetalhes(data);
            } else {
                this.showError('Erro ao carregar detalhes da tarefa');
            }
        } catch (error) {
            console.error('Erro ao carregar detalhes:', error);
            this.showError('Erro de conexão');
        } finally {
            this.hideLoading();
        }
    }

    mostrarModalDetalhes(tarefa) {
        const modal = document.getElementById('detalheTarefaModal');
        const titulo = document.getElementById('detalheTarefaTitulo');
        const conteudo = document.getElementById('detalheTarefaConteudo');
        
        titulo.textContent = tarefa.titulo;
        
        conteudo.innerHTML = `
            <div class="row">
                <div class="col-md-8">
                    <h6>Descrição</h6>
                    <p class="text-muted">${tarefa.descricao || 'Sem descrição'}</p>
                    
                    <h6>Status e Prioridade</h6>
                    <div class="d-flex gap-2 mb-3">
                        <span class="badge bg-primary">${tarefa.status_display}</span>
                        <span class="badge prioridade-${tarefa.prioridade}">${tarefa.prioridade_display}</span>
                    </div>
                    
                    ${tarefa.checklist && tarefa.checklist.length > 0 ? `
                        <h6>Checklist (${tarefa.progresso_checklist}%)</h6>
                        <div class="progress mb-2">
                            <div class="progress-bar" style="width: ${tarefa.progresso_checklist}%"></div>
                        </div>
                        <ul class="list-unstyled">
                            ${tarefa.checklist.map(item => `
                                <li>
                                    <i class="fas fa-${item.concluido ? 'check-square text-success' : 'square text-muted'}"></i>
                                    ${item.texto}
                                </li>
                            `).join('')}
                        </ul>
                    ` : ''}
                </div>
                
                <div class="col-md-4">
                    <h6>Informações</h6>
                    <ul class="list-unstyled">
                        ${tarefa.responsavel_nome ? `<li><strong>Responsável:</strong> ${tarefa.responsavel_nome}</li>` : ''}
                        ${tarefa.prazo ? `<li><strong>Prazo:</strong> ${new Date(tarefa.prazo).toLocaleString()}</li>` : ''}
                        <li><strong>Criado por:</strong> ${tarefa.criado_por_nome}</li>
                        <li><strong>Criado em:</strong> ${new Date(tarefa.criado_em).toLocaleString()}</li>
                        ${tarefa.colaboradores_nomes && tarefa.colaboradores_nomes.length > 0 ? `
                            <li><strong>Colaboradores:</strong> ${tarefa.colaboradores_nomes.join(', ')}</li>
                        ` : ''}
                    </ul>
                    
                    ${tarefa.anexos && tarefa.anexos.length > 0 ? `
                        <h6>Anexos</h6>
                        <ul class="list-unstyled">
                            ${tarefa.anexos.map(anexo => `
                                <li>
                                    <a href="${anexo.arquivo}" target="_blank">
                                        <i class="fas fa-paperclip"></i> ${anexo.nome_original}
                                    </a>
                                    <small class="text-muted d-block">${anexo.tamanho_formatado}</small>
                                </li>
                            `).join('')}
                        </ul>
                    ` : ''}
                </div>
            </div>
            
            ${tarefa.comentarios && tarefa.comentarios.length > 0 ? `
                <hr>
                <h6>Comentários</h6>
                <div class="comentarios-list">
                    ${tarefa.comentarios.map(comentario => `
                        <div class="comentario mb-3">
                            <div class="d-flex justify-content-between">
                                <strong>${comentario.autor_nome}</strong>
                                <small class="text-muted">${new Date(comentario.criado_em).toLocaleString()}</small>
                            </div>
                            <p class="mb-1">${comentario.texto}</p>
                            ${comentario.mencoes_usernames && comentario.mencoes_usernames.length > 0 ? `
                                <small class="text-info">Mencionou: ${comentario.mencoes_usernames.join(', ')}</small>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        `;
        
        new bootstrap.Modal(modal).show();
    }

    filtrarTarefas(filtro) {
        const cards = document.querySelectorAll('.kanban-card');
        
        cards.forEach(card => {
            const responsavel = card.dataset.responsavel;
            
            if (filtro === 'todos' || filtro === '' || responsavel === filtro) {
                card.style.display = 'block';
                card.style.opacity = '1';
            } else {
                card.style.display = 'none';
                card.style.opacity = '0.5';
            }
        });
        
        // Atualiza contadores
        this.atualizarContadores();
    }

    atualizarContadores() {
        const colunas = document.querySelectorAll('.kanban-column');
        
        colunas.forEach(coluna => {
            const cardsVisiveis = coluna.querySelectorAll('.kanban-card:not([style*="display: none"])');
            const badge = coluna.querySelector('.badge');
            
            if (badge) {
                badge.textContent = cardsVisiveis.length;
            }
        });
    }

    // Utilitários
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    }

    getStatusDisplay(status) {
        const displays = {
            'a_fazer': 'A Fazer',
            'em_andamento': 'Em Andamento',
            'aguardando_feedback': 'Aguardando Feedback',
            'concluido': 'Concluído'
        };
        return displays[status] || status;
    }

    showLoading(message = 'Carregando...') {
        // Remove loading anterior se existir
        this.hideLoading();
        
        const loading = document.createElement('div');
        loading.id = 'loading-overlay';
        loading.className = 'loading-overlay';
        loading.innerHTML = `
            <div class="loading-content">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="mt-2">${message}</div>
            </div>
        `;
        
        document.body.appendChild(loading);
    }

    hideLoading() {
        const loading = document.getElementById('loading-overlay');
        if (loading) {
            loading.remove();
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        // Adiciona ao container de toasts ou cria um
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(container);
        }
        
        container.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove do DOM após esconder
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    initTooltips() {
        // Inicializa tooltips do Bootstrap
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    initAutoSave() {
        // Auto-save para formulários longos
        const forms = document.querySelectorAll('[data-autosave]');
        
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input, textarea, select');
            
            inputs.forEach(input => {
                input.addEventListener('input', debounce(() => {
                    this.autoSaveForm(form);
                }, 2000));
            });
        });
    }

    autoSaveForm(form) {
        const formData = new FormData(form);
        const autoSaveKey = `autosave_${form.id || 'form'}`;
        
        // Salva no localStorage
        const data = {};
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        localStorage.setItem(autoSaveKey, JSON.stringify(data));
        
        // Mostra indicador de salvamento
        this.showAutoSaveIndicator();
    }

    showAutoSaveIndicator() {
        const indicator = document.getElementById('autosave-indicator') || document.createElement('div');
        indicator.id = 'autosave-indicator';
        indicator.className = 'autosave-indicator';
        indicator.innerHTML = '<i class="fas fa-save"></i> Rascunho salvo';
        
        if (!document.getElementById('autosave-indicator')) {
            document.body.appendChild(indicator);
        }
        
        indicator.style.display = 'block';
        
        setTimeout(() => {
            indicator.style.display = 'none';
        }, 2000);
    }

    logAction(action, data = {}) {
        // Log de ações para analytics/debug
        console.log(`[Grupos] ${action}:`, data);
        
        // Aqui você pode enviar para um serviço de analytics
        if (window.gtag) {
            gtag('event', action, {
                event_category: 'grupos',
                ...data
            });
        }
    }
}

// Utilitário debounce
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Inicializa quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.gruposManager = new GruposManager();
});

// Exporta para uso global
window.GruposManager = GruposManager;