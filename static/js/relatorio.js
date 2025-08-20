document.addEventListener('DOMContentLoaded', () => {
    // Configuração dos gráficos
    const balanceCtx = document.getElementById('balanceChart').getContext('2d');
    const categoriasCtx = document.getElementById('categoriasChart').getContext('2d');

    // Gráfico de Receitas x Despesas
    new Chart(balanceCtx, {
        type: 'bar',
        data: {
            labels: ['Valor (R$)'],
            datasets: [{
                label: 'Receitas',
                data: [chartData.receitas],
                backgroundColor: 'rgba(75, 192, 192, 0.5)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }, {
                label: 'Despesas',
                data: [chartData.despesas],
                backgroundColor: 'rgba(255, 99, 132, 0.5)',
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => `R$ ${value.toFixed(2)}`
                    }
                }
            }
        }
    });

    // Gráfico de Despesas por Categoria
    new Chart(categoriasCtx, {
        type: 'pie',
        data: {
            labels: chartData.categorias.labels,
            datasets: [{
                data: chartData.categorias.valores,
                backgroundColor: [
                    'rgba(75, 192, 192, 0.5)',
                    'rgba(255, 99, 132, 0.5)',
                    'rgba(255, 206, 86, 0.5)',
                    'rgba(54, 162, 235, 0.5)',
                    'rgba(153, 102, 255, 0.5)'
                ],
                borderColor: [
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(153, 102, 255, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const value = context.raw;
                            return `R$ ${value.toFixed(2)}`;
                        }
                    }
                }
            }
        }
    });

    // Atualizar relatório ao mudar filtros
    document.getElementById('filtrar').addEventListener('click', () => {
        const mes = document.getElementById('mes').value;
        const ano = document.getElementById('ano').value;
        window.location.href = `/financas/relatorio/?mes=${mes}&ano=${ano}`;
    });

    // Exportar relatório
    document.getElementById('exportar').addEventListener('click', () => {
        const mes = document.getElementById('mes').value;
        const ano = document.getElementById('ano').value;
        window.location.href = `/financas/exportar_excel/?mes=${mes}&ano=${ano}`;
    });
});