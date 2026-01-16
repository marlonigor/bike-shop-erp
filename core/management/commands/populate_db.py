from django.core.management.base import BaseCommand
from catalog.models import Category, Product
from stock.models import Warehouse

class Command(BaseCommand):
    help = 'Popula o banco de dados com dados iniciais para teste'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando populagem de dados...')

        # 1. Criar Categorias
        cat_pecas, _ = Category.objects.get_or_create(
            name='Peças',
            defaults={'type': Category.Type.PRODUCT}
        )
        cat_servicos, _ = Category.objects.get_or_create(
            name='Serviços',
            defaults={'type': Category.Type.SERVICE}
        )
        self.stdout.write(self.style.SUCCESS(f'Categorias criadas: {cat_pecas}, {cat_servicos}'))

        # 2. Criar Depósito
        warehouse, _ = Warehouse.objects.get_or_create(
            name='Loja Principal',
            defaults={'location': 'Matriz'}
        )
        self.stdout.write(self.style.SUCCESS(f'Depósito criado: {warehouse}'))

        # 3. Criar um Serviço de Teste
        # Nota: Não definimos is_service manualmente aqui para testar se o signal/save do model funciona
        revisao, created = Product.objects.get_or_create(
            sku='SERV001',
            defaults={
                'name': 'Revisão Geral (Mão de Obra)',
                'category': cat_servicos,
                'price': 150.00,
                'cost': 0.00,
                'active': True
            }
        )
        
        # Força o save para garantir que a lógica do is_service rodou (caso tenha sido criado agora)
        if created:
            revisao.save() 
            
        self.stdout.write(self.style.SUCCESS(f'Serviço criado: {revisao} (É serviço? {revisao.is_service})'))

        self.stdout.write(self.style.SUCCESS('--- Concluído com Sucesso ---'))