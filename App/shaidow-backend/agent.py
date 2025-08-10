# agent.py (Refactored)

from langchain_core.messages import (
    HumanMessage,
    ToolMessage,
    SystemMessage,
    BaseMessage,
)
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import all_tools


agent_model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    convert_system_message_to_human=True,
    temperature=0.2 # Using the temperature from your previous tool definition
)

agent_with_tools = agent_model.bind_tools(all_tools)
tool_node = ToolNode(all_tools)


# --- 2. Agent Node ---
# We've consolidated all agent logic into this single function.
def call_model(state: MessagesState) -> dict:
    """
    The primary agent node. It invokes the model with the correct, unaltered
    conversation history and returns the response to be added to the state.
    
    """
    response = agent_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# --- 3. Graph Conditional Logic ---
def should_continue(state: MessagesState) -> str:
    """
    Determines the next step. If the last message was an AI message
    with tool calls, route to the 'tools' node. Otherwise, end.
    """
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END

# --- 4. Graph Definition ---
def create_agent_graph(system_prompt: str) -> StateGraph:
    """
    Builds the LangGraph agent.
    """
    # Use the standard MessagesState for the graph's state.
    workflow = StateGraph(MessagesState)

    def add_system_message(state: MessagesState) -> dict:
        """
        A pre-processing node to ensure the system prompt is the first message.
        """
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            # Return a dict to immutably update the state
            return {"messages": [SystemMessage(content=system_prompt)] + messages}
        return {} # No change needed

    workflow.add_node("preprocess", add_system_message)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.set_entry_point("preprocess")
    workflow.add_edge("preprocess", "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        # The routing map: "tools" goes to the "tools" node, END stops the graph.
        {"tools": "tools", END: END},
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()