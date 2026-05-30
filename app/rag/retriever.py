# app/rag/retriever.py
import uuid
import asyncio
from uuid import UUID
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from app.rag.embiddings import embed_text, embed_texts
from app.rag.chunker import chunk_transcript
from app.core.config import settings

# Use sync client
qdrant_client = QdrantClient(url=settings.qdrant_url)


async def store_chunks(meeting_id: UUID, transcript: str) -> int:
    """Store transcript chunks in Qdrant"""
    chunks = chunk_transcript(transcript)
    
    if not chunks:
        return 0
    
    # Generate embeddings
    embeddings = await embed_texts(chunks)
    
    # Create Qdrant points
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "meeting_id": str(meeting_id),
                "chunk_index": index,
                "content": content,
            }
        )
        for index, (content, embedding) in enumerate(zip(chunks, embeddings))
    ]
    
    # Upsert to Qdrant (this method still works)
    await asyncio.to_thread(
        qdrant_client.upsert,
        collection_name=settings.qdrant_collection,
        points=points
    )
    
    return len(points)


async def search_similar_chunks(
    query: str, 
    limit: int = 3, 
    exclude_meeting_id: UUID | None = None
) -> list[dict]:
    """Search for similar chunks using NEW query_points API"""
    # Get query embedding
    query_embedding = await embed_text(query)
    
    # Build filter
    search_filter = None
    if exclude_meeting_id:
        search_filter = Filter(
            must_not=[
                FieldCondition(
                    key="meeting_id",
                    match=MatchValue(value=str(exclude_meeting_id))
                )
            ]
        )
    
    # NEW: Use query_points instead of search [citation:1][citation:7]
    response = await asyncio.to_thread(
        qdrant_client.query_points,
        collection_name=settings.qdrant_collection,
        query=query_embedding,  # Note: 'query' not 'query_vector'
        query_filter=search_filter,  # Note: 'query_filter' not 'query_filter'
        limit=min(limit, 10),
        with_payload=True
    )
    
    # Extract results from response
    results = response.points if response else []

    return [
        {
            "meeting_id": result.payload["meeting_id"],
            "chunk_index": result.payload["chunk_index"],
            "content": result.payload["content"],
            "similarity": round(result.score, 3)
        }
        for result in results
    ]


async def delete_meeting_chunks(meeting_id: UUID) -> None:
    """Delete all chunks for a meeting"""
    await asyncio.to_thread(
        qdrant_client.delete,
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="meeting_id",
                    match=MatchValue(value=str(meeting_id))
                )
            ]
        )
    )