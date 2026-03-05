import chromadb
from typing import List, Dict

from backend.core.config import settings

class KnowledgeBase:
    """Manages document indexing and semantic search using Chroma DB."""
    
    def __init__(self, persist_directory: str = None):
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIR
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(name="system_knowledge")
        
    def add_document(self, doc_id: str, text: str, metadata: Dict = None):
        """Indexes a document after chunking (simplified for prototype)."""
        self.collection.add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[doc_id]
        )
        return {"status": "success", "doc_id": doc_id}

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Perform semantic search."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        parsed_results = []
        if results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i] if results['metadatas'] else {}
                parsed_results.append({"text": doc, "metadata": meta})
                
        return parsed_results
        
# Global knowledge base instance
system_kb = KnowledgeBase()
