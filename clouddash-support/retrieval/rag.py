import chromadb

# Use EphemeralClient (in-memory) so the app works on platforms like Render
# where the filesystem is ephemeral. The KB is loaded fresh on every startup.
_client = chromadb.EphemeralClient()
_collection = _client.get_or_create_collection(name="clouddash_kb")

class KnowledgeBase:
    """A simple RAG pipeline using ChromaDB for retrieving knowledge base articles."""
    
    def __init__(self):
        self.client = _client
        self.collection = _collection

    def search(self, query: str, n_results: int = 3) -> list[dict]:
        """Searches ChromaDB for the most relevant articles."""
        if not self.collection:
            print("Warning: Collection is not initialized.")
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
        except Exception as e:
            print(f"Warning: KB search failed: {e}")
            return []

        # Format results into a list of dicts
        formatted_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "title": results['metadatas'][0][i].get('title', 'Unknown'),
                    "content": results['documents'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0
                })

        return formatted_results

def format_context(results: list[dict]) -> str:
    """Formats the search results into a string for the LLM prompt."""
    if not results:
        return "No relevant knowledge base articles found."
        
    context_parts = []
    for res in results:
        context_parts.append(f"[{res['id']}] {res['title']}\n{res['content']}")
        
    return "\n\n".join(context_parts)
