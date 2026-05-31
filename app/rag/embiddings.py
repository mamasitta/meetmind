from typing import List
from app.core.config import settings

# One client instance (same pattern as OpenAI)
from voyageai.client import Client
vo = Client(api_key=settings.voyage_api_key)


async def embed_text(text: str) -> List[float]:
    """
    Convert text to vector using Voyage AI
    
    Example:
        text = "Alice said the project deadline is Friday"
        vector = await embed_text(text)
        # Returns 1536 numbers representing meaning
    """
    # Voyage supports sync or async - we'll use sync for simplicity
    # For production, consider using async or threading
    result = vo.embed(
        texts=[text],
        model=settings.embedding_model,
        input_type="document"  # Important: "document" for storing, "query" for searching
    )
    
    # Apply dimension reduction if configured (save storage)
    embedding = result.embeddings[0]
    if settings.embedding_dimension and settings.embedding_dimension < len(embedding):
        # Trim to desired dimension (Matryoshka embeddings)
        embedding = embedding[:settings.embedding_dimension]
    
    return embedding


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Batch version - one API call for multiple texts
    
    Example:
        chunks = ["Alice: Hi", "Bob: Hello", "Alice: How are you?"]
        vectors = await embed_texts(chunks)
        # Returns list of 3 vectors
    """
    if not texts:
        return []
    
    # Clean and prepare texts
    cleaned_texts = [t.strip() for t in texts if t.strip()]
    
    if not cleaned_texts:
        return []
    
    # Batch embed (Voyage handles up to 128 texts per call)
    result = vo.embed(
        texts=cleaned_texts,
        model=settings.embedding_model,
        input_type="document"  # Use "document" for chunks you store
    )
    
    embeddings = result.embeddings
    
    # Apply dimension reduction if configured
    if settings.embedding_dimension and settings.embedding_dimension < len(embeddings[0]):
        embeddings = [e[:settings.embedding_dimension] for e in embeddings]
    
    return embeddings


async def embed_query(query: str) -> List[float]:
    """
    Special version for search queries
    
    IMPORTANT: Use input_type="query" for search queries!
    This optimizes retrieval quality.
    
    Example:
        user_question = "What did Alice say about the budget?"
        query_vector = await embed_query(user_question)
        # Then search against document vectors
    """
    result = vo.embed(
        texts=[query],
        model=settings.embedding_model,
        input_type="query"  # Different from "document"!
    )
    
    embedding = result.embeddings[0]
    
    if settings.embedding_dimension and settings.embedding_dimension < len(embedding):
        embedding = embedding[:settings.embedding_dimension]
    
    return embedding


async def embed_queries(queries: List[str]) -> List[List[float]]:
    """
    Batch version for multiple queries
    """
    if not queries:
        return []
    
    cleaned_queries = [q.strip() for q in queries if q.strip()]
    
    if not cleaned_queries:
        return []
    
    result = vo.embed(
        texts=cleaned_queries,
        model=settings.embedding_model,
        input_type="query"
    )
    
    embeddings = result.embeddings
    
    if settings.embedding_dimension and settings.embedding_dimension < len(embeddings[0]):
        embeddings = [e[:settings.embedding_dimension] for e in embeddings]
    
    return embeddings