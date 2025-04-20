from django.db import models
import datetime

class NewsArticle(models.Model):
    news_id = models.CharField(max_length=256, unique=True)
    title = models.TextField()
    category = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    url = models.TextField()
    image_url = models.TextField(null=True, blank = True)
    published_at = models.DateTimeField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class UserPreferences(models.Model):
    user_id = models.CharField(max_length=255)
    business_weight = models.FloatField(default=0.0)
    sports_weight = models.FloatField(default=0.0)
    technology_weight = models.FloatField(default=0.0)
    entertainment_weight = models.FloatField(default=0.0)
    health_weight = models.FloatField(default=0.0)
    general_weight = models.FloatField(default=0.0)
    science_weight = models.FloatField(default=0.0)

    def __str__(self):
        return f"User {self.user_id} Preferences"


class UserInteractions(models.Model):
    user_id = models.CharField(max_length=255)
    news_article = models.ForeignKey(NewsArticle, on_delete=models.CASCADE)  # Cascade delete interactions
    clicked = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)