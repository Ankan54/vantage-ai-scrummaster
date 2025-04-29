import re
from pydantic import BaseModel, Field
from typing import Dict, Any, Literal, TypedDict, List, Annotated
from langgraph.types import Command
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from data_fetch import run_get_tasks, LLM, RETRO_FEEDBACK
import streamlit as st
import streamlit.components.v1 as components
from tools import *
from prompts import *
RETRY_LIMIT = 2


members = ["scrum_master", "writer", "visualizer"]
options = members + ["FINISH"]

class State(MessagesState):
    invoke_history: Dict[str, int] = Field(default_factory=lambda: {m: 0 for m in members})
    # with st.status("Thinking...", expanded=True) as thinking_status:
    #     st_thinking = thinking_status
    st_thinking: st.expander = Field(default_factory=lambda: st.expander("Thinking...", expanded=True))
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
   - DO NOT call if data is adequate or not required

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

4. You are given the RetroSpective Feedback of the last two sprints. When user asks about retrospective report, you will directly call the writer agent to generate the report.  

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

    with state["st_thinking"]:
        with st.container(border=True):
            with st.spinner():
                st.write("Superviser Agent: Thinking of next steps...")
                response = LLM.with_structured_output(Router).invoke(messages)
                goto = response["next"]
                print(f"FROM: Supervisor, TO: {goto}\n{state}")

                if state["invoke_history"][goto] >= RETRY_LIMIT:
                    goto = "writer"
                # if goto == "FINISH":
                #     goto = END

                return Command(goto=goto, update=state)

def get_scrum_data():
    return run_get_tasks().to_json(orient="records")


def scrum_master_node(state: State) -> Command[Literal["supervisor"]]:

    react_agent = create_react_agent(
    LLM,  
    tools=[get_task_comments , get_list_members,add_comment,math_calculator,update_task_status ] , state_modifier=SystemMessage(  scrum_master_prompt.format(get_scrum_data())) )


    if "invoke_history" not in state:
        state["invoke_history"] = {m: 0 for m in members}
    if "st_thinking" not in state:
        state["st_thinking"] = st.expander("Thinking...", expanded=True)
    with state["st_thinking"]:
        with st.container(border=True):
            with st.spinner():
                st.write("Clickup API: Gathering Data")
                messages = [{"role": "system", "content": f"""You are an Experienced scrum Master, You are given the Entire Scrum Project Information of the User's project Team. Your task is to help the user search and analyze the project data so that it can be formed into a coherent response. Respond with the relevant data points from the scrum data given to you and your analysis of the data as per the user query, in structured and easily understandable manner.
                AVAILABLE SCRUM DATA IN JSON:
                {get_scrum_data()}
                """}] + state["messages"]
                st.write("Refining Data based on user query...")
                result = react_agent.invoke(state)

                last_ai_message = result['messages'][-1]
                return Command(
                    update={
                        "messages": [
                            HumanMessage(content=last_ai_message.content, name="scrum_master")
                        ],  "next": "supervisor",
                        "invoke_history": {
                            **state["invoke_history"],
                            "scrum_master": state["invoke_history"]["scrum_master"] + 1,
                        },
                        "st_thinking": state["st_thinking"],
                    },
                    goto="supervisor",
                )


def extract_from_markdown(text, mark="python"):
    pattern = r'```{}\s*(.*?)\s*```'.format(mark)
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else None


