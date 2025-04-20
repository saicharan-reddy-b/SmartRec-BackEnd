from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import NewsArticle, UserInteractions
import logging
from django.utils import timezone
from datetime import timedelta


# Set up a logger
logger = logging.getLogger(__name__)


@receiver(post_delete, sender=NewsArticle)
def delete_user_interactions(sender, instance, **kwargs):
    """
    Deletes all user interactions (clicks) associated with a deleted article.
    This prevents broken links and null pointers when the article is deleted.
    """
    # Get all interactions for this article
    user_interactions = UserInteractions.objects.filter(news_id=instance.news_id)

    # Delete the interactions
    deleted_count, _ = user_interactions.delete()

    # Log the deletion
    logger.info(f"Deleted {deleted_count} user interactions for article {instance.news_id}")


def cleanup_old_interactions():
    # Define the threshold date (e.g., 30 days ago)
    threshold_date = timezone.now() - timedelta(days=30)

    # Delete interactions older than 30 days
    deleted_count, _ = UserInteractions.objects.filter(timestamp__lt=threshold_date).delete()

    logger.info(f"Deleted {deleted_count} old user interactions")