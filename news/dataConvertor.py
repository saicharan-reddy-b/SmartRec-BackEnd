import re
import faiss
import numpy as np
import logging
from .models import NewsArticle
from sentence_transformers import SentenceTransformer
import hashlib
import os
import pandas as pd
import json

# Set up logging
logger = logging.getLogger(__name__)

# Path to the stored FAISS index file
FAISS_INDEX_PATH = 'news_faiss.index'

def clean_text(text):
    """
    Clean and preprocess the given text. Convert to lowercase, strip whitespaces, and remove special characters.
    """
    if pd.isna(text):
        return ""
    text = text.lower().strip()  # Convert to lowercase and strip
    text = re.sub(r"[^a-zA-Z0-9 ]", "", text)  # Remove non-alphanumeric characters except spaces
    return text

def generate_embeddings_for_articles(articles):
    """
    Generate embeddings for a list of articles using SBERT.

    :param articles: List of articles to generate embeddings for
    :return: List of embeddings for the articles and their corresponding news IDs
    """
    model = SentenceTransformer('all-MiniLM-L6-v2')  # Load the SBERT model
    embeddings = []
    news_id_to_index = {}  # To store the mapping of news_id to FAISS index

    for idx, article in enumerate(articles):
        # Generate a unique news_id for the article
        news_id = article['news_id']

        # Clean title and description
        title = clean_text(article['title'])
        description = clean_text(article['description'])

        # Combine title and description for embedding generation
        text = title + " " + description

        # Generate embedding for the combined text
        embedding = model.encode(text)
        embeddings.append(embedding)

        # Store the mapping of news_id to FAISS index
        news_id_to_index[idx] = news_id

    # Optionally, save this mapping to disk for persistence
    with open('news_id_to_index_mapping.json', 'w') as f:
        json.dump(news_id_to_index, f)

    return embeddings, news_id_to_index

def generate_news_id(article):
    """
    Generate a unique news ID based on title, description, URL, and published date.
    """
    unique_string = f"{article['title']} {article['description']} {article['url']} {article['publishedAt']}"
    return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()

def store_embeddings_in_faiss(embeddings):
    """
    Store the embeddings in FAISS for fast similarity search.
    If the index already exists, we load the existing one instead of creating a new one.
    :param embeddings: List of embeddings to be stored in FAISS
    :return: The FAISS index object
    """
    # Check if the FAISS index already exists
    if os.path.exists(FAISS_INDEX_PATH):
        # Load the existing FAISS index
        faiss_index = faiss.read_index(FAISS_INDEX_PATH)
        logger.info("Loaded existing FAISS index.")
    else:
        # Create a new FAISS index if none exists
        embeddings_array = np.array(embeddings).astype('float32')

        # Create a FAISS index for L2 (Euclidean) distance
        faiss_index = faiss.IndexFlatL2(embeddings_array.shape[1])

        # Add embeddings to the FAISS index
        faiss_index.add(embeddings_array)

        # Save the FAISS index to the file
        faiss.write_index(faiss_index, FAISS_INDEX_PATH)
        logger.info("Created and saved a new FAISS index.")

    return faiss_index

def process_and_store_embeddings():
    """
    Main function to fetch articles, clean them, generate embeddings, and store them in FAISS.
    This function will load the existing FAISS index if it exists, otherwise, it will create a new one.
    """
    # Step 1: Fetch articles from PostgreSQL (NewsArticle table)
    articles = NewsArticle.objects.all()  # Fetch all news articles
    logger.info(f"Fetched {len(articles)} articles from PostgreSQL")

    # Step 2: Clean the data and generate embeddings
    articles_data = [{
        'title': article.title,
        'description': article.description,
        'url': article.url,
        'publishedAt': article.published_at,
        'news_id': article.news_id,
    } for article in articles]

    embeddings, news_id_to_index = generate_embeddings_for_articles(articles_data)
    logger.info(f"Generated embeddings for {len(embeddings)} articles")

    # Step 3: Store embeddings in FAISS (or load existing FAISS index)
    faiss_index = store_embeddings_in_faiss(embeddings)
    logger.info(f"FAISS index is now ready with {len(embeddings)} embeddings.")

    return faiss_index, news_id_to_index

def load_faiss_index():
    """
    Load the FAISS index from the file.
    This function ensures that the FAISS index is loaded only when needed.
    """
    try:
        faiss_index = faiss.read_index(FAISS_INDEX_PATH)
        logger.info(f"Loaded FAISS index from {FAISS_INDEX_PATH}.")
        return faiss_index
    except Exception as e:
        logger.error(f"Error loading FAISS index from {FAISS_INDEX_PATH}: {str(e)}")
        return None

def fetch_embedding_from_faiss(news_id, news_id_to_index):
    """
    Fetch the embedding of a specific news article from FAISS based on the news ID.

    :param news_id: The unique identifier for the news article
    :param news_id_to_index: The mapping of news_id to the FAISS index
    :return: The embedding of the news article or None if not found
    """
    # Ensure the news_id exists in the mapping
    if news_id not in news_id_to_index:
        logger.error(f"News article with ID {news_id} not found in FAISS index.")
        return None

    # Get the index of the news article
    index = news_id_to_index[news_id]

    # Load the FAISS index (if not loaded already)
    faiss_index = load_faiss_index()

    if faiss_index is None:
        logger.error(f"FAISS index not loaded properly. Could not fetch embedding for {news_id}.")
        return None

    # Retrieve the embedding for the article from FAISS
    embedding = faiss_index.reconstruct(index)  # Fetch the embedding for the index
    if embedding is None:
        logger.error(f"Failed to fetch embedding for news article {news_id} from FAISS.")
        return None

    return embedding