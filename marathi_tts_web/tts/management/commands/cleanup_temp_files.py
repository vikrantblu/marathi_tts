from django.core.management.base import BaseCommand
from tts.utils.core.tts_settings import TTS_MEDIA_ROOT, TTS_TEMP_DIR, TTS_LOG_DIR
import os
import time
import logging

logger = logging.getLogger('tts.management.commands.cleanup_temp_files')

class Command(BaseCommand):
    help = 'Cleanup old temporary files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Clean up all directories (temp, logs, cache)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Remove files older than specified days (default: 1)',
        )

    def handle(self, *args, **options):
        try:
            days = options.get('days', 1)
            cleanup_all = options.get('all', False)
            
            # Convert days to seconds
            max_age = days * 86400

            # Clean up temp directory
            self.cleanup_directory(TTS_TEMP_DIR, 'Temp', max_age)
            
            # Also clean up the main TTS media directory (this is where your files are)
            self.cleanup_directory(TTS_MEDIA_ROOT, 'TTS Media', max_age)
            
            # Cleanup logs if --all is specified
            if cleanup_all:
                self.cleanup_directory(TTS_LOG_DIR, 'Log', max_age)
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully cleaned up all directories (files older than {days} days)'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully cleaned up media files (older than {days} days)'
                ))
                
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            self.stdout.write(self.style.ERROR(f'Cleanup failed: {str(e)}'))
            raise

    def cleanup_directory(self, directory, type_name, max_age):
        """Cleanup files older than specified age in seconds"""
        if not os.path.exists(directory):
            logger.info(f"{type_name} directory does not exist: {directory}")
            return

        now = time.time()
        count = 0

        try:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    if now - os.path.getmtime(filepath) > max_age:
                        os.remove(filepath)
                        count += 1
            logger.info(f"{type_name} cleanup: Removed {count} files")
            self.stdout.write(f"{type_name} cleanup: Removed {count} files")
        except Exception as e:
            logger.error(f"{type_name} cleanup failed: {str(e)}")
            self.stdout.write(self.style.ERROR(f'{type_name} cleanup failed: {str(e)}'))