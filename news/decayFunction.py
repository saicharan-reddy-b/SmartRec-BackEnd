from django.http import Http404

from .models import UserPreferences, NewsArticle
import logging

# Set up a logger
logger = logging.getLogger(__name__)

from .models import UserPreferences, NewsArticle
import logging

# Set up a logger
logger = logging.getLogger(__name__)


def update_user_preferences(user_id, category, click_weight, decay_rate=0.02):
    """
    Update the user category preferences based on clicks and a decay rate.

    :param user_id: The unique identifier for the user
    :param category: The category of news that the user interacted with
    :param click_weight: The weight of the click (typically 1 if clicked)
    :param decay_rate: The rate at which past weights decay (default 0.02)
    """
    # Step 1: Fetch current weight of the clicked category for the user
    try:
        user_pref = UserPreferences.objects.get(user_id=user_id)
        current_weight = getattr(user_pref, f"{category}_weight", 0)  # Default to 0 if category doesn't exist
    except UserPreferences.DoesNotExist:
        # If no existing preferences, initialize with a default weight (0 or 1/7 per category)
        user_pref = UserPreferences(user_id=user_id)
        user_pref.save()
        current_weight = 0  # Default to 0 (neutral preference)

    # Step 2: Update the weight of the clicked category
    new_weight = current_weight + (click_weight - current_weight) * decay_rate

    # Step 3: Update the weight field dynamically based on the category
    setattr(user_pref, f"{category}_weight", new_weight)
    user_pref.save()

    # Step 4: Decay other category weights
    decay_other_categories(user_id, category, decay_rate)

    # Step 5: Normalize all weights to ensure the sum equals 1
    normalize_and_save_preferences(user_id)

    # Log the update
    logger.info(f"Updated user {user_id}'s preference for category {category}: {new_weight}")


def decay_other_categories(user_id, clicked_category, decay_rate):
    """
    Apply decay to all other categories for the given user.

    :param user_id: The user whose category weights are being decayed
    :param clicked_category: The category that was clicked (will not be decayed)
    :param decay_rate: The rate at which non-clicked categories decay
    """
    try:
        user_pref = UserPreferences.objects.get(user_id=user_id)
    except UserPreferences.DoesNotExist:
        logger.error(f"UserPreferences not found for user {user_id}. Skipping decay.")
        return

    # List of all possible categories
    categories = [
        'business', 'sports', 'technology', 'entertainment', 'health', 'general', 'science'
    ]

    # Apply decay to each category except the clicked category
    for category in categories:
        if category != clicked_category:
            current_weight = getattr(user_pref, f"{category}_weight", 0.0)  # Default 0 if not set
            new_weight = current_weight * (1 - decay_rate)  # Apply decay
            setattr(user_pref, f"{category}_weight", new_weight)
            user_pref.save()

            # Log the decay
            logger.info(f"Decayed weight for user {user_id} in category {category}: {new_weight}")


def normalize_and_save_preferences(user_id):
    """
    Normalize the user preferences so that the sum of all weights equals 1.

    :param user_id: The unique identifier for the user
    """
    try:
        user_pref = UserPreferences.objects.get(user_id=user_id)

        # Calculate total weight (sum of all category weights)
        total_weight = sum([getattr(user_pref, f"{category}_weight") for category in
                            ['business', 'sports', 'technology', 'entertainment', 'health', 'general', 'science']])

        if total_weight == 0:
            logger.error(f"User {user_id} has invalid preferences (sum of weights is 0).")
            raise ValueError("Invalid user preferences. The sum of weights must be greater than 0.")

        # Normalize each weight by dividing by the total weight
        for category in ['business', 'sports', 'technology', 'entertainment', 'health', 'general', 'science']:
            current_weight = getattr(user_pref, f"{category}_weight")
            setattr(user_pref, f"{category}_weight", current_weight / total_weight)

        user_pref.save()
        logger.info(f"Normalized user {user_id}'s preferences.")

    except UserPreferences.DoesNotExist:
        logger.error(f"UserPreferences not found for user {user_id}.")
        raise Http404({"error": "User preferences not found. Please select your preferences."})

from .models import NewsArticle
from django.http import Http404
import logging

# Set up logging
logger = logging.getLogger(__name__)

def handle_user_click(user_id, news_id):
    """
    Handle the click of a news article, updating the user's preferences based on the clicked category.

    :param user_id: The unique identifier for the user
    :param news_id: The unique identifier for the clicked news article
    :raises Http404: If the news article is not found
    """
    # Step 1: Fetch the clicked news article to get its category
    try:
        article = NewsArticle.objects.get(news_id=news_id)
        category = article.category
    except NewsArticle.DoesNotExist:
        # Log the error and raise Http404 if the article does not exist
        logger.error(f"News article with ID {news_id} does not exist.")
        raise Http404(f"News article with ID {news_id} does not exist.")

    # Step 2: Update user preferences based on the category clicked
    try:
        update_user_preferences(user_id, category, click_weight=1.0)  # Assuming click_weight is 1 for a click
        logger.info(f"User {user_id} preferences updated for category {category}.")
    except Exception as e:
        # Log and handle any errors that occur during preference update
        logger.error(f"Error updating preferences for user {user_id} in category {category}: {str(e)}")
        raise  # Re-raise the exception for further handling (or return a response if needed)