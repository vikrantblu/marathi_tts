#!/usr/bin/env python3
import os
import shutil
import sqlite3
import re
from pathlib import Path
import logging
from typing import Optional
import subprocess

logger = logging.getLogger(__name__)

# Old app name and new app name
old_app_name = 'tts'  # Replace with the current app name
new_app_name = 'tts'  # Replace with the new app name

# Path to the Django project directory
project_dir = Path(__file__).parent.parent  # Get the directory of the current script

# Path to the SQLite3 database file
db_path = project_dir / 'db.sqlite3'

def validate_app_name(app_name: str) -> bool:
    """Validate Django app name"""
    return bool(re.match(r'^[a-z][a-z0-9_]*$', app_name))

def secure_move_directory(old_path: Path, new_path: Path) -> bool:
    """Securely move directory"""
    if new_path.exists():
        raise FileExistsError(f"Destination {new_path} already exists")
    if not old_path.exists():
        raise FileNotFoundError(f"Source {old_path} does not exist")
    shutil.move(str(old_path), str(new_path))
    return True

def secure_file_update(file_path: Path, old_name: str, new_name: str) -> None:
    """Securely update file contents"""
    if file_path.suffix in ['.py', '.html']:
        content = file_path.read_text()
        updated = content.replace(old_name, new_name)
        file_path.write_text(updated)

def secure_db_operation(db_path: Path, old_name: str, new_name: str) -> None:
    """Securely update database"""
    if not db_path.exists():
        raise FileNotFoundError(f"Database {db_path} not found")
        
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        old_table = f"{old_name}_userinput"
        new_table = f"{new_name}_userinput"
        cursor.execute("BEGIN TRANSACTION")
        try:
            cursor.execute(f"ALTER TABLE {old_table} RENAME TO {new_table}")
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise

def rename_django_app(old_app_name: str, new_app_name: str, project_dir: Optional[Path] = None) -> bool:
    """Rename Django app with security measures"""
    try:
        if not all(validate_app_name(name) for name in [old_app_name, new_app_name]):
            raise ValueError("Invalid app name format")

        project_dir = project_dir or Path(__file__).parent.parent
        old_app_path = project_dir / old_app_name
        new_app_path = project_dir / new_app_name
        db_path = project_dir / 'db.sqlite3'

        # Rename directory
        secure_move_directory(old_app_path, new_app_path)
        logger.info(f"Renamed directory: {old_app_name} -> {new_app_name}")

        # Update files
        for file_path in project_dir.rglob('*'):
            if file_path.is_file() and file_path.name != 'rename_app.py':
                secure_file_update(file_path, old_app_name, new_app_name)
        
        # Update database
        secure_db_operation(db_path, old_app_name, new_app_name)
        
        return True

    except Exception as e:
        logger.error(f"Failed to rename app: {e}")
        return False

# Function to run Django management commands
def run_management_commands():
    manage_py_path = project_dir / 'manage.py'
    python_executable = '/usr/bin/python3'  # Update this path to the full path of your Python executable
    subprocess.run([python_executable, manage_py_path, 'makemigrations'])
    subprocess.run([python_executable, manage_py_path, 'migrate', '--fake-initial'])
    subprocess.run([python_executable, manage_py_path, 'collectstatic'])

if __name__ == '__main__':
    if rename_django_app(old_app_name, new_app_name):
        run_management_commands()
        print("App renaming completed successfully.")
    else:
        print("App renaming NOT completed successfully. Please check logs for errors.")
