#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp /mnt/c/mytools/github/research/research//vikastro/db.sqlite3 /mnt/c/mytools/github/research/backups/db_backup_$DATE.sqlite3
tar -czf /mnt/c/mytools/github/research/backups/files_backup_$DATE.tar.gz /mnt/c/mytools/github/research/research
