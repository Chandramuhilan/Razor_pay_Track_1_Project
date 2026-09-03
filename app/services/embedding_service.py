import os
import json
import hashlib
import math
import logging
from typing import List, Dict

from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self._client = None
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
        
        self.CACHE_FILE = 'app/data/embedding_cache.json'
        self._cache: Dict[str, List[float]] = {}
        self._load_cache()

    def _load_cache(self):
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r') as f:
                    self._cache = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load embedding cache: {e}")
            self._cache = {}

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"Could not save embedding cache: {e}")

    def embed_text(self, text: str) -> List[float]:
        if not self._client:
            return []
        
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        if text_hash in self._cache:
            return self._cache[text_hash]
        
        try:
            result = self._client.models.embed_content(
                model='text-embedding-004',
                contents=[text]
            )
            embedding = result.embeddings[0].values
            self._cache[text_hash] = embedding
            self._save_cache()
            return embedding
        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            return []

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self._client:
            return [[] for _ in texts]
            
        embeddings = []
        texts_to_embed = []
        indices_to_embed = []
        
        for i, text in enumerate(texts):
            text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
            if text_hash in self._cache:
                embeddings.append(self._cache[text_hash])
            else:
                embeddings.append([]) # placeholder
                texts_to_embed.append(text)
                indices_to_embed.append(i)
                
        if texts_to_embed:
            try:
                result = self._client.models.embed_content(
                    model='text-embedding-004',
                    contents=texts_to_embed
                )
                for i, text in enumerate(texts_to_embed):
                    orig_idx = indices_to_embed[i]
                    emb = result.embeddings[i].values
                    embeddings[orig_idx] = emb
                    
                    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                    self._cache[text_hash] = emb
                self._save_cache()
            except Exception as e:
                logger.error(f"Error in batch embedding: {e}")
                
        return embeddings

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def is_available(self) -> bool:
        return bool(self._client)

embedding_service = EmbeddingService()
