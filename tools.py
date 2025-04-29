from langchain_core.tools import tool
# from analyzer import data_picker_agent, report_generator_agent
# from data_fetch import get_task_comments
import requests
import math, os
from typing import Optional, Union
from dotenv import load_dotenv
load_dotenv()


@tool
def update_task_status(task_id: str, new_status: str) -> dict:
    """Update the status of a specific task.
    
    Args:
        task_id: The ID of the task to update
        new_status: The new status to set for the task
        
    Returns:
        Response from the API as a dictionary
    """
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    payload = {"status": new_status}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": os.getenv("CLICKUP_API_KEY")
    }
    
    response = requests.put(url, json=payload, headers=headers)
    return response.json()


@tool
def get_task_comments(task_id: str, fetch_comments: bool = False) -> list:
    """Get comments for a specific task, only when required.
    
    Args:
        task_id: The ID of the task to get comments for
        fetch_comments: Whether to fetch comments or return empty list (default: False)
        
    Returns:
        List of comments with text and username
    """
    if not fetch_comments:
        return []
        
    url = f"https://api.clickup.com/api/v2/task/{task_id}/comment"
    headers = {
        "accept": "application/json",
        "Authorization": os.getenv("CLICKUP_API_KEY")
    }
    
    response = requests.get(url, headers=headers)
    comments = response.json().get('comments', [])
    
    refined_comments = [{"comment_text": comment["comment_text"], "username": comment["user"]["username"]} for comment in comments]
    return refined_comments

@tool
def get_list_members() -> dict:
    """Get all members of a specific list.
    
    Returns:
        Dictionary containing a list of members with their id, username, and email
    """
    url = "https://api.clickup.com/api/v2/list/901607182023/member"
    headers = {
        "accept": "application/json",
        "Authorization": os.getenv("CLICKUP_API_KEY")
    }
    
    response = requests.get(url, headers=headers)
    members_data = response.json()
    members = [{"id": member["id"], "username": member["username"], "email": member["email"]} for member in members_data["members"]]
    
    return {"members": members}

@tool
def add_comment(task_id: str, new_comment: str) -> dict:
    """Add a comment to a specific task.
    
    Args:
        task_id: The ID of the task to add a comment to
        new_comment: The text of the comment to add
        
    Returns:
        Response from the API as a dictionary
    """
    url = f"https://api.clickup.com/api/v2/task/{task_id}/comment?custom_task_ids=false"
    
    payload = {
        "notify_all": False,
        "comment_text": new_comment
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": os.getenv("CLICKUP_API_KEY")
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    return response.json()
@tool
def math_calculator(
    operation: str, 
    x: float, 
    y: Optional[float] = None
) -> Union[float, str]:
    """
    Perform advanced mathematical calculations.
    
    Args:
        operation (str): Mathematical operation to perform. 
        Supported operations:
        - Basic: 'add', 'subtract', 'multiply', 'divide'
        - Advanced: 'power', 'sqrt', 'log'
        - Trigonometric: 'sin', 'cos', 'tan'
        
        x (float): First number for the calculation
        y (float, optional): Second number for operations requiring two inputs
    
    Returns:
        float or str: Result of the calculation or error message
    
    Examples:
        math_calculator('add', 5, 3)  # Returns 8
        math_calculator('sqrt', 16)   # Returns 4
        math_calculator('sin', 0.5)   # Returns sine of 0.5
    """
    try:
        # Basic arithmetic operations
        if operation == 'add':
            return x + y if y is not None else x
        elif operation == 'subtract':
            return x - y if y is not None else -x
        elif operation == 'multiply':
            return x * y if y is not None else x
        elif operation == 'divide':
            if y == 0:
                return "Error: Division by zero"
            return x / y
        
        # Advanced mathematical operations
        elif operation == 'power':
            return x ** (y if y is not None else 2)
        elif operation == 'sqrt':
            return math.sqrt(x)
        elif operation == 'log':
            return math.log(x)
        
        # Trigonometric functions
        elif operation == 'sin':
            return math.sin(x)
        elif operation == 'cos':
            return math.cos(x)
        elif operation == 'tan':
            return math.tan(x)
        
        else:
            return f"Unsupported operation: {operation}"
    
    except Exception as e:
        return f"Calculation error: {str(e)}"
