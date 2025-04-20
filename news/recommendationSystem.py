import numpy as np
import faiss
from .models import NewsArticle, UserPreferences
from django.http import Http404, JsonResponse
import logging
import json

# Set up a logger
logger = logging.getLogger(__name__)

# Path to the stored FAISS index file
FAISS_INDEX_PATH = 'news_faiss.index'

def generate_user_preference_embedding(user_weights, embedding_dim):
    """
    Generate an embedding for the user's preferences based on category weights.
    This converts user weights into a vector that can be compared against article embeddings.
    """
    categories = ['business', 'sports', 'technology', 'entertainment', 'health', 'general', 'science']

    # Create user embedding from weights
    user_embedding = np.array([user_weights[category] for category in categories], dtype='float32')

    # Padding or truncating user embedding to match article embeddings
    if len(user_embedding) < embedding_dim:
        user_embedding = np.pad(user_embedding, (0, embedding_dim - len(user_embedding)))
    else:
        user_embedding = user_embedding[:embedding_dim]

    # Reshape to 2D array (1, embedding_dim) as faiss expects a 2D array
    user_embedding_2d = np.expand_dims(user_embedding, axis=0)

    # Normalize the user embedding (L2 normalization)
    faiss.normalize_L2(user_embedding_2d)

    return user_embedding_2d  # return the 2D normalized user embedding


def get_news_id_to_index_mapping():
    """
    Retrieve the mapping of FAISS index to news IDs from the stored mapping file.
    :return: Mapping of FAISS index to news_id
    """
    try:
        with open('news_id_to_index_mapping.json', 'r') as f:
            news_id_to_index = json.load(f)
        return news_id_to_index
    except FileNotFoundError:
        logger.error("Mapping file not found.")
        return {}
    except Exception as e:
        logger.error(f"Error loading mapping: {str(e)}")
        return {}


def get_news_id_from_faiss_index(faiss_index, index, news_id_to_index):
    """
    Retrieve the news_id corresponding to a FAISS index using the news_id_to_index mapping.
    :param faiss_index: The FAISS index
    :param index: The FAISS index
    :param news_id_to_index: The mapping of news_id to FAISS index
    :return: The corresponding news_id
    """
    index_str = str(index)
    if index_str in news_id_to_index:
        return news_id_to_index[index_str]
    else:
        logger.error(f"FAISS index {index} not found in mapping.")
        return None


def get_recommended_news(user_id, top_n=5):
    """
    Generate a list of recommended news articles based on user preferences and their category weights using FAISS.
    :param user_id: The unique identifier for the user
    :param top_n: The number of recommendations to return
    :return: A list of recommended news articles
    """
    try:
        # Fetch user preferences from the database
        user_pref = UserPreferences.objects.get(user_id=user_id)

        # User preferences weights for each category
        user_weights = {
            'business': user_pref.business_weight,
            'sports': user_pref.sports_weight,
            'technology': user_pref.technology_weight,
            'entertainment': user_pref.entertainment_weight,
            'health': user_pref.health_weight,
            'general': user_pref.general_weight,
            'science': user_pref.science_weight,
        }

        # Load FAISS index
        faiss_index = faiss.read_index(FAISS_INDEX_PATH)

        # Generate the user embedding from preferences
        user_embedding = generate_user_preference_embedding(user_weights, faiss_index.d)

        # Perform a similarity search to find the most similar articles
        distances, indices = faiss_index.search(user_embedding, top_n)

        # Fetch the recommended articles from the database using the updated method
        recommended_articles = []

        # Get the news_id to index mapping (from the FAISS index)
        news_id_to_index = get_news_id_to_index_mapping()

        for idx in indices[0]:
            # Get the corresponding news_id from the FAISS index using the mapping
            news_id = get_news_id_from_faiss_index(faiss_index, idx, news_id_to_index)

            if news_id:
                # Fetch the article from the database using the news_id
                try:
                    article = NewsArticle.objects.get(news_id=news_id)

                    # Add the article to the recommendations
                    recommended_articles.append({
                        'news_id': article.news_id,
                        'title': article.title,
                        'category': article.category,
                        'description': article.description,
                        'url': article.url,
                        'image_url':article.image_url,
                        'published_at': article.published_at,
                    })
                except NewsArticle.DoesNotExist:
                    logger.error(f"Article with news_id {news_id} not found in the database.")

        # Log the recommendation action
        logger.info(f"Recommended {top_n} news articles for user {user_id}.")

        # Filter out the articles the user has already clicked
        # clicked_news = get_user_clicked_articles(user_id)
        # filtered_recommended_articles = filter_recommended_articles(recommended_articles, clicked_news)

        # Return filtered recommendations
        return recommended_articles

    except UserPreferences.DoesNotExist:
        logger.error(f"User preferences not found for user {user_id}.")
        raise Http404({"error": "User preferences not found. Please select your preferences."})

    except Exception as e:
        logger.error(f"Error fetching recommendations for user {user_id}: {str(e)}")
        raise Exception({"error": "An error occurred while fetching recommendations."})


def get_user_clicked_articles(user_id):
    """
    Retrieve a list of articles that the user has already clicked on.
    This function can be customized depending on your data structure.
    :param user_id: The unique identifier for the user
    :return: List of news_ids that the user has clicked on
    """
    # Fetch user behavior from the database
    user_behaviors = UserPreferences.objects.get(user_id=user_id).behaviors  # Assuming user behavior is stored here

    # Extract clicked news_ids
    clicked_news = [behavior['news_id'] for behavior in user_behaviors if behavior['click'] == 1]

    return clicked_news


def filter_recommended_articles(recommended_articles, clicked_news):
    """
    Filter out the recommended articles that the user has already clicked on.
    :param recommended_articles: List of recommended articles
    :param clicked_news: List of articles the user has already clicked
    :return: Filtered list of recommended articles
    """
    return [article for article in recommended_articles if article['news_id'] not in clicked_news]