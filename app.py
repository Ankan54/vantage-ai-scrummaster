import streamlit as st
import time
from streamlit_extras.stylable_container import stylable_container
from agent import create_workflow
from data_fetch import LLM, RETRO_FEEDBACK
graph = create_workflow()
from data_fetch import run_get_tasks

# Page configuration
st.set_page_config(
    page_title="Vantage.ai",
    page_icon="🧑🏾‍💻",  
    layout="wide"
)

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "stream_buffer" not in st.session_state:
    st.session_state.stream_buffer = ""

if "show_cards" not in st.session_state:
    st.session_state.show_cards = True

if "standup_button_text" not in st.session_state:
    st.session_state.standup_button_text = "Start Standup"

if "retro_button_text" not in st.session_state:
    st.session_state.retro_button_text = "Start Retrospective"

if "chat_container_height" not in st.session_state:
    st.session_state.chat_container_height = 200  # Initial height when no messages

if "expander_expanded" not in st.session_state:
    st.session_state.expander_expanded = True

# def stream_handler(chunk: str, place_holder) -> None:
#     st.session_state.stream_buffer += chunk
#     # Print each chunk as it comes in
#     place_holder.write(st.session_state.stream_buffer)

# def generate_retro_report():
#     messages = [{"role": "user", "content": RETRO_FEEDBACK}]
#     stream_res = LLM.stream(messages)
#     st.session_state.stream_buffer = ""
#     # with st.chat_message("assistant"):
#     #place_holder = st.empty()
#     try:
#         for chunk in stream_res:
#             st.session_state.stream_buffer += chunk.content
#             #st.markdown(st.session_state.stream_buffer)
#     except:
#         pass

# Function to handle question button clicks
def ask_question(question):
    with st.session_state.history_container:
        # Add user message to chat history
        with st.chat_message("user"):
            st.markdown(f"**{question}**")

        st.session_state.messages.append({"role": "user", "content": question})

        # if question != "Get the Retrospective Report":
        for chunk in graph.stream({"messages": st.session_state.messages}):
            print(chunk)
        # else:
        #     generate_retro_report()
            
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": st.session_state.stream_buffer})
        # st.session_state.stream_buffer = ""
        
        # Hide cards
        st.session_state.show_cards = False
        
        # Collapse the expander when chat starts
        st.session_state.expander_expanded = False

        # Update chat container height when messages are present
        st.session_state.chat_container_height = 365

# Handle standup button click
def toggle_standup():
    if st.session_state.standup_button_text == "Start Standup":
        st.session_state.standup_button_text = "Get Standup Report"
        # Show notification using Streamlit toast
        st.toast("Standup Notification Sent to Team", icon="✅")
        time.sleep(3)
        st.rerun()
    else:
        # Send a standup summary prompt
        ask_question("Summarize the standup updates")

# Handle retrospective button click
def toggle_retro():
    if st.session_state.retro_button_text == "Start Retrospective":
        st.session_state.retro_button_text = "Get Retrospective Report"
        # Show notification using Streamlit toast
        st.toast("Retrospective Notification Sent to Team", icon="✅")
        time.sleep(3)
        st.rerun()
    else:
        get_retrospective_report()
    
def get_retrospective_report():
    # Send a retrospective summary prompt
    ask_question("Get the Retrospective Report")

def render_logo():
    st.markdown("# 🧑🏾‍💻 Vantage.ai")

# Custom CSS for minimal styling
def get_minimal_css():
    return """
    <style>
    /* Reduce size of question buttons */
    div.row-widget.stButton > button {
        font-size: 0.7rem !important;
        padding: 0.2rem 0.5rem !important;
        background-color: #f0f2f6 !important;
        color: #333333 !important;
        border: none !important;
    }
    
    /* Adjust container padding */
    .block-container {
        padding: 1rem 1rem !important;
        max-width: 100% !important;
    }
    
    /* Style the expander to inherit background color */
    .streamlit-expanderHeader {
        background-color: transparent !important;
        font-weight: bold !important;
    }
    
    /* Remove expander border */
    .streamlit-expanderContent {
        border: none !important;
        background-color: transparent !important;
    }
    </style>
    """

