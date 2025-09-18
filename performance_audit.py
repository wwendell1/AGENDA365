import os
import sys
import time
import cProfile
import pstats
from django.db import connection
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User

class PerformanceAudit:
    def __init__(self, base_path):
        self.base_path = base_path
        self.results = {}
        self.client = Client()

    def _profile_function(self, func, *args, **kwargs):
        """Perfila uma função e retorna estatísticas"""
        profiler = cProfile.Profile()
        profiler.enable()
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        profiler.disable()
        end_time = time.time()
        
        stats = pstats.Stats(profiler).sort_stats('cumulative')
        
        return {
            'execution_time': end_time - start_time,
            'stats': stats
        }

    def test_grupo_creation_performance(self):
        """Testa performance de criação de grupo"""
        def create_grupo():
            # Cria usuário de teste
            user = User.objects.create_user(
                username='perftest', 
                password='testpass123'
            )
            self.client.login(username='perftest', password='testpass123')
            
            # Dados do grupo
            grupo_data = {
                'nome': 'Grupo de Performance',
                'descricao': 'Grupo criado para teste de performance',
                'cor': '#FF6B6B'
            }
            
            # Envia requisição de criação
            response = self.client.post(
                reverse('criar_grupo'), 
                data=grupo_data
            )
            return response

        result = self._profile_function(create_grupo)
        self.results['grupo_creation'] = result

    def test_tarefa_creation_performance(self):
        """Testa performance de criação de tarefa"""
        def create_tarefa():
            # Cria usuário e grupo de teste
            user = User.objects.create_user(
                username='perftest_tarefa', 
                password='testpass123'
            )
            grupo = Grupo.objects.create(
                nome='Grupo Teste', 
                criado_por=user
            )
            MembroGrupo.objects.create(
                user=user, 
                grupo=grupo, 
                role='admin'
            )
            self.client.login(username='perftest_tarefa', password='testpass123')
            
            # Dados da tarefa
            tarefa_data = {
                'titulo': 'Tarefa de Performance',
                'descricao': 'Tarefa criada para teste de performance',
                'responsavel_principal': user.id,
                'prioridade': 'media',
                'status': 'a_fazer'
            }
            
            # Envia requisição de criação
            response = self.client.post(
                reverse('criar_tarefa', kwargs={'grupo_id': grupo.id}), 
                data=tarefa_data
            )
            return response

        result = self._profile_function(create_tarefa)
        self.results['tarefa_creation'] = result

    def analyze_database_queries(self):
        """Analisa queries de banco de dados"""
        # Reseta o contador de queries
        connection.queries_log.clear()

        # Executa consultas de exemplo
        from core.models import Grupo, Tarefa, MembroGrupo

        # Consultas para análise
        queries_to_test = [
            lambda: list(Grupo.objects.all()),
            lambda: list(Tarefa.objects.select_related('grupo', 'responsavel_principal').all()),
            lambda: list(MembroGrupo.objects.select_related('user', 'grupo').all())
        ]

        self.results['database_queries'] = {}
        for i, query_func in enumerate(queries_to_test, 1):
            start_time = time.time()
            query_func()
            end_time = time.time()

            # Captura queries executadas
            queries = connection.queries_log

            self.results['database_queries'][f'query_{i}'] = {
                'execution_time': end_time - start_time,
                'query_count': len(queries),
                'queries': queries
            }

    def generate_report(self):
        """Gera relatório de performance"""
        print("\n--- RELATÓRIO DE AUDITORIA DE PERFORMANCE ---")
        
        # Relatório de criação de grupo
        if 'grupo_creation' in self.results:
            grupo_result = self.results['grupo_creation']
            print("\nCriação de Grupo:")
            print(f"Tempo de Execução: {grupo_result['execution_time']:.4f} segundos")
            grupo_result['stats'].print_stats(5)

        # Relatório de criação de tarefa
        if 'tarefa_creation' in self.results:
            tarefa_result = self.results['tarefa_creation']
            print("\nCriação de Tarefa:")
            print(f"Tempo de Execução: {tarefa_result['execution_time']:.4f} segundos")
            tarefa_result['stats'].print_stats(5)

        # Relatório de queries de banco de dados
        if 'database_queries' in self.results:
            print("\nAnálise de Queries de Banco de Dados:")
            for query_name, query_data in self.results['database_queries'].items():
                print(f"\n{query_name}:")
                print(f"  Tempo de Execução: {query_data['execution_time']:.4f} segundos")
                print(f"  Número de Queries: {query_data['query_count']}")
                
                # Imprime as 3 queries mais lentas
                slow_queries = sorted(
                    query_data['queries'], 
                    key=lambda x: float(x['time']), 
                    reverse=True
                )[:3]
                
                print("  Queries mais lentas:")
                for q in slow_queries:
                    print(f"    - {q['sql']} (Tempo: {q['time']} seg)")

def main():
    # Configura o ambiente Django
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'produtiva.settings')
    django.setup()

    # Obtém o caminho do projeto
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Cria instância de auditoria
    audit = PerformanceAudit(base_path)
    
    # Executa testes de performance
    audit.test_grupo_creation_performance()
    audit.test_tarefa_creation_performance()
    audit.analyze_database_queries()
    
    # Gera relatório
    audit.generate_report()

if __name__ == '__main__':
    main()