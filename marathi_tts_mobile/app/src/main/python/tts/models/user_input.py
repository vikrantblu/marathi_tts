from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserInput(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100, default='', blank=True)
    title = models.CharField(max_length=255, default='Untitled Audio')
    content = models.TextField(default='')  # Original text
    text = models.TextField(default='')     # Processed text
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.user.username} - {self.title}'

    class Meta:
        ordering = ['-created_at']


class ScanResult(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, default='completed')
    findings_count = models.IntegerField(default=0)
    severity_counts = models.JSONField(default=dict)
    result_data = models.JSONField(default=dict)
    environment = models.CharField(max_length=20)
    scan_duration = models.FloatField(default=0.0)

    class Meta:
        ordering = ['-timestamp']
