from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings

# one async client instance — imported wherever Qdrant is needed
qdrant = AsyncQdrantClient(url=settings.qdrant_url)

# voyage vector size for voyage-3
VECTOR_SIZE = 1024


async def ensure_collection_exists() -> None:
    # creates the collection if it doesn't exist yet
    # safe to call on every startup — does nothing if already exists
    collections = await qdrant.get_collections()
    names = [c.name for c in collections.collections]

    if settings.qdrant_collection not in names:
        await qdrant.create_collection(
            collection_name = settings.qdrant_collection,
            vectors_config  = VectorParams(
                size     = VECTOR_SIZE,
                distance = Distance.COSINE   # cosine similarity for text
            )
        )
        print(f"  [qdrant] created collection '{settings.qdrant_collection}'")
    else:
        print(f"  [qdrant] collection '{settings.qdrant_collection}' ready")