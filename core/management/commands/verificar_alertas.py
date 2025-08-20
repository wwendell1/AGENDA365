from django.core.management.base import BaseCommand
from core.utils import verificar_alertas_financeiros

class Command(BaseCommand):
    help = 'Verifica e envia alertas financeiros para os usuários'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando verificação de alertas financeiros...')
        verificar_alertas_financeiros()
        self.stdout.write(self.style.SUCCESS('Verificação de alertas financeiros concluída com sucesso!'))