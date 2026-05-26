from crewai import LLM
from dotenv import load_dotenv
import os

load_dotenv()

llm = LLM(
    model="ollama/llama3.1",
    base_url="http://localhost:11434" 
)
