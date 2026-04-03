import os

ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_USER = os.getenv("ES_USER", "elastic")
ES_PASSWORD = os.getenv("ES_PASSWORD", "changeme")
ES_INDEX_NAME = os.getenv("ES_INDEX_NAME", "image_index")
ES_SYNONYM_INDEX = os.getenv("ES_SYNONYM_INDEX", "synonym_index")

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

SEARCH_DEFAULT_SIZE = 20
SEARCH_MAX_SIZE = 100
SEARCH_P99_LATENCY_MS = 100
