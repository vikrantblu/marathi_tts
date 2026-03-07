from django.core.management.base import BaseCommand
from tts.models import MarathiCorrection
import pandas as pd
from pathlib import Path

class Command(BaseCommand):
    help = 'Manage correction rules between CSV and DB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            choices=['import', 'export', 'clear'],
            required=True,
            help='Mode: import (CSV to DB), export (DB to CSV), or clear (remove all from DB)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force operation without confirmation'
        )

    def handle(self, *args, **options):
        if options['mode'] == 'clear':
            if options['force'] or input('Are you sure you want to clear all rules? (y/N) ').lower() == 'y':
                count = MarathiCorrection.objects.all().delete()[0]
                self.stdout.write(self.style.SUCCESS(f'Cleared {count} rules from database'))
            return

        csv_path = Path(__file__).parent.parent.parent.parent / 'models' / 'marathi-correction-model' / 'correction_rules.csv'
        
        if options['mode'] == 'import':
            if not options['force']:
                self.stdout.write("This will import rules from CSV to database.")
                if input('Continue? (y/N) ').lower() != 'y':
                    return

            df = pd.read_csv(csv_path)
            imported = 0
            skipped = 0
            
            for _, row in df.iterrows():
                _, created = MarathiCorrection.objects.get_or_create(
                    incorrect_text=row['incorrect_text'],
                    defaults={
                        'correct_text': row['correct_text'],
                        'category': 'imported_from_csv',
                        'notes': 'Auto-imported from correction_rules.csv'
                    }
                )
                if created:
                    imported += 1
                else:
                    skipped += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Imported {imported} rules. Skipped {skipped} existing rules.'
                )
            )

        elif options['mode'] == 'export':
            if not options['force'] and csv_path.exists():
                if input('CSV file exists. Overwrite? (y/N) ').lower() != 'y':
                    return

            rules = MarathiCorrection.objects.all()
            df = pd.DataFrame([
                {
                    'incorrect_text': rule.incorrect_text,
                    'correct_text': rule.correct_text,
                    'validation_status': 'valid'
                }
                for rule in rules
            ])
            df.to_csv(csv_path, index=False)
            self.stdout.write(
                self.style.SUCCESS(f'Exported {len(rules)} rules to CSV')
            )