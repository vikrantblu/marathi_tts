cd ~/myproject/research/django/vikastro
source  ~/myproject/myvenv/bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput --clear
namei -l /home/ubuntu/myproject/research/django/vikastro/staticfiles/admin/css/base.css

# Enable and start Gunicorn socket and service
sudo systemctl enable gunicorn.socket
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.service
sudo systemctl start gunicorn.service
sudo ln -sf /etc/nginx/sites-available/vikastro /etc/nginx/sites-enabled/vikastro
sudo systemctl daemon-reload
sudo systemctl restart gunicorn.socket
sudo systemctl restart gunicorn
sudo systemctl restart nginx
