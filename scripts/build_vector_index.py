import os
import json
import asyncio
import numpy as np
import faiss
from app.modules.rag.embeddings import EmbeddingService
from app.config import settings

async def build_index():
    processed_dir = "knowledge_base/processed"
    chunks_file = os.path.join(processed_dir, "chunks.jsonl")
    vector_store_dir = settings.VECTOR_STORE_PATH # vector_store/faiss_index
    
    # Resolve vector_store_dir if it points to a file, we need its directory
    if vector_store_dir.endswith("faiss_index"):
        # it is the directory name
        os.makedirs(vector_store_dir, exist_ok=True)
        index_file = os.path.join(vector_store_dir, "index.faiss")
        metadata_file = os.path.join(vector_store_dir, "index_metadata.json")
    else:
        # otherwise create parent
        os.makedirs(os.path.dirname(vector_store_dir), exist_ok=True)
        index_file = f"{vector_store_dir}.faiss"
        metadata_file = f"{vector_store_dir}_metadata.json"

    print("Starting vector index construction...")
    
    if not os.path.exists(chunks_file):
        print(f"Error: Chunks file '{chunks_file}' not found. Please run ingest_kb.py first.")
        return

    # Load chunks
    chunks = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line.strip()))

    if not chunks:
        print("No chunks found in chunks.jsonl.")
        return

    print(f"Loaded {len(chunks)} chunks to embed.")

    embedding_service = EmbeddingService()
    embeddings_list = []
    metadata_list = []

    print("Generating embeddings (calling OpenAI Embedding API)...")
    for i, chunk in enumerate(chunks):
        content_to_embed = f"Tiêu đề: {chunk['title']}\nNội dung: {chunk['content']}"
        embedding = await embedding_service.get_embedding(content_to_embed)
        embeddings_list.append(embedding)
        
        # Save metadata mapping for this index
        metadata_list.append({
            "chunk_id": chunk["chunk_id"],
            "doc_id": chunk["doc_id"],
            "title": chunk["title"],
            "category": chunk["category"],
            "content": chunk["content"],
            "source_path": chunk["source_path"]
        })
        
        if (i + 1) % 5 == 0 or (i + 1) == len(chunks):
            print(f"Embedded {i + 1}/{len(chunks)} chunks.")

    # Convert to float32 numpy array
    dimension = 1536
    embeddings_np = np.array(embeddings_list).astype("float32")
    
    # Normalize embeddings L2 to perform Cosine Similarity via Inner Product search
    faiss.normalize_L2(embeddings_np)

    # Initialize IndexFlatIP
    print("Building FAISS FlatIP index...")
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_np)

    # Write out index and metadata
    faiss.write_index(index, index_file)
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, ensure_ascii=False, indent=2)

    print(f"Vector index built successfully! Saved index to '{index_file}' and metadata to '{metadata_file}'.")

if __name__ == "__main__":
    asyncio.run(build_index())
