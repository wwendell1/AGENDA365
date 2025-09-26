document.addEventListener('DOMContentLoaded', () => {
    // Fechar notificações
    const notifications = document.querySelectorAll('.notification .delete');
    notifications.forEach(btn => {
        btn.addEventListener('click', () => {
            btn.parentNode.remove();
        });
    });

    // Toggle do menu mobile
    const navbarBurger = document.querySelector('.navbar-burger');
    const navbarMenu = document.querySelector('.navbar-menu');
    
    if (navbarBurger) {
        navbarBurger.addEventListener('click', () => {
            navbarBurger.classList.toggle('is-active');
            navbarMenu.classList.toggle('is-active');
        });
    }

    // Mostrar/ocultar senha
    const passwordToggles = document.querySelectorAll('.password-toggle');
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const input = toggle.previousElementSibling;
            const icon = toggle.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });

    // Atualização de status de tarefas via checkbox
    const taskCheckboxes = document.querySelectorAll('.task-checkbox');
    taskCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const taskId = this.getAttribute('data-task-id');
            const currentStatus = this.getAttribute('data-task-status');
            const isChecked = this.checked;
            const taskCard = this.closest('.card');
            const taskTitle = taskCard.querySelector('.task-title');
            
            // Log de depuração
            console.log('Checkbox clicado:', {
                taskId: taskId,
                currentStatus: currentStatus,
                isChecked: isChecked,
                taskTitle: taskTitle ? taskTitle.textContent : 'Título não encontrado'
            });
            
            // Determinar o novo status baseado no checkbox
            const novoStatus = isChecked ? 'concluido' : 'a_fazer';
            
            console.log('Enviando requisição de atualização de status:', {
                url: `/tarefas/atualizar_status_tarefa_grupo/${taskId}/`,
                method: 'POST',
                body: JSON.stringify({
                    status: novoStatus
                })
            });
            
            fetch(`/tarefas/atualizar_status_tarefa_grupo/${taskId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    status: novoStatus
                })
            })
            .then(response => {
                // Log de depuração para resposta
                console.log('Resposta do servidor:', {
                    status: response.status,
                    statusText: response.statusText,
                    headers: Object.fromEntries(response.headers.entries())
                });
                
                // Verificar se a resposta foi bem-sucedida
                if (!response.ok) {
                    // Tentar obter o texto de erro
                    return response.text().then(errorText => {
                        console.error('Erro de resposta:', errorText);
                        throw new Error(`Erro HTTP: ${response.status} - ${errorText}`);
                    });
                }
                
                return response.json();
            })
            .then(data => {
                // Log de depuração para dados
                console.log('Dados recebidos:', data);
                
                if (data.success) {
                    // Atualizar visualmente o título da tarefa
                    if (isChecked) {
                        taskTitle.classList.add('has-text-grey-light');
                        taskCard.classList.add('has-background-success-light');
                        this.setAttribute('data-task-status', 'concluido');
                    } else {
                        taskTitle.classList.remove('has-text-grey-light');
                        taskCard.classList.remove('has-background-success-light');
                        this.setAttribute('data-task-status', 'a_fazer');
                    }
                    
                    // Adicionar feedback visual de sucesso
                    const successBadge = document.createElement('span');
                    successBadge.classList.add('tag', 'is-success', 'ml-2');
                    successBadge.textContent = 'Status atualizado';
                    taskCard.querySelector('.level-left').appendChild(successBadge);
                    
                    // Remover badge após 3 segundos
                    setTimeout(() => {
                        successBadge.remove();
                    }, 3000);
                } else {
                    // Reverter o checkbox se a atualização falhar
                    this.checked = !isChecked;
                    
                    // Mostrar erro de forma mais detalhada
                    const errorBadge = document.createElement('span');
                    errorBadge.classList.add('tag', 'is-danger', 'ml-2');
                    errorBadge.textContent = data.error || 'Erro ao atualizar o status';
                    taskCard.querySelector('.level-left').appendChild(errorBadge);
                    
                    // Remover badge de erro após 5 segundos
                    setTimeout(() => {
                        errorBadge.remove();
                    }, 5000);
                }
            })
            .catch(error => {
                console.error('Erro completo:', error);
                
                // Reverter o checkbox
                this.checked = !isChecked;
                
                // Mostrar erro de conexão
                const errorBadge = document.createElement('span');
                errorBadge.classList.add('tag', 'is-danger', 'ml-2');
                errorBadge.textContent = 'Erro de conexão';
                taskCard.querySelector('.level-left').appendChild(errorBadge);
                
                // Remover badge de erro após 5 segundos
                setTimeout(() => {
                    errorBadge.remove();
                }, 5000);
            });
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
});
