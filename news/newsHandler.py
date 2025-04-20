import requests
import logging
from django.conf import settings
from django.db import IntegrityError
from .models import NewsArticle
import hashlib


# Set up a logger
logger = logging.getLogger(__name__)

def fetch_all_news_for_categories(categories):
    url = 'https://newsapi.org/v2/top-headlines'
    all_articles = []

    for category in categories:
        page = 1  # Start from page 1
        while True:
            params = {
                'category': category,
                'apiKey': settings.NEWS_API_KEY,  # Your NewsAPI key
                'pageSize': 100,  # Max articles per page (NewsAPI allows up to 100)
                'country': 'us',  # Filter by country (e.g., US)
                'page': page,  # Paginate through results
            }

            try:
                response = requests.get(url, params=params)

                if response.status_code == 200:
                    articles = response.json()['articles']
                    for article in articles:
                        article['category'] = category  # Add the category field to each article
                    all_articles += articles  # Add articles to the list

                    if len(articles) < 100:
                        break  # Stop pagination if fewer than 100 articles (last page)
                    page += 1  # Move to the next page
                else:
                    # Log if NewsAPI response status is not 200
                    logger.error(f"NewsAPI Error: Status code {response.status_code} for category {category}")
                    break  # Stop the loop if the request failed

            except requests.exceptions.RequestException as e:
                # Log if a request error occurs (e.g., connection issues, timeout)
                logger.error(f"Request failed for category {category} on page {page}. Error: {str(e)}")
                break  # Stop the loop on error
            except Exception as e:
                # Log any unexpected errors
                logger.error(f"Unexpected error fetching news for category {category} on page {page}. Error: {str(e)}")
                break  # Stop the loop on error

    return all_articles


def generate_news_id(article):
    """
    Generate a unique news ID based on title, description, URL, and published date.
    """
    unique_string = f"{article['title']} {article['description']} {article['url']} {article['publishedAt']}"
    return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()


def save_news_to_db(articles):
    for article in articles:
        # Generate a unique news_id for the article
        news_id = generate_news_id(article)

        # Check if the article already exists by the news_id (avoid duplicates)
        if NewsArticle.objects.filter(news_id=news_id).exists():
            logger.info(f"Duplicate article found. Skipping: {article['title']}")
            continue  # Skip inserting this article since it's a duplicate

        # Save the article to the database if it's not a duplicate
        try:
            NewsArticle.objects.create(
                news_id=news_id,
                title=article['title'],
                category=article['category'],
                description=article['description'],
                url=article['url'],
                image_url =article['urlToImage'],
                published_at=article['publishedAt'],
            )
            logger.info(f"Saved article: {article['title']}")

        except IntegrityError as e:
            # If there's any error while saving, log it
            logger.error(f"Error saving article {article['title']}: {str(e)}")