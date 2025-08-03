from typing import Sequence, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI

from tools import all_tools

class AgentState(TypedDict):
    messages: Sequence[BaseMessage]

agent_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", convert_system_message_to_human=True)
agent_with_tools = agent_model.bind_tools(all_tools)
tool_node = ToolNode(all_tools)

def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

def call_model(state: AgentState) -> dict:
    response = agent_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# Updated function to accept the system prompt
def create_agent_graph(system_prompt: str):
    """
    Factory function to create and compile the LangGraph agent.
    """
    workflow = StateGraph(AgentState)

    # We need a way to inject the system message into the state
    def add_system_message(state: AgentState) -> AgentState:
        # Create a new list with the system message at the beginning
        # This ensures the agent always has its instructions
        messages_with_system = [SystemMessage(content=system_prompt)] + list(state['messages'])
        return {"messages": messages_with_system}

    # This node will preprocess the input to add the system message
    workflow.add_node("preprocess", add_system_message)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    # The entry point is now the preprocessing node
    workflow.set_entry_point("preprocess")
    
    # After preprocessing, we go to the agent
    workflow.add_edge("preprocess", "agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        },
    )
    workflow.add_edge("tools", "agent")

    agent_graph = workflow.compile()
    
    return agent_graph