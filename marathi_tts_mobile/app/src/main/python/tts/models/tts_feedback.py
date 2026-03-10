from django.db import models
from django.contrib.auth.models import User

class TTSFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    audio_file = models.CharField(max_length=255)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    
    # Store technical details
    voice_settings = models.JSONField(default=dict)
    audio_metrics = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tts_feedback'

    def __str__(self):
        return f"Feedback by {self.user.username} - Rating: {self.rating}"