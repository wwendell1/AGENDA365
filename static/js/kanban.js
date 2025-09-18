document.addEventListener('DOMContentLoaded', function() {
    // Inicializa o Sortable em cada coluna
    document.querySelectorAll('.cartoes-container').forEach(function(container) {
        new Sortable(container, {
            group: 'cartoes', // Permite arrastar entre colunas
            animation: 150,
            ghostClass: 'cartao-ghost', // Classe para o elemento fantasma durante o arrasto
            chosenClass: 'cartao-chosen', // Classe para o elemento escolhido
            dragClass: 'cartao-drag', // Classe durante o arrasto
            
            onEnd: function(evt) {
                const cartaoId = evt.item.dataset.id;
                const novaColuna = evt.to.closest('.kanban-coluna').dataset.nome;
                const novaOrdem = Array.from(evt.to.children).indexOf(evt.item);
                
                // Envia a atualização para o servidor
                fetch(`/api/cartao-kanban/${cartaoId}/mover/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        coluna: novaColuna,
                        ordem: novaOrdem
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        // Se houver erro, reverte a movimentação
                        evt.from.appendChild(evt.item);
                        alert('Erro ao mover o cartão: ' + data.error);
                    }
                    // Atualiza os contadores das colunas
                    atualizarContadores();
                })
                .catch(error => {
                    console.error('Erro:', error);
                    evt.from.appendChild(evt.item);
                    alert('Erro ao comunicar com o servidor');
                });
            }
        });
    });
    
    // Função para obter o token CSRF
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Função para atualizar os contadores de cartões em cada coluna
    function atualizarContadores() {
        document.querySelectorAll('.kanban-coluna').forEach(coluna => {
            const contador = coluna.querySelector('.kanban-coluna-contador');
            const numCartoes = coluna.querySelectorAll('.cartao').length;
            contador.textContent = numCartoes;
        });
    }
    
    // Inicializa os contadores
    atualizarContadores();
    
    // Manipula o formulário de novo cartão
    const formNovoCartao = document.getElementById('novoCartaoForm');
    const btnSalvarCartao = document.getElementById('salvarCartao');
    
    btnSalvarCartao.addEventListener('click', function() {
        const formData = new FormData(formNovoCartao);
        const data = {
            titulo: formData.get('titulo'),
            descricao: formData.get('descricao'),
            grupo_id: formData.get('grupo_id'),
            responsaveis: Array.from(formData.getAll('responsaveis')),
            prioridade: formData.get('prioridade'),
            data_limite: formData.get('data_limite')
        };
        
        fetch('/api/cartao-kanban/criar/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Cria o novo cartão e adiciona à coluna "A Fazer"
                const colunaAFazer = document.querySelector('.kanban-coluna[data-nome="A Fazer"] .cartoes-container');
                const novoCartao = criarCartao(data.cartao);
                colunaAFazer.appendChild(novoCartao);
                
                // Fecha o modal e limpa o formulário
                const modal = bootstrap.Modal.getInstance(document.getElementById('novoCartaoModal'));
                modal.hide();
                formNovoCartao.reset();
                
                // Atualiza os contadores
                atualizarContadores();
            } else {
                alert('Erro ao criar cartão: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao comunicar com o servidor');
        });
    });
    
    // Função para criar um novo elemento de cartão
    function criarCartao(cartao) {
        const div = document.createElement('div');
        div.className = 'cartao';
        div.dataset.id = cartao.id;
        
        div.innerHTML = `
            <h3 class="cartao-titulo">${cartao.titulo}</h3>
            <div class="cartao-responsaveis">
                ${cartao.responsaveis.map(resp => `
                    <span class="responsavel-tag">${resp.nome}</span>
                `).join('')}
            </div>
            <div class="cartao-prioridade prioridade-${cartao.prioridade}">
                ${cartao.prioridade}
            </div>
            ${cartao.data_limite ? `
                <div class="cartao-data-limite">
                    Prazo: ${new Date(cartao.data_limite).toLocaleDateString()}
                </div>
            ` : ''}
        `;
        
        return div;
    }
});