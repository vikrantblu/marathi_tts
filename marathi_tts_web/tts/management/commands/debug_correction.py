from django.core.management.base import BaseCommand
from models.correction_model import MarathiCorrectionModel
from tts.models import MarathiCorrection
from django.core import serializers
import json

class Command(BaseCommand):
    help = 'Debug correction model behavior'

    def add_arguments(self, parser):
        parser.add_argument('text', type=str, help='Text to correct')
        parser.add_argument(
            '--show-db',
            action='store_true',
            help='Show full database entries'
        )

    def handle(self, *args, **options):
        text = options['text']
        
        # Show database entries first
        if options['show_db']:
            self.stdout.write("\nDatabase entries:")
            rules = MarathiCorrection.objects.all()
            data = serializers.serialize('json', rules)
            for entry in json.loads(data):
                self.stdout.write(json.dumps(entry, indent=2, ensure_ascii=False))
        
        # Load model and show rules
        model = MarathiCorrectionModel()
        self.stdout.write(f"\nTotal rules loaded: {len(model.correction_rules)}")
        
        # Show specific rule if it exists
        if text in model.correction_rules:
            self.stdout.write(f"\nRule found in model:")
            self.stdout.write(f"  {text} → {model.correction_rules[text]}")
            
            # Check DB for this rule
            rule = MarathiCorrection.objects.filter(incorrect_text=text).first()
            if rule:
                self.stdout.write(f"\nRule exists in database:")
                self.stdout.write(f"  ID: {rule.id}")
                self.stdout.write(f"  Created: {rule.created_at}")
                self.stdout.write(f"  Updated: {rule.updated_at}")
            else:
                self.stdout.write("\nWARNING: Rule exists in model but not in database!")
        
        # Test correction
        corrected = model.correct_text_marathi(text)
        self.stdout.write(f"\nTest correction:")
        self.stdout.write(f"Input:     {text}")
        self.stdout.write(f"Corrected: {corrected}")