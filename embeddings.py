"""Voyage AI embeddings."""
import os
from functools import cache

import voyageai
from dotenv import load_dotenv

load_dotenv()

MODEL = "voyage-3.5"  # 1024 dimensions; the M2 vector index must use 1024 too
DIMENSIONS = 1024


@cache
def _client():
    return voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))


def embed(text, input_type="document"):
    """Turn text into a list of 1024 numbers. Use input_type="query" for search text."""
    return _client().embed([text], model=MODEL, input_type=input_type).embeddings[0]
