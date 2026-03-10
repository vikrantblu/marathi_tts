from django.db import models


class MarathiCorrection(models.Model):
    incorrect_text = models.CharField(max_length=255, unique=True)
    correct_text = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Marathi Correction'
        verbose_name_plural = 'Marathi Corrections'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.incorrect_text} → {self.correct_text}'
