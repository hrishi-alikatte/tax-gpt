"""Legacy RAG module.

Retained temporarily so the existing Flet app can still boot. New code paths
go through `TaxAI2025.rag.explain` and `TaxAI2025.ai.model_router`. Secrets
are loaded only via `TaxAI2025.core.config`.
"""
import os
import shutil

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

from TaxAI2025.core.config import ConfigError, groq_config, rag_index_dir


def _resolve_groq_key() -> str:
    # Lazy: fail loudly only when this legacy path is actually used.
    return groq_config().api_key


DB_PATH = str(rag_index_dir())

class TaxKnowledgeBase:
    def __init__(self):
        self.vector_store = None
        self.qa_chain = None

    def load_data(self, file_path):
        print(f"--- INGESTING DATA: {file_path} ---")
        
        if file_path.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path)
        documents = loader.load()

        # Chunking: Smaller chunks for precise tax code citation
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,       
            chunk_overlap=150,     
            separators=["\n\n", "\n", "•", " ", ""],
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)
        print(f"Created {len(chunks)} chunks.")

        # Embeddings - SWITCHED TO MULTILINGUAL (French/English)
        # Using local cache to avoid permission errors
        local_cache = os.path.join(os.getcwd(), "TaxAI2025/model_cache")
        print(f"Using HuggingFace Multilingual Embeddings (paraphrase-multilingual-MiniLM-L12-v2)...")
        embeddings = HuggingFaceEmbeddings(
            model_name="paraphrase-multilingual-MiniLM-L12-v2",
            cache_folder=local_cache
        )

        if os.path.exists(DB_PATH):
            shutil.rmtree(DB_PATH) 
            
        self.vector_store = Chroma.from_documents(
            documents=chunks, 
            embedding=embeddings,
            persist_directory=DB_PATH
        )
        print("Database ready.")
        self._setup_llm_chain()

    def _setup_llm_chain(self):
        try:
            cfg = groq_config()
        except ConfigError as e:
            raise ConfigError(
                "Legacy Groq RAG path requires GROQ_API_KEY. "
                "Prefer the new Azure-backed path in TaxAI2025.rag.explain."
            ) from e

        print("Loading Groq model (legacy path)...")
        llm = ChatGroq(
            temperature=0.1,
            groq_api_key=cfg.api_key,
            model_name=cfg.model,
        )

        # Prompt - UPGRADED to "TaxPilot Auditor" Persona
        template = """
        You are TaxPilot, an expert Tax Auditor for the Canton of Vaud, Switzerland.
        
        YOUR GOAL:
        Help the user file a COMPLETE and ACCURATE tax return. 
        
        BEHAVIOR:
        1. **Official Sources Only**: Base every answer strictly on the provided Context (Official Vaud Instructions).
        2. **Proactive Completeness**: If the user asks about a deduction (e.g., "Food"), ASK if they also meet related conditions (e.g., "Do you also eat at a canteen? This affects the rate.").
        3. **Missing Info**: If the documents don't have the answer, say "I cannot find this in your official documents. Please check the 'Guide de remplissage'."
        4. **Language**: The documents are in French. You must understand them, but ANSWER IN ENGLISH.
        
        Context (Vaud Tax Guide):
        {context}
        
        User Question: {question}
        
        Auditor Response (in English):
        """
        QA_CHAIN_PROMPT = PromptTemplate.from_template(template)

        # Chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 4}),
            chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}
        )
        print("Brain is ready!")

    def ask(self, query):
        if not self.qa_chain:
            return "⚠️ System Notice: Please upload the 'Instructions Générales' (PDF) first to initialize the knowledge base."
        try:
            print(f"Auditing: '{query}'...")
            result = self.qa_chain.invoke({"query": query})
            return result["result"]
        except Exception as e:
            return f"Error: {str(e)}"
