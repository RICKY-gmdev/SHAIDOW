#agent.py
import os
from typing import Dict, Any, Optional, Sequence, Annotated
from typing_extensions import TypedDict
from functools import partial
from langchain_core.messages import (
    ToolMessage,
    SystemMessage,
    BaseMessage,
    AIMessage,
    AnyMessage,
)
from langgraph.graph.message import add_messages
from pydantic import SecretStr
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from tools import all_tools

agent_model: Optional[ChatGroq] = None
agent_with_tools = None
tool_node = ToolNode(all_tools)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def initialize_agent():
    global agent_model, agent_with_tools

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is required.")

    agent_model = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0.2,
        api_key=SecretStr(groq_api_key),
    )
    agent_with_tools = agent_model.bind_tools(all_tools)
    return agent_model


def _ensure_system_first(messages: Sequence[AnyMessage], system_prompt: str) -> Sequence[BaseMessage]:
    if not messages or not isinstance(messages[0], SystemMessage):
        return [SystemMessage(content=system_prompt.strip())] + list(messages)  # type: ignore
    return messages  # type: ignore


def router(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    The router makes exactly ONE decision: answer directly, or delegate to
    exactly one specialist tool. It never runs a second time for the same
    turn - the tool's result (once sanitized) IS the final answer. This is
    the core fix: no reinterpretation loop, no risk of the graph looping
    forever if a tool errors or the model gets indecisive.
    """
    if agent_with_tools is None or agent_model is None:
        raise RuntimeError("Agent not initialized. Call initialize_agent() first.")

    system_prompt = config["configurable"].get("system_prompt", "You are a helpful assistant.")
    messages = _ensure_system_first(state["messages"], system_prompt)

    try:
        response = agent_with_tools.invoke(messages)
    except Exception as e:
        print(f"--- Router tool-call generation failed, answering directly: {e} ---")
        response = agent_model.invoke(messages)

    return {"messages": [response]}


def route_decision(state: AgentState) -> str:
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []
    if isinstance(last_message, AIMessage) and tool_calls:
        return "tools"
    return END


def finalize(state: AgentState) -> Dict[str, Any]:
    """
    Combines every tool result from this turn into the final answer. The
    router can legitimately call more than one tool in parallel (e.g. a
    summary + an image, per the system prompt's own worked example), so we
    walk backward collecting every consecutive ToolMessage - not just the
    last one - or a multi-tool turn would silently lose all but one result.
    """
    messages = state["messages"]

    tool_messages = []
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            tool_messages.append(msg)
        else:
            break
    tool_messages.reverse()  # restore original call order

    cleaned_parts = []
    for tm in tool_messages:
        content = tm.content if isinstance(tm.content, str) else str(tm.content)
        if content.startswith("IMAGE_DATA::"):
            cleaned_parts.append("[Image was generated successfully and displayed below.]")
        elif content.startswith("IMAGE_URL::"):
            # The raw URL is already captured separately by the frontend's
            # tool_end handler and rendered as an image bubble - showing it
            # again as plain text here would just be noise.
            cleaned_parts.append("[Image found and displayed below.]")
        else:
            cleaned_parts.append(content)

    final_text = "\n\n".join(cleaned_parts) if cleaned_parts else "Sorry, I couldn't get a proper answer from that tool."
    return {"messages": [AIMessage(content=final_text)]}


def create_agent_graph(system_prompt: str):
    workflow = StateGraph(AgentState)
    router_node = partial(router, config={"configurable": {"system_prompt": system_prompt}})

    workflow.add_node("router", router_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("finalize", finalize)

    workflow.set_entry_point("router")
    workflow.add_conditional_edges("router", route_decision, {"tools": "tools", END: END})
    workflow.add_edge("tools", "finalize")
    workflow.add_edge("finalize", END)  # <- no loop back. This is the whole fix.

    return workflow.compile()