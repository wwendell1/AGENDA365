// Funções gerais
document.addEventListener('DOMContentLoaded', () => {
    // Notificações
    const notifications = document.querySelectorAll('.notification .delete');
    notifications.forEach(btn => {
        btn.addEventListener('click', () => {
            btn.parentNode.remove();
        });
    });

    // Dropdown menu
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        dropdown.addEventListener('click', event => {
            event.stopPropagation();
            dropdown.classList.toggle('is-active');
        });
    });

    // Gráficos só serão inicializados se os elementos existirem na página
    const balanceChart = document.getElementById('balanceChart');
    const categoriasChart = document.getElementById('categoriasChart');

    if (balanceChart) {
        new Chart(balanceChart.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['Receitas', 'Despesas'],
                datasets: [{
                    data: [chartData.receitas, chartData.despesas],
                    backgroundColor: ['#48c774', '#f14668']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    if (categoriasChart) {
        new Chart(categoriasChart.getContext('2d'), {
            type: 'pie',
            data: {
                labels: chartData.categorias.labels,
                datasets: [{
                    data: chartData.categorias.valores,
                    backgroundColor: [
                        '#48c774', '#3298dc', '#f14668', '#ffdd57', '#9d4edd',
                        '#367ABD', '#485fc7', '#ff6b6b', '#4ecdc4', '#95a5a6'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    // Eventos dos botões
    const filtrarBtn = document.getElementById('filtrar');
    const exportarBtn = document.getElementById('exportar');
    const mesSelect = document.getElementById('mes');
    const anoSelect = document.getElementById('ano');

    if (filtrarBtn) {
        filtrarBtn.addEventListener('click', () => {
            const mes = mesSelect.value;
            const ano = anoSelect.value;
            window.location.href = `?mes=${mes}&ano=${ano}`;
        });
    }

    if (exportarBtn) {
        exportarBtn.addEventListener('click', () => {
            const mes = mesSelect.value;
            const ano = anoSelect.value;
            window.location.href = `?mes=${mes}&ano=${ano}&export=excel`;
        });
    }
});

