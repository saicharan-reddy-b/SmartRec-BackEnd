from .decayFunction import handle_user_click
from django.http import JsonResponse, Http404
from .recommendationSystem import get_recommended_news
from .dataConvertor import process_and_store_embeddings
from .models import NewsArticle
from django.views.decorators.csrf import csrf_exempt
import logging
import json

from .newsHandler import fetch_all_news_for_categories, save_news_to_db
from .userPreferencesHandler import update_user_preferences_impl, get_user_preferences

logger = logging.getLogger(__name__)

@csrf_exempt
def get_categories_articles(request):
    """
    API view to fetch articles for multiple categories.

    :return: JSON response with a list of articles for each category in the provided list
    """
    if request.method == "GET":
        try:
            # Get the list of categories from the query parameters
            categories = request.GET.getlist('categories')  # Get the list of categories from the URL parameter

            if not categories:
                logger.error("No categories provided.")
                return JsonResponse({"error": "Please provide a list of categories."}, status=400)

            # Fetch articles from the database for each category
            articles_data = {}
            for category in categories:
                articles = NewsArticle.objects.filter(category=category).values(
                    'news_id', 'title', 'category', 'description', 'url', 'published_at', 'image_url'
                )

                # If no articles found for the category
                if not articles:
                    articles_data[category] = {"error": f"No articles found for category '{category}'."}
                    continue

                # Add the fetched articles to the dictionary
                articles_data[category] = list(articles)

            # Return the articles data as a JSON response
            return JsonResponse({'articles': articles_data}, status=200)

        except Exception as e:
            logger.error(f"Error fetching articles for categories: {str(e)}")
            return JsonResponse({'error': 'An error occurred while fetching categories data.'}, status=500)

@csrf_exempt
def handle_click_view(request):
    if request.method == "POST":
        try:
            user_id = request.GET.get('user_id')
            news_id = request.GET.get('news_id')
            handle_user_click(user_id, news_id)
            return JsonResponse({"message": "User preferences updated successfully."})
        except Http404 as e:
            # Handle 404 error if the article is not found
            return JsonResponse({"error": str(e)}, status=404)
        except Exception as e:
            # Catch any other exceptions and return an error message
            return JsonResponse({"error": "An error occurred while processing your request."}, status=500)

@csrf_exempt
def populate_news_data(request):
    """
    API view to fetch news data, store them in the database, and build the FAISS index.
    :return: JSON response indicating success or failure of the operation
    """
    if request.method == "GET":
        try:
            # List of categories to fetch news for
            categories = ['business', 'sports', 'technology', 'entertainment', 'health', 'general', 'science']

            # Step 1: Fetch all news articles for the specified categories
            logger.info(f"Fetching news articles for categories: {categories}")
            articles = fetch_all_news_for_categories(categories)

            # Step 2: Save the fetched articles into the database
            logger.info(f"Saving {len(articles)} articles to the database.")
            save_news_to_db(articles)

            # Step 3: Process the articles to generate embeddings and store them in FAISS
            logger.info("Generating embeddings and storing them in FAISS.")
            process_and_store_embeddings()

            # Return success response
            return JsonResponse({'message': 'News data populated successfully, FAISS index built.'}, status=200)

        except Exception as e:
            logger.error(f"Error during population process: {str(e)}")
            return JsonResponse({'error': 'An error occurred while populating the news data.'}, status=500)


