# agent.py
import os
from typing import Dict, Any, Optional, Sequence, Annotated
from typing_extensions import TypedDict
from functools import partial
from langchain_core.messages import (
    ToolMessage,
    SystemMessage,
    HumanMessage,
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

ROUTER_INSTRUCTION = """You are SHAIDOW's Orchestrator Core, created by Ricky (Md Ayman Iqbal).
Your job is to inspect the conversation and route the user's request to the right specialist tool(s):
1. Call `coding_tool` for ANY code, debugging, software architecture, .NET/C#, Python, SQL, or algorithm request.
2. Call `reasoning_tool` for complex analysis, logic puzzles, math, strategy, or deep multi-step questions.
3. Call `mistral_tool` for quick facts, summaries, definitions, or real-world topics.
4. Call `search_for_image_tool` when the user asks to see a real photo OR when a real photo enriches a factual topic.
5. Call `generate_image_tool` when the user asks to create, draw, or generate custom AI art/illustrations.
   - You MAY call multiple tools in parallel (e.g., `mistral_tool` + `search_for_image_tool`).
   - Always pass a self-contained, detailed `query` (include relevant context from earlier messages so the specialist tool has everything it needs).
   - ONLY reply directly without tools if the user is just greeting you, chatting casually, or asking about your identity as SHAIDOW."""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def initialize_agent():
    global agent_model, agent_with_tools

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is required.")

    # llama-3.3-70b-versatile or openai/gpt-oss-20b
    agent_model = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        api_key=SecretStr(groq_api_key),
    )
    agent_with_tools = agent_model.bind_tools(all_tools)
    return agent_model


def _replace_system_prompt(messages: Sequence[AnyMessage], prompt: str) -> list[BaseMessage]:
    filtered = [m for m in messages if not isinstance(m, SystemMessage)]
    return [SystemMessage(content=prompt.strip())] + list(filtered)


async def router(state: AgentState, config: dict) -> Dict[str, Any]:
    if agent_with_tools is None or agent_model is None:
        raise RuntimeError("Agent not initialized. Call initialize_agent() first.")

    persona_prompt = config["configurable"].get("system_prompt", "")
    combined_router_prompt = f"{ROUTER_INSTRUCTION}\n\n---\n{persona_prompt}"
    messages = _replace_system_prompt(state["messages"], combined_router_prompt)

    try:
        response = await agent_with_tools.ainvoke(messages)
    except Exception as e:
        print(f"--- Router tool-call failed, falling back to direct model: {e} ---")
        response = await agent_model.ainvoke(messages)

    return {"messages": [response]}


def route_decision(state: AgentState) -> str:
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []
    if isinstance(last_message, AIMessage) and tool_calls:
        return "tools"
    return END


async def finalize(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Synthesizes specialist tool outputs into SHAIDOW's persona using `agent_model`
    (with NO tools bound, guaranteeing zero possibility of an infinite loop).
    """
    if agent_model is None:
        raise RuntimeError("Agent not initialized.")

    messages = state["messages"]
    tool_messages: list[ToolMessage] = []
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            tool_messages.append(msg)
        else:
            break
    tool_messages.reverse()

    specialist_outputs = []
    image_notices = []

    for tm in tool_messages:
        content = tm.content if isinstance(tm.content, str) else str(tm.content)
        if content.startswith("IMAGE_DATA::") or content.startswith("IMAGE_URL::"):
            image_notices.append("[Visual asset successfully retrieved/generated and attached below.]")
        else:
            specialist_outputs.append(f"### Specialist Output ({tm.name}):\n{content}")

    # If the user ONLY asked for an image and nothing else, return a clean confirmation
    if image_notices and not specialist_outputs:
        return {"messages": [AIMessage(content="Here is the visual you requested.")]}

    persona_prompt = config["configurable"].get("system_prompt", "You are SHAIDOW.")
    joined_specialist_data = "\n\n".join(specialist_outputs + image_notices)

    # Build a clean synthesis prompt so SHAIDOW formats and polishes the specialist output
    history_without_tools = [
        m for m in messages
        if isinstance(m, (HumanMessage, AIMessage)) and not getattr(m, "tool_calls", None)
    ]

    synthesis_instruction = (
        f"{persona_prompt}\n\n"
        "---\n"
        "### ORCHESTRATION SYNTHESIS TASK\n"
        "Your specialist sub-agents returned the following raw output for the user's latest message:\n\n"
        f"{joined_specialist_data}\n\n"
        "Present a polished, well-structured final response as SHAIDOW using the specialist output above. "
        "Preserve all code blocks and technical accuracy in full, maintain your loyal/futuristic SHAIDOW persona, "
        "and end with 1-2 proactive next steps."
    )

    synth_messages = [SystemMessage(content=synthesis_instruction)] + history_without_tools
    final_ai_message = await agent_model.ainvoke(synth_messages)
    return {"messages": [final_ai_message]}


def create_agent_graph(system_prompt: str):
    workflow = StateGraph(AgentState)
    router_node = partial(router, config={"configurable": {"system_prompt": system_prompt}})
    finalize_node = partial(finalize, config={"configurable": {"system_prompt": system_prompt}})

    workflow.add_node("router", router_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("finalize", finalize_node)

    workflow.set_entry_point("router")
    workflow.add_conditional_edges("router", route_decision, {"tools": "tools", END: END})
    workflow.add_edge("tools", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()
