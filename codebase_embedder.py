# Requirements: pip install langchain langgraph openai tiktoken faiss-cpu
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.embeddings import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
except ImportError as e:
    print("Missing dependencies. Please run: pip install langchain langgraph openai tiktoken faiss-cpu")
    raise e

import os

CODEBASES = {
    "ccp-vap": "/Users/pratyushsingh/Public/github/ccp-vap",
    "ccp-execute": "/Users/pratyushsingh/Public/github/ccp-execute"
}
EXTS = ('.java', '.md', '.txt')
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

def load_code_files(root_dir, exts=EXTS):
    docs, metadatas = [], []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname.endswith(exts):
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        docs.append(f.read())
                        metadatas.append({"source": fpath})
                except Exception as e:
                    print(f"Error reading {fpath}: {e}")
    return docs, metadatas

def embed_codebase(name, path):
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    # Use the same configuration as in openai_connect.py with allowed embedding model
    embeddings = OpenAIEmbeddings(
        openai_api_key="sk-WRDSNGPePp-cHG5Q6WhRjA",
        openai_api_base="https://ciq-litellm-proxy-service.prod-dbx.commerceiq.ai",
        model="openai/text-embedding-3-small"  # Use full model name from allowed list
    )
    docs, metadatas = load_code_files(path)
    chunks, chunk_metas = [], []
    for doc, meta in zip(docs, metadatas):
        for chunk in splitter.split_text(doc):
            chunks.append(chunk)
            chunk_metas.append(meta)
    print(f"Embedding {len(chunks)} chunks for {name}...")
    vectorstore = FAISS.from_texts(chunks, embeddings, metadatas=chunk_metas)
    vectorstore.save_local(f"{name}_vectorstore")
    print(f"Saved {name}_vectorstore")

if __name__ == "__main__":
    for name, path in CODEBASES.items():
        print(f"Processing {name}...")
        embed_codebase(name, path) 