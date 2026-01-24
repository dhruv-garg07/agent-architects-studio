import re
from collections import Counter
from typing import List
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Download NLTK resources (only needed once)
nltk.download('punkt')
nltk.download('stopwords')

def generate_tags(text_chunk: str, top_n: int = 5) -> List[str]:
    """
    Extracts semantic tags from a given text chunk using keyword frequency and filtering.

    Args:
        text_chunk (str): The input text chunk.
        top_n (int): Number of top tags to return.

    Returns:
        List[str]: A list of relevant tags.
    """
    # Normalize and tokenize
    text = text_chunk.lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    tokens = word_tokenize(text)

    # Remove stopwords and short tokens
    stop_words = set(stopwords.words('english'))
    filtered_tokens = [word for word in tokens if word not in stop_words and len(word) > 2]

    # Count frequency
    freq_dist = Counter(filtered_tokens)

    # Return top N keywords as tags
    tags = [word for word, _ in freq_dist.most_common(top_n)]
    return tags