"""Low-frequency LangGraph workflow for rich requests; never imported by detection."""
from __future__ import annotations

from typing import Any, TypedDict

from .context import deterministic_summary, verified_facts
from .ollama import OllamaUnavailableError, ollama_service
from .validation import validate_scene_response


class RichState(TypedDict, total=False):
    intent: str
    world_state: dict[str, Any]
    facts: dict[str, Any]
    text: str
    source: str


def _facts(state: RichState) -> RichState:
    return {"facts": verified_facts(state["world_state"])}


def _scene(state: RichState) -> RichState:
    fallback = deterministic_summary(state["world_state"])
    try:
        candidate = ollama_service.describe(state["facts"])
        validated = validate_scene_response(candidate, state["facts"])
        if validated:
            return {"text": validated, "source": "ollama"}
    except OllamaUnavailableError:
        pass
    return {"text": fallback, "source": "deterministic"}


def _fallback(state: RichState) -> RichState:
    return {"text": deterministic_summary(state["world_state"]), "source": "deterministic"}


def _route(state: RichState) -> str:
    return "scene" if state.get("intent") == "SCENE" else "fallback"


class RichWorkflow:
    def __init__(self) -> None:
        self._graph = None

    def _build(self):
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError:
            return None
        graph = StateGraph(RichState)
        graph.add_node("facts", _facts)
        graph.add_node("scene", _scene)
        graph.add_node("fallback", _fallback)
        graph.add_edge(START, "facts")
        graph.add_conditional_edges("facts", _route, {"scene": "scene", "fallback": "fallback"})
        graph.add_edge("scene", END)
        graph.add_edge("fallback", END)
        return graph.compile()

    def run(self, intent: str, world_state: dict[str, Any]) -> dict[str, str]:
        if self._graph is None:
            self._graph = self._build()
        if self._graph is None:
            return _scene({"intent": intent, "world_state": world_state, "facts": verified_facts(world_state)})
        result = self._graph.invoke({"intent": intent, "world_state": world_state})
        return {"text": result["text"], "source": result["source"]}


rich_workflow = RichWorkflow()
