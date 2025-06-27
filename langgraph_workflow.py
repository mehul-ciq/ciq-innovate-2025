# Requirements: pip install langchain langgraph openai tiktoken faiss-cpu
try:
    import langgraph
    from langgraph.graph import StateGraph, END
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_openai import ChatOpenAI
except ImportError as e:
    print("Missing dependencies. Please run: pip install langchain langgraph openai tiktoken faiss-cpu")
    raise e

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.codebase_retriever import CodebaseRetriever

# Define the state schema
from typing import TypedDict, List, Optional
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: List[BaseMessage]
    query: str
    codebase: Optional[str]  # "ccp-vap", "ccp-execute", or "both"
    retrieved_docs: List
    response: Optional[str]

class CodebaseAgent:
    def __init__(self):
        self.retriever = CodebaseRetriever()
        
        # Initialize the LLM for LangGraph
        self.llm = ChatOpenAI(
            base_url="https://ciq-litellm-proxy-service.prod-dbx.commerceiq.ai",
            api_key="sk-WRDSNGPePp-cHG5Q6WhRjA",
            model="openai/gpt-4o"
        )
        
        # Build the workflow
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("retrieve_code", self._retrieve_code_node)
        workflow.add_node("generate_response", self._generate_response_node)
        
        # Add edges
        workflow.add_edge("retrieve_code", "generate_response")
        workflow.add_edge("generate_response", END)
        
        # Set entry point
        workflow.set_entry_point("retrieve_code")
        
        return workflow.compile()
    
    def _retrieve_code_node(self, state: AgentState) -> AgentState:
        """Retrieve relevant code based on the query"""
        query = state["query"]
        codebase = state.get("codebase", "both")
        
        print(f"🔍 Retrieving code for: {query}")
        print(f"📁 Codebase: {codebase}")
        
        if codebase == "ccp-vap":
            docs = self.retriever.retrieve_from_vap(query, k=5)
        elif codebase == "ccp-execute":
            docs = self.retriever.retrieve_from_execute(query, k=5)
        else:  # both
            docs = self.retriever.retrieve_from_both(query, k=5)
        
        print(f"📄 Found {len(docs)} relevant code chunks")
        
        # Format retrieved docs for context
        context = ""
        for i, doc in enumerate(docs):
            context += f"\n--- Code Chunk {i+1} ---\n"
            context += f"Source: {doc.metadata.get('source', 'Unknown')}\n"
            context += f"Content:\n{doc.page_content}\n"
        
        state["retrieved_docs"] = docs
        
        # Add context to messages
        if context:
            context_message = f"Here is relevant code from the codebase:\n{context}\n\nPlease use this code to answer the user's question."
            state["messages"].append(HumanMessage(content=context_message))
        
        return state
    
    def _generate_response_node(self, state: AgentState) -> AgentState:
        """Generate response using the LLM with retrieved context"""
        messages = state["messages"]
        
        print("🤖 Generating response with LLM...")
        
        try:
            # Use the LLM to generate response
            response = self.llm.invoke(messages)
            state["response"] = response.content
            
            print("✅ Response generated successfully")
            
        except Exception as e:
            print(f"❌ Error generating response: {e}")
            state["response"] = f"Sorry, I encountered an error while generating the response: {str(e)}"
        
        return state
    
    def query_codebase(self, query: str, codebase: str = "both") -> str:
        """Main method to query the codebase"""
        # Initialize state
        state = AgentState(
            messages=[HumanMessage(content=query)],
            query=query,
            codebase=codebase,
            retrieved_docs=[],
            response=None
        )
        
        # Run the workflow
        result = self.workflow.invoke(state)
        
        return result["response"]

# Example usage
if __name__ == "__main__":
    agent = CodebaseAgent()
    
    # Test queries
    test_queries = [
        ("Show me the controller classes", "both"),
        ("What services are available in ccp-vap?", "ccp-vap"),
        ("How is execution handled in ccp-execute?", "ccp-execute"),
    ]
    
    for query, codebase in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Codebase: {codebase}")
        print(f"{'='*60}")
        
        response = agent.query_codebase(query, codebase)
        print(f"\nResponse:\n{response}")
        print(f"\n{'-'*60}") 