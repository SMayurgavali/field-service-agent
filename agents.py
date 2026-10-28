import os
from dotenv import load_dotenv
from crewai import Agent, LLM
from inventory_tool import check_inventory_tool

load_dotenv(override=True)


def create_gemini_llm():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Check your .env file."
        )

    return LLM(
        model = "gemini/gemini-3.6-flash",
        api_key = api_key,
        temperature = 0.2,
    )

def create_triage_agent():

    """Agent 1 : Diagnose the machine complaint """
    
    
    return Agent(
        role="Senior Field Triage Specialist",
        goal=( 
            "Analyze machine failure complaints and identify "
            "a possible root cause and recommend the primary spare part."
        ),
        backstory=(
            "You are an industrial maintenance assistant. "
            "Avoid unsupported diagnoses and clearly state uncertainty."
        ),
        llm=create_gemini_llm(),
        verbose=True,
        allow_delegation=False,
    )



def create_inventory_agent():
    """Agent 2 : Verify soarse-part inventory"""

    return Agent(
        role="Warehouse Inventory Specialist",
        goal=(
            "Identify the required spare part required by the diagnosis "
            "and verify its stock and warehouse location."
        ),
        backstory=(
            "You manage warehouse inventory. "
            "Use the inventory tool to verify stock. "
            "Never invent stock quantities ,part ID's or warehouse locations."
        ),
        llm=create_gemini_llm(),
        tools=[check_inventory_tool],
        verbose=True,
        allow_delegation=False,
    )