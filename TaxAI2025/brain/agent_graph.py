"""Legacy LangGraph agent. Loads secrets via TaxAI2025.core.config only."""
import json
from typing import TypedDict, List, Dict, Any

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

from TaxAI2025.core.schema import UserProfile
from TaxAI2025.brain.rag import TaxKnowledgeBase
from TaxAI2025.core.config import groq_config


class AgentState(TypedDict):
    session_id: str
    messages: List[Dict[str, str]]
    profile: dict  # Serialized UserProfile
    next_action: str 
    reply: str
    query_to_search: str

def build_tax_agent(brain: TaxKnowledgeBase, db):
    cfg = groq_config()
    llm = ChatGroq(
        model_name=cfg.model, groq_api_key=cfg.api_key, temperature=0
    ).with_structured_output(UserProfile)
    standard_llm = ChatGroq(
        model_name=cfg.model, groq_api_key=cfg.api_key, temperature=0
    )

    def extract_profile(state: AgentState):
        """Extracts facts from the latest user message and updates the profile."""
        print("--- [Agent] Extracting Profile ---")
        user_msg = state["messages"][-1]["content"] if state["messages"] else ""
        current_profile = UserProfile(**state["profile"])
        
        # We prompt the LLM to update the profile given the new message
        prompt = f"Current Profile: {current_profile.model_dump_json()}\nNew Message: {user_msg}\nUpdate the profile with any new information found."
        
        # We use a simple prompt rather than full instructions for extraction
        updated_profile_data = llm.invoke(prompt)
        
        if updated_profile_data:
            # Merge fields
            for k, v in updated_profile_data.model_dump().items():
                if v is not None:
                    setattr(current_profile, k, v)
        
        # Save to DB
        db.save_user_profile(state["session_id"], current_profile.model_dump())
        state["profile"] = current_profile.model_dump()
        return state

    def completeness_check(state: AgentState):
        """Checks if there is missing critical info to ask about."""
        print("--- [Agent] Checking Completeness ---")
        current_profile = UserProfile(**state["profile"])
        missing = current_profile.get_missing_critical_fields()
        
        if missing:
             state["next_action"] = "ask_proactive"
             state["query_to_search"] = missing[0]
        else:
             state["next_action"] = "answer_question"
             state["query_to_search"] = state["messages"][-1]["content"] if state["messages"] else ""
        
        return state

    def ask_proactive(state: AgentState):
        """Asks a proactive question based on missing fields."""
        print("--- [Agent] Asking Proactive Question ---")
        missing_field = state["query_to_search"]
        
        prompt = f"""
        You are a professional Vaud Tax Accountant. 
        You noticed we are missing a critical piece of information: '{missing_field}'.
        Politely ask the user to provide this information.
        Be professional, conversational, and explain why we need it for their taxes.
        """
        response = standard_llm.invoke(prompt)
        state["reply"] = response.content
        return state

    def retrieve_and_answer(state: AgentState):
        """Standard RAG to answer the user's question, injecting the current profile."""
        print("--- [Agent] Retrieving & Answering ---")
        query = state["query_to_search"]
        current_profile = UserProfile(**state["profile"])
        
        # Force retrieve context 
        if brain and brain.vector_store:
            docs = brain.vector_store.similarity_search(query, k=3)
            context = "\n".join([d.page_content for d in docs])
        else:
            context = "No knowledge base loaded."
            
        prompt = f"""
        You are a specialized Vaud Tax Expert.
        
        Context from Vaud Tax Guide:
        {context}
        
        User's Known Profile:
        {current_profile.model_dump_json()}
        
        User's Question: {query}
        
        Answer professionally in English, directly referencing the Vaud context provided.
        """
        response = standard_llm.invoke(prompt)
        state["reply"] = response.content
        return state

    def update_history(state: AgentState):
        """Adds the final reply to the message history."""
        reply = state["reply"]
        state["messages"].append({"role": "assistant", "content": reply})
        # Note: the caller will save this to the database
        return state

    # Build Graph
    workflow = StateGraph(AgentState)
    
    workflow.add_node("extract", extract_profile)
    workflow.add_node("evaluate", completeness_check)
    workflow.add_node("ask_proactive", ask_proactive)
    workflow.add_node("retrieve_and_answer", retrieve_and_answer)
    workflow.add_node("update", update_history)
    
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "evaluate")
    
    # Conditional logic
    workflow.add_conditional_edges(
        "evaluate",
        lambda x: x["next_action"],
        {
            "ask_proactive": "ask_proactive",
            "answer_question": "retrieve_and_answer"
        }
    )
    
    workflow.add_edge("ask_proactive", "update")
    workflow.add_edge("retrieve_and_answer", "update")
    workflow.add_edge("update", END)
    
    return workflow.compile()
