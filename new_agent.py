from pydantic import BaseModel, Field
from typing import Dict, Any, Literal, TypedDict, List, Annotated
from langgraph.types import Command
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END, MessagesState
# from langchain_core.prompts import 
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from data_fetch import run_get_tasks, LLM
import streamlit as st
from prompts import *
# from analyzer import data_picker_agent, report_generator_agent
RETRY_LIMIT = 2


members = ["scrum_master", "writer", "visualizer"]
options = members + ["FINISH"]

class State(MessagesState):
    invoke_history: Dict[str, int] = Field(default_factory=lambda: {m: 0 for m in members})
    next: str

class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""
    next: Literal[tuple(members)]


def supervisor_node(state: State) -> Command[Literal[tuple(members)]]:
    system_prompt = """You are the Supervisor Agent for an AI Scrummaster App, responsible for orchestrating a conversation between specialized workers to fulfill user requests efficiently. Your role is to analyze each user request, determine which specialized agent should handle it next, and manage the overall workflow until completion.

Available Agents:
1. Scrum Master Agent: Performs complex reasoning and analysis of scrum project data from a Scrum Master's perspective. Use this agent when:
   - The request requires knowledge or analysis of scrum data.
   - The request requires assessment of sprint metrics, team velocity, or burndown charts.
   - Scrum artifacts or ceremonies need to be evaluated
   - Team performance patterns need to be identified and understood
   - Agile process improvements need to be recommended based on data
   - Any Issues or blockers need to be identified and addressed
   - Analysis of Sprint health and Overall Delivery Status

2. Writer Agent: Creates polished, coherent responses based on available information. Use this agent when:
   - When the data does not require any form of visualization to adequately answer the user query
   - When all the data to answer the query is available
   - Analysis is complete and results need to be communicated
   - A well-structured response needs to be crafted
   - Content needs to be organized and presented clearly
   - Information needs to be summarized for the user

3. Visualizer Agent: Creates visual representations of data or concepts. Use this agent when:
   - Data visualization would enhance understanding, like sprint velocity charts, burnup charts, or burndown charts.
   - Charts, graphs, or diagrams are explicitly requested
   - Complex relationships would be clearer with visual representation
   - The user needs to or should see patterns or trends in data

Your goal is to ensure efficient collaboration between agents without unnecessary steps while delivering complete solutions to user requests.

Response Format:
Always respond with only one of the following:
- "scrum_master" - When scrum project analysis or agile metrics assessment is needed
- "writer" - When information needs to be communicated in a polished form
- "visualizer" - When visual representation would be beneficial

YOUR RESPONSE: """

    messages = [
        {"role": "system", "content": system_prompt},
    ] + state["messages"]
    
    response = LLM.with_structured_output(Router).invoke(messages)
    goto = response["next"]
    print(f"FROM: Supervisor, TO: {goto}\n{state}")
    if "invoke_history" not in state:
        state["invoke_history"] = {m: 0 for m in members}
    if state["invoke_history"][goto] >= RETRY_LIMIT:
        goto = "writer"
    # if goto == "FINISH":
    #     goto = END

    return Command(goto=goto, update=state)

def get_scrum_data():
    return run_get_tasks().to_json(orient="records")


def scrum_master_node(state: State) -> Command[Literal["supervisor"]]:
    # messages = [{"role": "system", "content": f"""You are an Experienced scrum Master, You are given the Entire Scrum Project Information of the User's project Team. Your task is to help the user search and analyze the project data so that it can be formed into a coherent response. Respond with the relevant data points from the scrum data given to you and your analysis of the data as per the user query, in structured and easily understandable manner.
    
    # AVAILABLE SCRUM DATA IN JSON:
    # {get_scrum_data()}
    # """}] + state["messages"]
    react_agent = create_react_agent(
    LLM,  
    tools=[get_task_comments] , state_modifier=SystemMessage(  scrum_master_prompt.format(get_scrum_data())), + state["messages"]
    name="scrum_master")

    # result = LLM.invoke(messages)
    result = react_agent.invole(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result.content, name="scrum_master")
            ],  "next": "supervisor",
            "invoke_history": {
                **state["invoke_history"],
                "scrum_master": state["invoke_history"]["scrum_master"] + 1,
            }
        },
        goto="supervisor",
    )

