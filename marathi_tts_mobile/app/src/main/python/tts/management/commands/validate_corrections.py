from django.core.management.base import BaseCommand
from tts.models import MarathiCorrection
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Validate correction rules between DB and CSV'

    def handle(self, *args, **options):
        # Load DB rules
        db_rules = {c.incorrect_text: c.correct_text 
                   for c in MarathiCorrection.objects.all()}
        
        # Load CSV rules directly
        csv_path = Path(__file__).parent.parent.parent.parent / 'models' / 'marathi-correction-model' / 'correction_rules.csv'
        
        if not csv_path.exists():
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return
            
        df = pd.read_csv(csv_path)
        csv_rules = {row['incorrect_text']: row['correct_text'] for _, row in df.iterrows()}
        
        # Compare
        self.stdout.write(self.style.SUCCESS("Rules comparison:"))
        self.stdout.write(f"Database rules: {len(db_rules)}")
        self.stdout.write(f"CSV rules: {len(csv_rules)}")
        
        # Show rules in CSV but not in DB
        csv_only = set(csv_rules.keys()) - set(db_rules.keys())
        if csv_only:
            self.stdout.write("\nRules in CSV but not in database:")
            for key in sorted(csv_only):
                self.stdout.write(f"  {key} → {csv_rules[key]}")
        
        # Show rules in DB but not in CSV
        db_only = set(db_rules.keys()) - set(csv_rules.keys())
        if db_only:
            self.stdout.write("\nRules in database but not in CSV:")
            for key in sorted(db_only):
                self.stdout.write(f"  {key} → {db_rules[key]}")
                
        # Show differences in corrections
        differences = []
        for key in set(csv_rules.keys()) & set(db_rules.keys()):
            if csv_rules[key] != db_rules[key]:
                differences.append((key, csv_rules[key], db_rules[key]))
                
        if differences:
            self.stdout.write("\nDifferent corrections between CSV and DB:")
            for key, csv_val, db_val in sorted(differences):
                self.stdout.write(f"  {key}:")
                self.stdout.write(f"    CSV: {csv_val}")
                self.stdout.write(f"    DB:  {db_val}")