#!/bin/bash

echo "Starting WSL disk cleanup..."
# Print disk usage before and after
echo -e "\nDisk usage before cleanup:"
df -h / | tail -n 1
# System cleanup - Ubuntu WSL only
echo "Cleaning package manager cache..."
sudo apt-get clean
sudo apt-get autoremove -y

echo "Cleaning journal logs..."
sudo journalctl --vacuum-time=1d

echo "Removing package lists and archives..."
sudo rm -rf /var/lib/apt/lists/*
sudo rm -rf /var/cache/apt/archives/*

# Python cleanup - Restrict to WSL paths only
echo "Cleaning Python cache..."
# Clear pip cache
pip cache purge

echo "Removing Python bytecode files..."
# Only search in home directory and current project
find /home -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find /home -name "*.pyc" -delete 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find /home -name "*.pyo" -delete 2>/dev/null
find . -name "*.pyo" -delete 2>/dev/null


# Docker cleanup (if installed)
if command -v docker &> /dev/null; then
    echo "Cleaning Docker cache..."
    docker system prune -af
    docker volume prune -f
fi

# Snap cleanup (if installed)
if command -v snap &> /dev/null; then
    echo "Cleaning Snap packages..."
    snap list --all | awk '/disabled/{print $1, $3}' | while read snapname revision; do
        sudo snap remove "$snapname" --revision="$revision"
    done
fi

# Log cleanup
echo "Cleaning system logs..."
sudo find /var/log -type f -name "*.gz" -delete 2>/dev/null
sudo find /var/log -type f -name "*.1" -delete 2>/dev/null
sudo truncate -s 0 /var/log/*.log 2>/dev/null

# Cache cleanup
echo "Cleaning user cache..."
rm -rf ~/.cache/pip/* 2>/dev/null
rm -rf ~/.cache/thumbnails/* 2>/dev/null



# Clean apt cache
echo "Cleaning apt cache..."
sudo apt-get clean
sudo apt-get autoclean
sudo apt-get remove --purge $(dpkg -l 'linux-*' | sed '/^ii/!d;/'"$(uname -r | sed "s/\(.*\)-\([^0-9]\+\)/\1/")"'/d;s/^[^ ]* [^ ]* \([^ ]*\).*/\1/;/[0-9]/!d')
sudo apt-get autoremove --purge -y

echo -e "\nDisk usage after cleanup:"
df -h / | tail -n 1
rm -rf /tmp/* 2>/dev/null
echo -e "\nWSL disk cleanup completed!"
echo -e "\n*****Below is the list of packages consuming higher disk space*****\n"
dpkg-query -W --showformat='${Installed-Size} ${Package}\n' | sort -nr | head -n 5