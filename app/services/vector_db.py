import chromadb
from chromadb.utils import embedding_functions
import os
import uuid

# Setup storage directory
CHROMA_DATA_PATH = os.path.join(os.getcwd(), "chroma_db")
if not os.path.exists(CHROMA_DATA_PATH):
    os.makedirs(CHROMA_DATA_PATH)

# Initialize ChromaDB Client
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

# Use a standard clinical-friendly embedding model
# Note: sentence-transformers is used as the default embedding function
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Get or create the collection
collection = client.get_or_create_collection(
    name="clinical_audit_intelligence",
    embedding_function=embedding_func,
    metadata={"hnsw:space": "cosine"}
)

def get_issue_context_string(issue_type: str, column: str, row_context: dict) -> str:
    """Creates a deterministic string for embedding based on issue context."""
    return f"Issue: {issue_type} | Column: {column} | Context: {str(row_context)}"

async def find_similar_issue(issue_type: str, column: str, row_context: dict, threshold: float = 0.9):
    """Searches for a similar issue in the vector store."""
    context_str = get_issue_context_string(issue_type, column, row_context)
    
    results = collection.query(
        query_texts=[context_str],
        n_results=1
    )
    
    if results['documents'] and results['distances']:
        # Cosine distance (lower is better, 0.0 is exact match, 2.0 is opposite)
        # Cosine similarity = 1 - distance
        similarity = 1 - results['distances'][0][0]
        
        if similarity >= threshold:
            return {
                "explanation": results['documents'][0][0],
                "similarity": similarity,
                "metadata": results['metadatas'][0][0]
            }
    
    return None

def store_explanation(issue_type: str, column: str, row_context: dict, explanation: str, edited_by: str = "AI"):
    """Saves an explanation to the vector store for future reuse."""
    context_str = get_issue_context_string(issue_type, column, row_context)
    
    # We use a combined hash or unique ID to avoid duplicates for exact same context
    doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, context_str))
    
    collection.upsert(
        ids=[doc_id],
        documents=[explanation],
        metadatas=[{
            "issue_type": issue_type,
            "column": column,
            "edited_by": edited_by
        }]
    )
    print(f"📍 [VECTOR] Stored intelligence for '{issue_type}' on '{column}' (ID: {doc_id[:8]})")
