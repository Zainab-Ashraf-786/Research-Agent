from pathlib import Path
from typing import List, Union
from agent.config import LLMConfig
from agent.llm import LLMSession, generate_json

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "planner.txt"

def plan_queries(question: str, runner: Union[LLMConfig, LLMSession]) -> List[str]:
    """
    Stage 1: Generates 3 to 5 search queries covering distinct angles.
    Consumes exactly 1 LLM call.
    """
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    prompt = template.format(question=question.strip())
    
    if isinstance(runner, LLMSession):
        data = runner.generate_json(prompt, system="You are a professional query planner. Return valid JSON only.")
    else:
        data = generate_json(prompt, runner, system="You are a professional query planner. Return valid JSON only.")

    queries = []
    if isinstance(data, dict) and "queries" in data and isinstance(data["queries"], list):
        queries = [str(q).strip() for q in data["queries"] if str(q).strip()]
    elif isinstance(data, list):
        queries = [str(q).strip() for q in data if str(q).strip()]

    # Guarantee at least 1 query, maximum 5
    if not queries:
        queries = [question.strip()]
    return queries[:5]