def visualizer(state: State) -> Command[Literal["__end__"]]:
    messages = [{'role': 'system', 'content': """You are an expert Data Analyst. You are given all the data required to answer the user's query. Write youre response adhering tothe instructions below:
[INSTRUCTIONS]
1. **Context Assessment**: Identify whether the query is for exploratory analysis, data validation, reporting, trend identification, or problem-solving. Tailor your response format accordingly.
2. **Data Introduction**: Begin with a brief overview of the dataset when relevant, including its structure, key variables, and any important metadata to orient users unfamiliar with the data.
3. **Direct Answer First**: Provide a clear, concise answer to the primary question before expanding into supporting details or methodology. Highlight key findings in bold when appropriate.
4. **Evidence-Based Support**: Include specific metrics, statistical findings, or data points that directly support your conclusions. When applicable, mention confidence levels or limitations of the analysis.
5. **Visual Representation Strategy**:
   - Select visualization types based on the user's query and data characteristics (not a one-size-fits-all approach)
   - Create multiple focused visualizations rather than overcrowded single charts
   - Use appropriate visualization types:
     * Time series data → Line charts, area charts
     * Categorical comparisons → Bar/column charts, heat maps
     * Part-to-whole relationships → Pie charts, stacked bars, treemaps
     * Distributions → Histograms, box plots, violin plots
     * Correlations → Scatter plots, bubble charts, correlation matrices
     * Geographical data → Maps with data overlays
6. **Visualization Implementation**: Generate visualizations using HTML, CSS, Bootstrap, and JavaScript (Chart.js). Ensure responsive design that works across device sizes.
7. **Visual Quality Standards**:
   - Implement a consistent color scheme across visualizations
   - Ensure all axes, legends, and data points are clearly labeled
   - Include appropriate titles and subtitles for each visualization
   - Add data tooltips for interactive exploration
   - Optimize for accessibility (color contrast, alternative text)
   - Include data source attribution when relevant
8. **Code Quality**: Ensure all code is functional, properly formatted, and includes necessary dependencies within the implementation. Include brief comments explaining complex sections.
9. **Progressive Enhancement**: When the data complexity warrants it, provide both simple summary visualizations and more detailed exploratory options.
10. **Actionable Insights**: Conclude with 2-3 key takeaways or recommendations based on the data analysis, connecting back to the original query.
11. **Markdown Formatting**: Ensure your response is properly formatted using Markdown syntax, including headings, lists and code blocks.
                 """,}] + state["messages"]
    html_expander = st.expander("Generating Visuals")
    html_placeholder = st.empty()
    content_placeholder = st.empty()
    st.session_state.stream_buffer = ""
    html_block_flag = False
    html_code = ""
    with st.chat_message("assistant"):
        for data in LLM.stream(messages):
            try:
                if "```" in data.content:
                    html_block_flag = True
                    html_code = ""
                elif html_block_flag and "```" in data.content:
                    html_block_flag = False
                    html_code += data.content
                    with html_expander:
                        html_placeholder.markdown(html_code)
                        html_code_str = extract_from_markdown(html_code, mark='html')
                        components.html(html_code_str, height=600, scrolling=True)
                    #html_placeholder.code(html_code.replace("```html", "").replace("```", "").strip())
                
                # Accumulate HTML or regular content
                if html_block_flag:
                    html_code += data.content
                    with html_expander:
                        html_placeholder.markdown(html_code)
                        # components.html(html_code_str, height=600, scrolling=True)

                else:
                    st.session_state.stream_buffer += data.content
                    content_placeholder.write(st.session_state.stream_buffer)

            except Exception as e:
                st.write(e)
                pass

    return Command(
        update={
        "messages": messages + [{"role": "assistant", "content": st.session_state.stream_buffer}],
        "next": "FINISHED",
        "invoke_history": {
            **state["invoke_history"],
            "writer": state["invoke_history"]["writer"] + 1,
        },
    },
    goto = END)

        

def writer_node(state: State) -> Command[Literal["supervisor"]]:
    messages = [{"role": "system", "content": f"""You are an Expert Writer, You are given all the information needed to answer the user's query in a coherent manner. Your task is to craft a response that is concise, clear, and easy to understand. Use tables and bullets points to structure and organize wherever the information can be expressed in a structured and elegant manner. \
                You are also given the retrospective feedback of the last two sprints. Use this information only when asked about creating Retrospective Report. RETROSPECTIVE_FEEDBACK: {RETRO_FEEDBACK}. Do not incude Retrospective information for any other question"""}] + state["messages"]

    st.session_state.stream_buffer = ""

    def stream_handler(chunk: str, place_holder) -> None:
        st.session_state.stream_buffer += chunk
        # Print each chunk as it comes in
        place_holder.write(st.session_state.stream_buffer)
    
    # Configure the LLM to use the streaming callback
    config = {}
    config["callbacks"] = [{"stream": stream_handler}]
    
    # Generate a response (streaming happens through the callback)
    with st.chat_message("assistant"):
        place_holder = st.empty()
        try:
            for chunk in LLM.stream(messages):
                stream_handler(chunk.content, place_holder)
        except:
            pass
    
    # Add the completed response to the state
    return Command(
        update={
        "messages": messages + [{"role": "assistant", "content": st.session_state.stream_buffer}],
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
    workflow.set_entry_point("scrum_master")
    
    # Compile the graph
    return workflow.compile()


def CardProperties(BaseModel):
    title: str
    description: str

def card_agent(query: str):
    meesage = {
        "role": "system",
        "content": ""
    }
    response = LLM.with_structured_output(List[CardProperties]).invoke(message)
