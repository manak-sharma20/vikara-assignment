import os
import json
from retrieval.rag import _collection

def ingest_articles(collection=None):
    """Reads JSON articles and loads them into a ChromaDB collection."""
    if collection is None:
        collection = _collection

    # Support running from repo root or from within the package
    articles_dir = "knowledge_base/articles"
    if not os.path.exists(articles_dir):
        articles_dir = "articles"
    documents, ids, metadatas = [], [], []
    
    # Read each JSON file in the articles directory
    for filename in os.listdir(articles_dir):
        if not filename.endswith(".json"):
            continue
            
        with open(os.path.join(articles_dir, filename), "r") as f:
            article = json.load(f)
            
        # Combine title and content
        combined_text = f"{article['title']}\n\n{article['content']}"
        
        documents.append(combined_text)
        ids.append(article["id"])
        metadatas.append({
            "title": article["title"],
            "category": article["category"]
        })
        
    # Store articles in ChromaDB
    if documents:
        collection.upsert(documents=documents, ids=ids, metadatas=metadatas)
        print(f"Loaded {len(documents)} articles into ChromaDB.")
    else:
        print("No articles found to ingest.")

if __name__ == "__main__":
    ingest_articles()