def visualizer(state: State) -> Command[Literal["__end__"]]:
    messages = [{'role': 'system', 'content': """You are an expert data analyst. You are given the user's query and all the data you will need to answer the query.\
                Your task is to answer the User's query clearly as per the given instructions below.
                [INSTRUCTIONS]
                1. Consider the context in which the question is being asked. Is it exploratory analysis, data validation, reporting, or problem-solving. Form your asnwer accordingly.
                2. Briefly explain about the data that is provided to you in case the user is not familiar with the dataset.
                3. Start with a clear and concise answer to the query. Address the primary question directly before diving into the details.
                4. Use specific data points, summaries, or statistics to support your answer.
                5. Add some visual aids like Tables, charts, graphs as well to enhance the clarity of your answer. Always try to include any charts along with tables. Use the type of chart that can provide the best clarity to user.
                6. The visuals will be written in the form of code. the code will be written using HTML, CSS, BootStrap and JavaScript only.
                7. Make sure the visuals look appealing and all the data points, table headers, chart axes are accurately labeled. use javascript chart.js library to display the Graphs and Charts.
                8. Always ensure that the code is accurate and all the necessary dependency are being installed in the code itself.
                9. Make sure to have a modern look to the visuals. if there are different data points, do not put all of them in a single chart. display multiple charts wherever required.
                """},
                {'role': 'user', 'content': f"""User Query: {state["messages"]}
                Answer: """}]
    for data in LLM.stream(messages):
        try:
            if data["choices"][0]["delta"]["content"]:
                text = data["choices"][0]["delta"]["content"]
                #print(text)
                # Check for HTML code blocks
                if "```" in text:
                    html_block_flag = True
                    html_code = ""
                elif html_block_flag and "```" in text:
                    html_block_flag = False
                    #html_placeholder.code(html_code.replace("```html", "").replace("```", "").strip())
                
                # Accumulate HTML or regular content
                if html_block_flag:
                    html_code += text
                    # with html_expander:
                    #     html_placeholder.markdown(html_code)
                else:
                    content += text
                    content_placeholder.markdown(content)
        except:
            pass

def writer_node(state: State) -> Command[Literal["supervisor"]]:
    messages = [{"role": "system", "content": f"""You are an Expert Data, You are given all the information needed to answer the user's query in a coherent manner. Your task is to craft a response that is concise, clear, and easy to understand."""}] + state["messages"]

    st.session_state.stream_buffer = ""

    def stream_handler(chunk: str, place_holder) -> None:
        st.session_state.stream_buffer += chunk
        # Print each chunk as it comes in
        place_holder.write(st.session_state.stream_buffer)
    
    # Configure the LLM to use the streaming callback
    config = {}
    config["callbacks"] = [{"stream": stream_handler}]
    
    # Generate a response (streaming happens through the callback)
    with st.chat_message("user"):
        place_holder = st.empty()
        for chunk in LLM.stream(messages):
            stream_handler(chunk.content, place_holder)
    
    
    # Add the completed response to the state
    return Command(
        update={
        "messages": messages + {"role": "assistant", "content": st.session_state.stream_buffer},
        "next": "FINISHED",
        "invoke_history": {
            **state["invoke_history"],
            "writer": state["invoke_history"]["writer"] + 1,
        },
    },
    goto = END)

# Create the graph
def create_workflow() -> StateGraph:
    """
    Creates the LangGraph workflow for the scrum bot.
    """
    # Initialize the graph
    workflow = StateGraph(State)
    
    # Add the nodes (agents)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("scrum_master", scrum_master_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("visualizer", visualizer)
    
    # Add the edges (connections between agents)
    # workflow.add_edge("supervisor", "scrum_master")
    # workflow.add_edge("supervisor", "writer")
    # workflow.add_edge("writer", END)
    
    # Set the entry point
    workflow.set_entry_point("supervisor")
    
    # Compile the graph
    return workflow.compile()

    for s in graph.stream(
    {"messages": [("user", "List all the comments for the task 86cycygye using the tool")]}, subgraphs=False
):
    print(s)
    print("----")
