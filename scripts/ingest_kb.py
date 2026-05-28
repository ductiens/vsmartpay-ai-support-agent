import os
import json
import re

def parse_markdown_file(filepath: str) -> list:
    chunks = []
    filename = os.path.basename(filepath)
    doc_id = os.path.splitext(filename)[0]
    
    # Map doc_id to user-friendly category name
    category_map = {
        "faq": "FAQ",
        "fees": "Fees",
        "limits": "Limits",
        "terms": "Terms & Privacy",
        "troubleshooting": "Troubleshooting"
    }
    category = category_map.get(doc_id, "General")

    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return chunks

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_title = "Giới thiệu"
    current_content_lines = []
    chunk_index = 0

    for line in lines:
        stripped_line = line.strip()
        
        # Detect Heading 1 (Document Title)
        if stripped_line.startswith("# ") and not stripped_line.startswith("## "):
            # If there's an active chunk, save it first
            if current_content_lines:
                content = "".join(current_content_lines).strip()
                if content:
                    chunk_id = f"{doc_id}_{chunk_index}"
                    chunks.append({
                        "chunk_id": chunk_id,
                        "doc_id": doc_id,
                        "title": current_title,
                        "category": category,
                        "content": content,
                        "source_path": f"knowledge_base/raw/{filename}"
                    })
                    chunk_index += 1
                current_content_lines = []
            
            # Heading 1 can be used to set document category or introduction title
            doc_title = stripped_line.replace("# ", "").strip()
            current_title = f"Giới thiệu về {doc_title}"
            continue

        # Detect Heading 2 (Semantic Sections)
        if stripped_line.startswith("## "):
            # Save the previous chunk
            content = "".join(current_content_lines).strip()
            if content:
                chunk_id = f"{doc_id}_{chunk_index}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "title": current_title,
                    "category": category,
                    "content": content,
                    "source_path": f"knowledge_base/raw/{filename}"
                })
                chunk_index += 1
            
            # Start new chunk
            current_title = stripped_line.replace("## ", "").strip()
            current_content_lines = []
            continue

        # Accumulate lines for current chunk
        current_content_lines.append(line)

    # Save the last chunk of the file
    content = "".join(current_content_lines).strip()
    if content:
        chunk_id = f"{doc_id}_{chunk_index}"
        chunks.append({
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "title": current_title,
            "category": category,
            "content": content,
            "source_path": f"knowledge_base/raw/{filename}"
        })

    return chunks

def ingest_kb():
    raw_dir = "knowledge_base/raw"
    processed_dir = "knowledge_base/processed"
    output_file = os.path.join(processed_dir, "chunks.jsonl")

    os.makedirs(processed_dir, exist_ok=True)
    all_chunks = []

    print("Starting knowledge base ingestion...")
    
    if not os.path.exists(raw_dir):
        print(f"Error: Raw directory '{raw_dir}' does not exist.")
        return

    files = [f for f in os.listdir(raw_dir) if f.endswith(".md")]
    print(f"Found {len(files)} markdown documents in raw folder: {files}")

    for file in files:
        filepath = os.path.join(raw_dir, file)
        file_chunks = parse_markdown_file(filepath)
        all_chunks.extend(file_chunks)
        print(f"Successfully parsed {file}: generated {len(file_chunks)} chunks.")

    # Write out chunks as JSON lines
    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Ingestion pipeline completed successfully! Written {len(all_chunks)} chunks to '{output_file}'.")

if __name__ == "__main__":
    ingest_kb()
