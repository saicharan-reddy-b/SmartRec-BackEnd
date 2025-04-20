from .models import UserPreferences
from django.http import Http404
import logging

# Set up logging
logger = logging.getLogger(__name__)

def get_user_preferences(user_id):
    """
    Fetch user preferences for a given user.

    :param user_id: The unique identifier for the user
    :return: A dictionary of category names and their respective weights, or error if preferences are missing
    """
    try:
        # Fetch the user preferences for the given user
        user_pref = UserPreferences.objects.get(user_id=user_id)

        # Create a dictionary to hold category-wise preferences
        user_weights = {
            'business': user_pref.business_weight,
            'sports': user_pref.sports_weight,
            'technology': user_pref.technology_weight,
            'entertainment': user_pref.entertainment_weight,
            'health': user_pref.health_weight,
            'general': user_pref.general_weight,
            'science': user_pref.science_weight,
        }

        return user_weights

    except UserPreferences.DoesNotExist:
        # If user preferences do not exist, return a 404 error with a message
        logger.error(f"User preferences not found for user {user_id}.")
        raise Http404({"error" : "User preferences not found. Please select your preferences."})

def update_user_preferences_impl(user_id, categories):
    """
    Update user preferences with normalized weights for the given categories.
    :param user_id: The unique identifier for the user
    :param categories: List of categories selected by the user
    :return: A dictionary with success or error message
    """
    try:
        # Available categories in the system
        available_categories = ['business', 'sports', 'technology', 'entertainment', 'health', 'general', 'science']

        # Validate categories, ensure they are within the available categories
        valid_categories = [cat for cat in categories if cat in available_categories]

        if not valid_categories:
            raise Exception({"error": "No valid categories provided."})

        # Equal weight assignment
        weight_per_category = 1 / len(valid_categories)

        # Assign weights to the selected categories
        user_weights = {category: weight_per_category for category in valid_categories}

        # Fetch the user's existing preferences or create a new entry
        user_pref, created = UserPreferences.objects.get_or_create(user_id=user_id)

        # Update the user's preferences with the new weights
        for category in available_categories:
            if category in user_weights:
                setattr(user_pref, f"{category}_weight", user_weights[category])
            else:
                setattr(user_pref, f"{category}_weight", 0)

        # Save the updated preferences
        user_pref.save()

        logger.info(f"User preferences updated for user {user_id}.")
        return {"message": "User preferences updated successfully."}

    except Exception as e:
        logger.error(f"Error updating user preferences for user {user_id}: {str(e)}")
        return {"error": f"An error occurred while updating preferences: {str(e)}"}