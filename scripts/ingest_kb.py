# Script to ingest raw knowledge base files
import os

def ingest_knowledge():
    raw_dir = "knowledge_base/raw"
    processed_dir = "knowledge_base/processed"
    print("Starting knowledge ingestion...")
    if os.path.exists(raw_dir):
        files = os.listdir(raw_dir)
        print(f"Found raw files: {files}")
        # In actual phase, parsing and cleaning logic will be added here
        print("Ingestion complete.")
    else:
        print("Raw directory not found.")

if __name__ == "__main__":
    ingest_knowledge()
