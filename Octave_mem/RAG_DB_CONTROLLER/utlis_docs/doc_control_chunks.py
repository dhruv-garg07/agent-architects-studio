import os
import docx
import csv
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter

def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

    elif ext == ".pdf":
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

    elif ext == ".docx":
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])

    elif ext == ".csv":
        with open(file_path, newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            rows = [" ".join(row) for row in reader]
            text = "\n".join(rows)

    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    return text

def make_chunks(text: str, chunk_size: int = 500, overlap: int = 50):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap
    )
    return splitter.split_text(text)

def process_file(file_path: str):
    text = extract_text(file_path)
    chunks = make_chunks(text)
    return chunks

import re
from collections import Counter
from typing import List

# Basic English stopwords list (can be expanded)
STOPWORDS = {
    'the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'on', 'with', 'as', 'by',
    'an', 'at', 'from', 'this', 'that', 'it', 'be', 'are', 'was', 'were', 'or',
    'but', 'not', 'have', 'has', 'had', 'can', 'will', 'would', 'should', 'could'
}

def fast_tag_extractor(text_chunk: str, top_n: int = 3) -> str:
    """
    Quickly extracts tags from a text chunk using regex and frequency analysis.

    Args:
        text_chunk (str): The input text.
        top_n (int): Number of top tags to return.

    Returns:
        List[str]: A list of relevant tags.
    """
    # Normalize text: lowercase and remove punctuation
    text = re.sub(r'[^\w\s]', '', text_chunk.lower())

    # Tokenize and filter
    tokens = text.split()
    filtered = [word for word in tokens if word not in STOPWORDS and len(word) > 2]

    # Frequency count
    freq = Counter(filtered)

    # Return top N tags as comma-separated string
    return ', '.join([word for word, _ in freq.most_common(top_n)])
