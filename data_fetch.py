from datetime import datetime
import pandas as pd
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from openai import OpenAI
import requests, os
import pandas as pd
from typing import List, Dict, Any
from dotenv import load_dotenv
load_dotenv()

def fetch_clickup_tasks(list_id):
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task?subtasks=true&include_closed=true"
    headers = {
        "accept": "application/json",
        "Authorization": os.getenv("CLICKUP_API_KEY")
    }
    response = requests.get(url, headers=headers)
    tasks = response.json()['tasks']
    return tasks

def cu2df(tasks: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert a list of ClickUp task JSON objects to a pandas DataFrame.
    
    Parameters:
    -----------
    tasks : List[Dict[str, Any]]
        A list of ClickUp task dictionaries
    
    Returns:
    --------
    pd.DataFrame
        A DataFrame with extracted task information
    """
    # Extract relevant information from tasks
    task_data = []
    
    for task in tasks:
        # Extract basic task information
        task_info = {
            'id': task.get('id'),
            'custom_id': task.get('custom_id'),
            'custom_item_id' : task.get('custom_item_id'),
            'name': task.get('name'),
            'description': task.get('description'),
            'status': task.get('status', {}).get('status'),
            'status_color': task.get('status', {}).get('color'),
            'date_created': pd.to_datetime(int(task.get('date_created', 0))/1000, unit='s'),
            'date_updated': pd.to_datetime(int(task.get('date_updated', 0))/1000, unit='s'),
            'archived': task.get('archived', False),
            'points' : task.get('points', None )
        }
        
        # Handle priority JSON
        priority = task.get('priority', {})
        if isinstance(priority, dict):
            task_info.update({
                'priority_color': priority.get('color'),
                'priority_id': priority.get('id'),
                'priority_orderindex': priority.get('orderindex'),
                'priority_name': priority.get('priority')
            })
        elif isinstance(priority, str):
            # If priority is a simple string
            task_info['priority_name'] = priority
        
        # Extract creator information
        creator = task.get('creator', {})
        task_info.update({
            'creator_id': creator.get('id'),
            'creator_username': creator.get('username'),
            'creator_email': creator.get('email'),
        })
        
        # Extract custom fields
        custom_fields = {field['name']: field.get('type_config', {}).get('default') 
                         for field in task.get('custom_fields', [])}
        
        tshirt_size = None
        for field in task.get("custom_fields", []):
            if field.get("name") == "T-shirt Size":
                
                options = field.get("type_config", {}).get("options", [])
                for option in options:
                    
                    if option.get("orderindex") == field.get("value"):
                        tshirt_size = option.get("name")

                        break
            custom_fields['T-shirt Size'] = tshirt_size


        
        task_info.update(custom_fields)
        
        # Extract and categorize tags
        tags = task.get('tags', [])
        tag_names = [tag.get('name', '') for tag in tags]
        
        # Separate item type and sprint tags
        task_info['item_type'] = next((tag for tag in tag_names if tag in ['story', 'epic', 'task', 'bug', 'improvements']), '')
        task_info['sprint_name'] = next((tag for tag in tag_names if tag.startswith('sprint ')), '')
        task_info['tags'] = ', '.join(tag_names)
        
        # Extract assignees
        assignees = task.get('assignees', [])
        assignee_names = [assignee.get('username', '') for assignee in assignees]
        task_info['assignees'] = ', '.join(assignee_names)
        
        # Extract additional metadata
        task_info.update({
            'parent_task': task.get('parent'),
            'top_level_parent': task.get('top_level_parent'),
            'list_name': task.get('list', {}).get('name'),
            'project_name': task.get('project', {}).get('name'),
            'due_date': pd.to_datetime(int(task.get('due_date', 0))/1000, unit='s') if task.get('due_date') else None,
        })
        
        task_data.append(task_info)
    
    # Create DataFrame
    df = pd.DataFrame(task_data)
    
    return df

def preprocess(df):
    df = df.merge(df[['id', 'name']], left_on='parent_task', right_on='id', how='left', suffixes=('', '_parent'))

    # Replace parent_task ID with its corresponding name
    df["parent_task"] = df["name_parent"]

    # Drop the extra columns
    df.drop(columns=["id_parent", "name_parent"], inplace=True)
    df = df[['id', 'name', 'description', 'status','assignees' ,'item_type' ,'sprint_name'
    , 'date_created', 'date_updated', 
    'creator_id', 'creator_username', 'creator_email','parent_task',
        'priority_orderindex','points',
    'priority_name']]
    return df


def run_get_tasks(list_id  = '901607242495'):
    tasks = fetch_clickup_tasks(list_id)
    df= cu2df(tasks)
    df = preprocess(df)
    return df

token = os.getenv("GITHUB_TOKEN")
endpoint = "https://models.github.ai/inference"
model_name = "openai/gpt-4o"

LLM = OpenAI(
    base_url=endpoint,
    api_key=token,
    temperature=0,
    model=model_name
)

RETRO_FEEDBACK = """Sprint 1 Retrospective
What Went Well

"We successfully established the initial API architecture and implemented the foundational endpoints."
"The UI design foundations and core components were completed as planned."
"The experiment tracking setup was implemented without major hurdles."
"We managed to develop the baseline forecasting model on schedule."
"The initial MLOps pipeline foundations are in place and working."

What Could Be Improved

"Some team members had multiple critical path tasks assigned simultaneously, creating bottlenecks."
"The data pipeline setup task became blocked and couldn't be completed this sprint."
"Dependencies between stories weren't clearly identified during planning, which affected workflow."
"Communication about blockers wasn't happening early enough in our daily standups."
"We didn't allocate enough time for knowledge sharing about the MLOps infrastructure."
"Acceptance criteria for some stories, especially around the API architecture, were somewhat vague."
"We didn't properly account for the learning curve associated with some of the new technologies."
"Documentation for completed components was minimal and inconsistent."

Action Items

Improve story breakdown to avoid assigning multiple critical path items to the same person
Conduct a dependency mapping session before sprint planning
Implement a "blocker identification" segment in daily standups
Schedule regular knowledge sharing sessions for complex technical components
Create templates for component documentation
Develop clearer acceptance criteria templates
Reserve buffer time for tasks involving new technologies

Sprint 2 Retrospective
What Went Well

"The data visualization components were completed successfully and received positive feedback."
"We implemented model predictions with confidence intervals ahead of schedule."
"Extending the API layer is progressing well despite its complexity."
"The experiment tracking capabilities have been expanded effectively."
"Cross-team collaboration improved, especially between the UI and API developers."

What Could Be Improved

"We still have three blocked stories at the end of this sprint, including two carried over from Sprint 1."
"The model deployment pipeline is blocked due to infrastructure dependencies."
"Advanced model development couldn't proceed due to dependencies on the data pipeline."
"The forecasting parameter customization task took longer than estimated due to unclear requirements."
"Documentation continues to be inconsistent across components."
"Communication about dependencies and blockers is still happening too late to resolve effectively."
"We didn't properly account for the complexity of the model deployment pipeline."
"Testing frameworks are still pending, which may create quality issues later."
"Knowledge silos persist, particularly around MLOps infrastructure and advanced modeling techniques."

Action Items

Conduct an urgent unblocking session focused specifically on the data pipeline setup
Create a visual dependency map for all remaining stories
Implement a "blocker early warning system" where potential blockers are flagged in advance
Prioritize the initial testing framework in Sprint 3
Schedule dedicated documentation days at the end of each week
Rotate team members across different components to reduce knowledge silos
Break down complex tasks like model deployment into smaller, more manageable stories
Implement pair programming for complex tasks to improve knowledge sharing

Above given the retrospective feedback for the previous two sprints. Your task is to create a summary of theffedback for sprint 2 and analyse the feedback of both sprint 1 and 2 to identify the recurring issues in the project and how to rectify the same.
"""
