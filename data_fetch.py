from datetime import datetime
import pandas as pd
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from databricks_langchain import ChatDatabricks
import requests 
import pandas as pd
from typing import List, Dict, Any

def fetch_clickup_tasks(list_id):
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task?subtasks=true&include_closed=true"
    headers = {
        "accept": "application/json",
        "Authorization": "pk_176660818_YUYR1Z46L0B7WT8CU8MCCEC00B3W3I07"
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

LLM = ChatDatabricks(
    endpoint="databricks-claude-3-7-sonnet",
    temperature=0,
    max_tokens=1500,
)
