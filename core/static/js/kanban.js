document.addEventListener('DOMContentLoaded', function() {
    // Inicializa o Sortable em todas as colunas
    const colunas = document.querySelectorAll('.kanban-cards');
    colunas.forEach(coluna => {
        new Sortable(coluna, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'blue-background-class',
            onEnd: function(evt) {
                const cartaoId = evt.item.dataset.id;
                const colunaDestino = evt.to.dataset.coluna;
                atualizarPosicaoCartao(cartaoId, colunaDestino);
            }
        });
    });

    // Atualiza a posição do cartão no servidor
    function atualizarPosicaoCartao(cartaoId, novaColuna) {
        fetch(`/api/cartao-kanban/${cartaoId}/mover/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                coluna: novaColuna
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                atualizarContadores();
                // Adiciona registro ao histórico
                const historicoHtml = `
                    <div class="historico-item">
                        <span class="timestamp">${new Date().toLocaleString()}</span>
                        <span class="acao">Cartão movido para ${novaColuna}</span>
                    </div>
                `;
                document.querySelector('.historico-lista').insertAdjacentHTML('afterbegin', historicoHtml);
            } else {
                alert('Erro ao mover o cartão. Por favor, tente novamente.');
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao mover o cartão. Por favor, tente novamente.');
        });
    }

    // Atualiza os contadores de cartões em cada coluna
    function atualizarContadores() {
        colunas.forEach(coluna => {
            const contador = coluna.closest('.kanban-column').querySelector('.kanban-column-count');
            contador.textContent = coluna.children.length;
        });
    }

    // Função para criar novo cartão
    document.getElementById('salvarCartao')?.addEventListener('click', function() {
        const form = document.getElementById('novoCartaoForm');
        const formData = new FormData(form);

        fetch('/api/cartao-kanban/criar/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Adiciona o novo cartão à coluna "A Fazer"
                const novoCartaoHtml = criarCartaoHtml(data.cartao);
                document.querySelector('[data-coluna="a_fazer"] .kanban-cards')
                    .insertAdjacentHTML('beforeend', novoCartaoHtml);
                
                // Fecha o modal e limpa o formulário
                const modal = bootstrap.Modal.getInstance(document.getElementById('novoCartaoModal'));
                modal.hide();
                form.reset();
                
                atualizarContadores();
            } else {
                alert('Erro ao criar o cartão. Por favor, tente novamente.');
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao criar o cartão. Por favor, tente novamente.');
        });
    });

    // Função auxiliar para criar o HTML do cartão
    function criarCartaoHtml(cartao) {
        return `
            <div class="kanban-card" data-id="${cartao.id}">
                <div class="kanban-card-title">${cartao.titulo}</div>
                <div class="kanban-card-meta">
                    <div>Responsável: ${cartao.responsavel}</div>
                    ${cartao.data_entrega ? `<div>Entrega: ${cartao.data_entrega}</div>` : ''}
                </div>
            </div>
        `;
    }

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

    // Inicializa os contadores
    atualizarContadores();
});

document.addEventListener('DOMContentLoaded', function() {
    const colunas = document.querySelectorAll('.kanban-coluna');
    
    // Inicializa o Sortable.js para cada coluna do Kanban
    colunas.forEach(coluna => {
        new Sortable(coluna.querySelector('.cartoes-container'), {
            group: 'cartoes',
            animation: 150,
            ghostClass: 'cartao-ghost',
            chosenClass: 'cartao-chosen',
            dragClass: 'cartao-drag',
            onEnd: function(evt) {
                const cartao = evt.item;
                const cartaoId = cartao.getAttribute('data-id');
                const novaColuna = evt.to.closest('.kanban-coluna');
                const novaColunaNome = novaColuna.getAttribute('data-nome');
                const cartoes = Array.from(novaColuna.querySelectorAll('.cartao'));
                const novaOrdem = cartoes.indexOf(cartao);
                
                // Envia a requisição para atualizar a posição do cartão
                fetch(`/api/cartao-kanban/${cartaoId}/mover/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({
                        coluna: novaColunaNome,
                        ordem: novaOrdem,
                        comentario: `Cartão movido para ${novaColunaNome}`
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        // Reverte a movimentação em caso de erro
                        evt.from.appendChild(cartao);
                        mostrarErro('Erro ao mover cartão: ' + data.error);
                    }
                    atualizarContadores();
                })
                .catch(error => {
                    console.error('Erro:', error);
                    // Reverte a movimentação em caso de erro
                    evt.from.appendChild(cartao);
                    mostrarErro('Erro ao mover cartão');
                });
            }
        });
    });

    // Função para atualizar os contadores de cartões em cada coluna
    function atualizarContadores() {
        colunas.forEach(coluna => {
            const contador = coluna.querySelector('.kanban-coluna-contador');
            const cartoes = coluna.querySelectorAll('.cartao');
            contador.textContent = cartoes.length;
        });
    }

    // Inicializa o formulário de novo cartão
    document.getElementById('salvarCartao')?.addEventListener('click', function() {
        const form = document.getElementById('novoCartaoForm');
        const formData = new FormData(form);
        const dados = {
            titulo: formData.get('titulo'),
            descricao: formData.get('descricao'),
            responsaveis: Array.from(form.querySelector('#responsaveis').selectedOptions).map(opt => opt.value),
            prioridade: formData.get('prioridade'),
            data_limite: formData.get('data_limite')
        };

        fetch('/api/cartao-kanban/criar/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(dados)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Adiciona o novo cartão à coluna "A Fazer"
                const coluna = document.querySelector('.kanban-coluna[data-nome="A Fazer"] .cartoes-container');
                const cartao = criarElementoCartao(data.cartao);
                coluna.appendChild(cartao);
                
                // Fecha o modal e limpa o formulário
                const modal = bootstrap.Modal.getInstance(document.getElementById('novoCartaoModal'));
                modal.hide();
                form.reset();
                
                atualizarContadores();
            } else {
                mostrarErro('Erro ao criar cartão: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            mostrarErro('Erro ao criar cartão');
        });
    });
});

