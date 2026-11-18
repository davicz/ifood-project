"""Run explicitly once to download the trusted multilingual embedding model."""
from app.intelligence import MODEL, CACHE
from sentence_transformers import SentenceTransformer
SentenceTransformer(MODEL, cache_folder=str(CACHE), device='cpu')
print('Modelo preparado:', MODEL)
