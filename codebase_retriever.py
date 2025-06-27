# Requirements: pip install langchain langgraph openai tiktoken faiss-cpu
try:
    from langchain_community.embeddings import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
except ImportError as e:
    print("Missing dependencies. Please run: pip install langchain langgraph openai tiktoken faiss-cpu")
    raise e

import os

class CodebaseRetriever:
    def __init__(self):
        # Initialize embeddings with the same configuration
        self.embeddings = OpenAIEmbeddings(
            openai_api_key="sk-WRDSNGPePp-cHG5Q6WhRjA",
            openai_api_base="https://ciq-litellm-proxy-service.prod-dbx.commerceiq.ai",
            model="openai/text-embedding-3-small"
        )
        
        # Load vectorstores for both codebases
        self.vap_vectorstore = None
        self.execute_vectorstore = None
        self._load_vectorstores()
    
    def _load_vectorstores(self):
        """Load the FAISS vectorstores for both codebases"""
        try:
            if os.path.exists("ccp-vap_vectorstore"):
                self.vap_vectorstore = FAISS.load_local("ccp-vap_vectorstore", self.embeddings, allow_dangerous_deserialization=True)
                print("✅ Loaded ccp-vap vectorstore")
            else:
                print("❌ ccp-vap vectorstore not found. Run codebase_embedder.py first.")
                
            if os.path.exists("ccp-execute_vectorstore"):
                self.execute_vectorstore = FAISS.load_local("ccp-execute_vectorstore", self.embeddings, allow_dangerous_deserialization=True)
                print("✅ Loaded ccp-execute vectorstore")
            else:
                print("❌ ccp-execute vectorstore not found. Run codebase_embedder.py first.")
        except Exception as e:
            print(f"Error loading vectorstores: {e}")
    
    def retrieve_from_vap(self, query: str, k: int = 5):
        """Retrieve relevant code chunks from ccp-vap codebase"""
        if not self.vap_vectorstore:
            return []
        try:
            docs = self.vap_vectorstore.similarity_search(query, k=k)
            return docs
        except Exception as e:
            print(f"Error retrieving from ccp-vap: {e}")
            return []
    
    def retrieve_from_execute(self, query: str, k: int = 5):
        """Retrieve relevant code chunks from ccp-execute codebase"""
        if not self.execute_vectorstore:
            return []
        try:
            docs = self.execute_vectorstore.similarity_search(query, k=k)
            return docs
        except Exception as e:
            print(f"Error retrieving from ccp-execute: {e}")
            return []
    
    def retrieve_from_both(self, query: str, k: int = 5):
        """Retrieve relevant code chunks from both codebases"""
        vap_docs = self.retrieve_from_vap(query, k=k//2)
        execute_docs = self.retrieve_from_execute(query, k=k//2)
        return vap_docs + execute_docs
    
    def get_retriever_for_codebase(self, codebase: str):
        """Get a retriever object for a specific codebase"""
        if codebase == "ccp-vap":
            return self.vap_vectorstore.as_retriever() if self.vap_vectorstore else None
        elif codebase == "ccp-execute":
            return self.execute_vectorstore.as_retriever() if self.execute_vectorstore else None
        else:
            print(f"Unknown codebase: {codebase}")
            return None

# Example usage
if __name__ == "__main__":
    retriever = CodebaseRetriever()
    
    # Test retrieval
    query = "controller class"
    print(f"\nSearching for: {query}")
    
    print("\n--- Results from ccp-vap ---")
    vap_results = retriever.retrieve_from_vap(query, k=3)
    for i, doc in enumerate(vap_results):
        print(f"{i+1}. Source: {doc.metadata.get('source', 'Unknown')}")
        print(f"   Content: {doc.page_content[:200]}...")
    
    print("\n--- Results from ccp-execute ---")
    execute_results = retriever.retrieve_from_execute(query, k=3)
    for i, doc in enumerate(execute_results):
        print(f"{i+1}. Source: {doc.metadata.get('source', 'Unknown')}")
        print(f"   Content: {doc.page_content[:200]}...") 