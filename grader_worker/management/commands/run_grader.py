
from django.core.management.base import BaseCommand
import multiprocessing

from main.lib.grader import run_grader_workers

class Command(BaseCommand):
    help = 'Runs multiple grader workers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workers',
            type=int,
            default=max(multiprocessing.cpu_count() - 1, 1),
            help='Number of worker processes'
        )

    def handle(self, *args, **options):
        num_workers = options['workers']
        self.stdout.write(f'Starting {num_workers} grader workers...')
        run_grader_workers(num_workers)