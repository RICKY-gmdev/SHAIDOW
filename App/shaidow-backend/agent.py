# agent.py
import os
from typing import Dict, Any, Optional, Sequence, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import (
    ToolMessage,
    SystemMessage,
    HumanMessage,
    BaseMessage,
    AIMessage,
    AnyMessage,
)
from langchain_core.runnables import RunnableConfig
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
Inspect the conversation and route the user's request to the right specialist tool(s):
1. Call `coding_tool` for ANY code, debugging, software architecture, .NET/C#, Python, SQL, or algorithm request.
2. Call `reasoning_tool` for complex analysis, logic puzzles, math, strategy, or deep multi-step questions.
3. Call `mistral_tool` for quick facts, summaries, definitions, or real-world overviews.
4. Call `search_for_image_tool` when the user asks to see a real photo OR when a real photo enriches a factual topic.
5. Call `generate_image_tool` when the user asks to create, draw, or generate custom AI art/illustrations.
   - You MAY call multiple tools in parallel (e.g., `mistral_tool` + `search_for_image_tool`).
   - Always pass a self-contained, detailed `query` (include relevant context from earlier messages so the specialist tool has everything it needs).
   - When calling a tool, do NOT write a text response before the tool call—just emit the tool call directly.
   - ONLY reply directly without tools if the user is greeting you, chatting casually, or asking about your identity as SHAIDOW."""


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


def _replace_system_prompt(messages: Sequence[AnyMessage], prompt: str) -> list[BaseMessage]:
    filtered = [m for m in messages if not isinstance(m, SystemMessage)]
    return [SystemMessage(content=prompt.strip())] + list(filtered)


def route_decision(state: AgentState) -> str:
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []
    if isinstance(last_message, AIMessage) and tool_calls:
        return "tools"
    return END


def create_agent_graph(system_prompt: str, checkpointer=None):
    async def router(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        if agent_with_tools is None or agent_model is None:
            raise RuntimeError("Agent not initialized. Call initialize_agent() first.")

        combined_router_prompt = f"{ROUTER_INSTRUCTION}\n\n---\n{system_prompt}"
        messages = _replace_system_prompt(state["messages"], combined_router_prompt)

        try:
            response = await agent_with_tools.ainvoke(messages, config=config)
        except Exception as e:
            print(f"--- Router tool-call failed, falling back to direct model: {e} ---")
            response = await agent_model.ainvoke(messages, config=config)

        return {"messages": [response]}

    async def finalize(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
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
                image_notices.append("[Visual asset successfully retrieved/generated and displayed to the user.]")
            else:
                specialist_outputs.append(f"### Specialist Output ({tm.name}):\n{content}")

        history_without_tools = [
            m for m in messages
            if isinstance(m, (HumanMessage, AIMessage)) and not getattr(m, "tool_calls", None)
        ]

        joined_specialist_data = "\n\n".join(specialist_outputs + image_notices)

        synthesis_instruction = (
            f"{system_prompt}\n\n"
            "---\n"
            "### ORCHESTRATION SYNTHESIS TASK\n"
            "Your specialist sub-agents returned the following output for the user's latest request:\n\n"
            f"{joined_specialist_data}\n\n"
            "Instructions:\n"
            "- Present a polished, well-structured final response as SHAIDOW using the specialist output above.\n"
            "- If only an image was generated/found, briefly confirm it in SHAIDOW's voice without repeating raw URLs.\n"
            "- Preserve all code blocks and technical details in full.\n"
            "- End with 1-2 concise, proactive next steps."
        )

        synth_messages = [SystemMessage(content=synthesis_instruction)] + history_without_tools
        final_ai_message = await agent_model.ainvoke(synth_messages, config=config)
        return {"messages": [final_ai_message]}

    workflow = StateGraph(AgentState)
    workflow.add_node("router", router)
    workflow.add_node("tools", tool_node)
    workflow.add_node("finalize", finalize)

    workflow.set_entry_point("router")
    workflow.add_conditional_edges("router", route_decision, {"tools": "tools", END: END})
    workflow.add_edge("tools", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile(checkpointer=checkpointer)
