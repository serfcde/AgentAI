from crewai import LLM
from dotenv import load_dotenv
import os

load_dotenv()

llm = LLM(
    model=f"ollama/{os.getenv('OLLAMA_MODEL', 'llama3.1')}",
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)
