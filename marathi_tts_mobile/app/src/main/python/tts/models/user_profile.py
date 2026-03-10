from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_voice = models.CharField(max_length=50, default='default')
    preferred_speed = models.FloatField(default=1.0)
    preferred_pitch = models.FloatField(default=0.0)
    preferred_volume = models.FloatField(default=0.0)
    
    # Store additional preferences as JSON
    voice_preferences = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tts_user_profile'

    def __str__(self):
        return f"Profile for {self.user.username}"