// Função para obter o token CSRF do cookie
function getCsrfToken() {
    const name = 'csrftoken';
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

// Função para mostrar mensagens de erro
function mostrarErro(mensagem) {
    const toast = document.createElement('div');
    toast.className = 'toast toast-erro';
    toast.textContent = mensagem;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Função para criar o elemento HTML do cartão
function criarElementoCartao(dados) {
    const cartao = document.createElement('div');
    cartao.className = 'cartao';
    cartao.setAttribute('data-id', dados.id);
    
    const titulo = document.createElement('h3');
    titulo.className = 'cartao-titulo';
    titulo.textContent = dados.titulo;
    
    const responsaveis = document.createElement('div');
    responsaveis.className = 'cartao-responsaveis';
    dados.responsaveis.forEach(resp => {
        const span = document.createElement('span');
        span.className = 'responsavel-tag';
        span.textContent = resp.nome || resp.username;
        responsaveis.appendChild(span);
    });
    
    const prioridade = document.createElement('div');
    prioridade.className = `cartao-prioridade prioridade-${dados.prioridade}`;
    prioridade.textContent = dados.prioridade.charAt(0).toUpperCase() + dados.prioridade.slice(1);
    
    cartao.appendChild(titulo);
    cartao.appendChild(responsaveis);
    cartao.appendChild(prioridade);
    
    if (dados.data_limite) {
        const dataLimite = document.createElement('div');
        dataLimite.className = 'cartao-data-limite';
        dataLimite.textContent = `Prazo: ${new Date(dados.data_limite).toLocaleDateString()}`;
        cartao.appendChild(dataLimite);
    }
    
    return cartao;
}