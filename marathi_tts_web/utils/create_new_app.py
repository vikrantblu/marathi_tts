#!/usr/bin/env python3
import os
import shutil
import re
from pathlib import Path
import subprocess
import logging

logger = logging.getLogger(__name__)

def validate_app_name(app_name: str) -> bool:
    """Validate Django app name"""
    return bool(re.match(r'^[a-z][a-z0-9_]*$', app_name))

def secure_copy_app(old_app: str, new_app: str, project_dir: Path) -> bool:
    """Securely copy Django app directory"""
    if not all(validate_app_name(app) for app in [old_app, new_app]):
        raise ValueError("Invalid app name format")
    
    old_path = project_dir / old_app
    new_path = project_dir / new_app
    
    if new_path.exists():
        raise FileExistsError(f"Destination {new_path} already exists")
    if not old_path.exists():
        raise FileNotFoundError(f"Source {old_path} does not exist")
        
    shutil.copytree(old_path, new_path)
    return True

def update_file_content(file_path: Path, old_app: str, new_app: str) -> None:
    """Securely update file contents"""
    if file_path.suffix in ['.py', '.html']:
        content = file_path.read_text()
        updated = content.replace(old_app, new_app)
        file_path.write_text(updated)

def create_new_app(old_app_name: str, new_app_name: str) -> bool:
    """Create new Django app securely"""
    try:
        project_dir = Path(__file__).parent.parent
        
        # Copy app directory
        secure_copy_app(old_app_name, new_app_name, project_dir)
        
        # Update references
        new_app_path = project_dir / new_app_name
        for file_path in new_app_path.rglob('*'):
            if file_path.is_file():
                update_file_content(file_path, old_app_name, new_app_name)
        
        # Run Django commands
        subprocess.run(
            ['python', 'manage.py', 'makemigrations', new_app_name],
            check=True,
            shell=False,
            cwd=project_dir
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create new app: {e}")
        return False

if __name__ == '__main__':
    create_new_app('tts', 'ss_app')