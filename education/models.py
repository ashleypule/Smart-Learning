from django.db import models
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Document(models.Model):
    uploaded_file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class images(models.Model):
    uploaded_file = models.ImageField(upload_to='uploaded_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Grade(models.Model):
    LEVEL_CHOICES = [
        ('Primary', 'Primary School'),
        ('High', 'High School'),
        ('Varsity', 'Varsity'),
    ]
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    name = models.CharField(max_length=50, default='Grade')  

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"


class Subject(models.Model):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Question(models.Model):
    text = models.TextField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    video_url = models.URLField(blank=True, null=True)  

    def __str__(self):
        return self.text[:50]

class Solution(models.Model):
    image = models.ImageField(upload_to='solutions/')
    extracted_text = models.TextField(blank=True, null=True)
    user_edited_text = models.TextField(blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    solution_step = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Solution {self.id} - Correct: {self.is_correct}"