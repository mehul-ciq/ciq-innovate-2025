from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent.orchestrator import AgentOrchestrator
from knowledge_base.retriever import KnowledgeBaseRetriever
from knowledge_base.loader import KnowledgeBaseLoader
from llm.openai_client import LLMClient
from agent.langgraph_workflow import CodebaseAgent

app = FastAPI()

# Initialize and load knowledge base
kb_loader = KnowledgeBaseLoader()
kb_loader.load_from_directory("knowledge")  # expects a 'knowledge' directory with .txt/.md files
knowledge_base = KnowledgeBaseRetriever(loader=kb_loader)
llm_client = LLMClient()
agent = AgentOrchestrator(knowledge_base, llm_client)

# Initialize codebase agent
codebase_agent = CodebaseAgent()

class ChatRequest(BaseModel):
    prompt: str

class CodebaseQueryRequest(BaseModel):
    query: str
    codebase: str = "both"  # "ccp-vap", "ccp-execute", or "both"

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        response = agent.handle_prompt(request.prompt)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/codebase-query")
async def query_codebase(request: CodebaseQueryRequest):
    try:
        response = codebase_agent.query_codebase(request.query, request.codebase)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "AI Agent API is running!"} 