def render_quick_questions():
    questions = [
        "Summarise the progress of the team",
        "List blockers that have been long overdue",
        "What's the team velocity in this sprint?",
        "Are we on track for the sprint?",
        "What are the risks for this sprint?"
    ]

    
    with st.expander("Quick Questions", expanded=st.session_state.expander_expanded):
        # Use 5 columns for the buttons
        cols = st.columns(5)
        for i, question in enumerate(questions):
            with cols[i]:
                if st.button(question, key=f"q_{i}", use_container_width=True):
                    ask_question(question)

def render_sprint_sidebar():
    try:
        # First try to use the newer link_button if available
        st.link_button("VIew Project Board", "https://sharing.clickup.com/9016848875/l/h/8cq4cfb-876/8025b4c039a4ae6", use_container_width=True)
    except:
        # Fall back to a simpler approach for older Streamlit versions
        st.markdown(
            '<a href="https://sharing.clickup.com/9016848875/l/h/8cq4cfb-876/8025b4c039a4ae6" target="_blank" style="text-decoration: none;">Project Board 📋</a>', 
            unsafe_allow_html=True
        )

    st.markdown("#### Current Sprint Summary")
    
    categories = {
        "Blocked": [],
        "Overdue": [],
        "In Progress": [],
        "Completed": []
    }
    
    status_mapping = {
        "blocked": "Blocked",
        "pending": "Overdue",
        "in progress": "In Progress",
        "completed": "Completed"
    }
    res =run_get_tasks()
    for name, status in zip(res["name"], res["status"]):
        category = status_mapping.get(status.lower())
        if category and len(categories[category]) < 3:
            categories[category].append(name)
    
    status_colors = {
        "Blocked": st.error,
        "Overdue": st.warning,
        "In Progress": st.info,
        "Completed": st.success
    }
    for category, stories in categories.items():
        if stories:
            st.markdown(f"**{category}**")
            for story in stories:
                status_colors[category](story)

def main():
    # Inject minimal CSS
    st.markdown(get_minimal_css(), unsafe_allow_html=True)
    
    # Create a layout with main content and sidebar
    main_col, sidebar_col = st.columns([7, 2])
    
    with main_col:
        
        # Top section with logo, action buttons, and quick questions
        top_section, standup, retro = st.columns([7, 3, 3])
        
        with top_section:
            st.markdown("")
            render_logo()            

        with standup: 
            st.markdown("")
            st.markdown("")
            if st.button(st.session_state.standup_button_text, use_container_width=True):
                toggle_standup()
        
        with retro: 
            st.markdown("")
            st.markdown("")
            if st.button(st.session_state.retro_button_text, use_container_width=True):
                toggle_retro()

        # Display the UI only if show_cards is True
        if st.session_state.show_cards:
            # Create three equal-width columns for cards
            st.markdown("### Features")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                with st.container(border=True):
                    st.markdown("#### 📊 AI-Powered Insights")
                    st.markdown("Transform raw data into actionable insights with AI-powered analytics and visualization tools.")
            
            with col2:
                with st.container(border=True):
                    st.markdown("#### 🔄 Intelligent Task Automation")
                    st.markdown("Automate repetitive tasks such as scheduling, resource allocation, and progress tracking.")
            
            with col3:
                with st.container(border=True):
                    st.markdown("#### 📈 Automatic Progress Report")
                    st.markdown("AI generates and shares real-time dashboards and progress reports, showcasing metrics.")
        
        # Always display quick questions (now in an expander)
        render_quick_questions()
            
        # Display chat messages
        with st.container(border=True):
            
            history_container = st.container(height=st.session_state.chat_container_height, border=False)
            st.session_state.history_container = history_container
            with history_container:
                # Display chat messages using st.chat_message
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
            
            prompt = st.chat_input("ask about project status")
            if prompt:
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.session_state.chat_container_height = 365
                
                st.session_state.show_cards = False
                
                # Collapse expander when chat starts
                st.session_state.expander_expanded = False
                with history_container:                
                    for chunk in graph.stream({"messages": st.session_state.messages}, subgraphs=False):
                        print(chunk)
                
                st.session_state.messages.append({"role": "assistant", "content": st.session_state.stream_buffer})
                
                # Force a rerun to update the UI
                st.rerun()
    
    # Sidebar content
    with sidebar_col:
        # Sprint summary sidebar
        st.markdown("")
        st.markdown("")

        with st.container(border=True, height=750):
            render_sprint_sidebar()

if __name__ == "__main__":
    main()
