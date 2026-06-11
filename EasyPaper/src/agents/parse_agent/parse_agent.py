from langchain_core.messages import AnyMessage
from ..shared.llm_client import LLMClient
from typing_extensions import TypedDict, Annotated, Optional, IO
from langgraph.graph import StateGraph, START, END
import asyncio
import operator
from pathlib import Path
import json
from typing import TYPE_CHECKING, List, Dict, Any
from ...config.schema import ModelConfig
from ..base import BaseAgent
from .parse_helpers import extract_bytes_text, extract_pdf_text

if TYPE_CHECKING:
    from fastapi import APIRouter


UNDERSTAND_PROMPT = """You are a helpful assistant that helps to understand paper.
User will provide you the raw contents of the paper within a <paper> tag.
Please use critical thinking to understand the paper and provide a summary of the paper.

Please summarize the paper from following aspects:
- Summary (str): a brief summary of the paper
- Research Background (str): the background of the research
- Research Question (str): the question of the research
- Research Hypothesis (list[str]): the hypothesis of the research
- Methods (list[str]): the methods of the research
- Results (list[str]): the results of the research
- Key Findings (list[str]): the key findings of the research

Please output in JSON format.
{
    "summary": "...",
    "research_background": "...",
    "research_question": "...",
    "research_hypothesis": [...],
    "methods": [...],
    "results": [...],
    "key_findings": [...],
}
"""

MAX_RETRIES = 3
RETRY_BASE_WAIT = 3


class ParseAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    file_path: Optional[str] = None
    file_content: Optional[IO[bytes]] = None
    paper_text: Optional[str] = None
    understand_result: Optional[dict] = None
    llm_calls: int

class ParseAgent(BaseAgent):
    def __init__(self, config: ModelConfig):
        self.client = LLMClient(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.model_name = config.model_name
        self.agent = self.init_agent()

    _extract_pdf_text = staticmethod(extract_pdf_text)
    _extract_bytes_text = staticmethod(extract_bytes_text)

    def init_agent(self):
        agent_builder = StateGraph(ParseAgentState)
        agent_builder.add_node("extract_text", self.extract_text)
        agent_builder.add_node("understand_paper", self.understand_paper)
        agent_builder.add_edge(START, "extract_text")
        agent_builder.add_edge("extract_text", "understand_paper")
        agent_builder.add_edge("understand_paper", END)
        return agent_builder.compile()

    async def extract_text(self, state: ParseAgentState):
        """Extract text from PDF locally using PyMuPDF instead of remote Files API."""
        print(f"INPUT STATE [extract_text]: file_path={state.get('file_path')}, "
              f"has_content={state.get('file_content') is not None}")

        if state.get("file_path"):
            text = extract_pdf_text(state["file_path"])
        elif state.get("file_content"):
            text = extract_bytes_text(state["file_content"])
        else:
            raise ValueError("Either file_path or file_content must be provided")

        print(f"[extract_text] Extracted {len(text)} chars from PDF")
        return {"paper_text": text}

    async def understand_paper(self, state: ParseAgentState):
        """
        Understand the paper by sending extracted text to the LLM.
        - **Description**:
            - Retries up to MAX_RETRIES times with exponential backoff on
              transient server errors (busy, 429, 5xx).
        """
        paper_text = state.get("paper_text")
        if not paper_text:
            raise ValueError("No paper text available for analysis")

        print(f"INPUT STATE [understand_paper]: text_len={len(paper_text)}")

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": UNDERSTAND_PROMPT},
                        {"role": "user", "content": f"<paper>{paper_text}</paper>"}
                    ],
                    response_format={'type': 'json_object'}
                )
                return {
                    "understand_result": json.loads(response.choices[0].message.content)
                }
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                is_transient = any(k in err_str for k in ("busy", "retry", "429", "500", "502", "503", "overloaded"))
                if is_transient and attempt < MAX_RETRIES:
                    wait = RETRY_BASE_WAIT * (2 ** (attempt - 1))
                    print(f"[understand_paper] Transient error (attempt {attempt}/{MAX_RETRIES}), "
                          f"retrying in {wait}s: {e}")
                    await asyncio.sleep(wait)
                    continue
                raise

        raise last_error  # type: ignore[misc]

    async def run(self, file_path: Optional[str] = None, file_content: Optional[IO[bytes]] = None):
        """Run the agent"""
        return await self.agent.ainvoke({
            "file_path": file_path,
            "file_content": file_content,
        })

    @property
    def name(self) -> str:
        """Agent name identifier"""
        return "paper_parser"

    @property
    def description(self) -> str:
        """Agent description"""
        return "Research paper understanding and parsing agent"

    @property
    def router(self) -> "APIRouter":
        """Return the FastAPI router for this agent"""
        from .router import create_parse_router
        return create_parse_router(self)

    @property
    def endpoints_info(self) -> List[Dict[str, Any]]:
        """Return endpoint metadata for list_agents"""
        return [
            {
                "path": "/agent/parse",
                "method": "POST",
                "description": "Parse research paper and extract structured information",
                "input_model": "ParsePayload",
                "output_model": "ParseResult"
            }
        ]
