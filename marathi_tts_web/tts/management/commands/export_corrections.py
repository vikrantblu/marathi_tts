from django.core.management.base import BaseCommand
import csv
from tts.models import MarathiCorrection
from pathlib import Path

class Command(BaseCommand):
    help = 'Export corrections from database to CSV'

    def handle(self, *args, **options):
        corrections = MarathiCorrection.objects.all()
        output_path = Path(__file__).parent.parent.parent.parent / 'models' / 'marathi-correction-model' / 'correction_rules.csv'
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['incorrect_text', 'correct_text', 'validation_status'])
            for c in corrections:
                writer.writerow([c.incorrect_text, c.correct_text, 'valid'])
        
        self.stdout.write(self.style.SUCCESS(f'Exported {corrections.count()} corrections to {output_path}'))