@csrf_exempt
def recommend_news(request):
    """
    API endpoint to fetch recommended news articles based on user preferences.
    :param request: The HTTP request
    :return: A JSON response containing the recommended news articles
    """
    if request.method == "GET":
        try:
            # Get user_id from request data (assuming JSON body)
            user_id = request.GET.get('user_id')

            if not user_id:
                return JsonResponse({"error": "User ID is required"}, status=400)

            # Fetch the top N recommended news articles
            recommended_articles = get_recommended_news(user_id, 21)

            if not recommended_articles:
                return JsonResponse({"error": "No recommendations found"}, status=404)

            # Return the recommended articles in a structured format
            response_data = {
                "status": "success",
                "recommended_articles": recommended_articles
            }

            return JsonResponse(response_data, status=200)
        except Http404 as e:
            logger.error(f"User Preferences Not found hence throwing error :{str(e)}")
            return JsonResponse({"error": f"User Preferences Not found hence throwing error : {str(e)}"}, status=404)

        except Exception as e:
            logger.error(f"Error fetching recommendations: {str(e)}")
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

    else:
        return JsonResponse({"error": "Invalid request method. Only GET is allowed."}, status=405)

@csrf_exempt
def update_user_preferences(request):
    """
    API view to update user preferences with normalized weights for each selected category.
    :param user_id: The unique identifier for the user
    :return: JSON response indicating success or failure
    """
    if request.method == "POST":
        try:
            # Get the list of categories from the request body
            data = json.loads(request.body)
            user_id = request.GET.get('user_id')
            categories = data.get("categories", None)

            if not categories:
                return JsonResponse({"error": "No categories provided in the request."}, status=400)

            # Call the service function to update the user preferences
            response = update_user_preferences_impl(user_id, categories)

            # Return appropriate response based on the service result
            if "error" in response:
                return JsonResponse(response, status=400)
            return JsonResponse(response, status=200)

        except Exception as e:
            logger.error(f"Error updating user preferences for user {user_id}: {str(e)}")
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

    else:
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)


@csrf_exempt
def get_user_preferences_view(request):
    """
    API view to fetch user preferences for the given user.
    :param user_id: The unique identifier for the user
    :return: JSON response containing user preferences
    """
    if request.method == "GET":
        try:
            # Get user_id from the query parameters
            user_id = request.GET.get('user_id')

            if not user_id:
                return JsonResponse({"error": "No user_id provided."}, status=400)

            # Call the existing function to get user preferences
            user_weights = get_user_preferences(user_id)

            # Return the preferences in a structured format
            preferences_data = [
                {"category": category, "weight": weight}
                for category, weight in user_weights.items()
            ]

            return JsonResponse({"preferences": preferences_data}, status=200)
        except Http404 as e:
            logger.error(f"Error fetching preferences, preferneces not found : {str(e)}")
            return JsonResponse({"error" : f"Error fetching preferences, preferences not found : {str(e)}"}, status = 404)

        except Exception as e:
            logger.error(f"Error fetching preferences for user {user_id}: {str(e)}")
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

    else:
        return JsonResponse({"error": "Only GET requests are allowed."}, status=405)

@csrf_exempt
def get_trending_news(request):
    """
    API view to get the most recent or most interacted news articles.
    The trending articles are determined based on the `published_at` field or any other metric.
    :return: JSON response with the list of trending news articles
    """
    if request.method == "GET":
        try:
            # Define the number of trending articles to fetch (e.g., top 10)
            top_n = int(request.GET.get("top_n", 10))  # Default to 10 if not provided

            # Fetch the top N most recent articles based on `published_at`
            trending_articles = NewsArticle.objects.all().order_by('-published_at')[:top_n]

            if not trending_articles:
                return JsonResponse({"error": "No trending news available."}, status=404)

            # Serialize the fetched articles into a list
            trending_articles_data = [
                {
                    "news_id": article.news_id,
                    "title": article.title,
                    "category": article.category,
                    "description": article.description,
                    "url": article.url,
                    "image_url":article.image_url,
                    "published_at": article.published_at
                }
                for article in trending_articles
            ]

            # Return the trending articles as a JSON response
            return JsonResponse({"trending_news": trending_articles_data}, status=200)

        except Exception as e:
            logger.error(f"Error fetching trending news: {str(e)}")
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

    else:
        return JsonResponse({"error": "Only GET requests are allowed."}, status=405)