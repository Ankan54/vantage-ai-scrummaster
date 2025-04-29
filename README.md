![Logo](https://github.com/Ankan54/scrum_n_coke/blob/main/assets/vatnageailogo.JPG)
# Vantage.ai : A Multi-Agent Project Management Tool
Vantage.ai is an intelligent, multi-agent generative AI application that acts as a proactive Scrum Master for project teams. Through a natural, conversation-driven interface, Vantage.ai autonomously monitors project status, evaluates sprint health, identifies critical blockers, analyzes team member capacity, and generates automated standup summaries and retrospective insights. Each specialized agent collaborates in real time to provide teams with continuous, context-aware support, helping them stay aligned, anticipate issues early, and drive better outcomes — all without manual overhead.

Vantage.ai consists of the following type of agents,

- **Central Scrum Master Agent**  
  - Acts as the core orchestrator, coordinating all specialized agents.
  - Manages the overall project flow and ensures seamless communication between agents.

- **Sprint Analyser Agent**  
  - Analyzes project artifacts (tasks, tickets, updates).
  - Provides detailed summaries highlighting positives, negatives, risks, and key achievements.

- **Sprint Monitoring Agent**  
  - Continuously monitors project activity in the background.
  - Detects lack of updates or non-compliance with Agile principles.
  - Sends timely notifications to relevant users to ensure corrective action.

- **Standup and Retrospective Agent**  
  - Automates daily standups and sprint retrospectives.
  - Collects feedback individually from team members.
  - Collates feedback into detailed summaries with action items and critical issues clearly outlined.
  - Analyzes historical standup and retrospective data to identify:
    - Knowledge gaps
    - Process improvement opportunities

- **Sprint Planner Agent**  
  - Identifies unrefined user stories and epics to prepare the agenda for sprint planning sessions.
  - Suggests story point estimations based on task complexity.
  - Recommends story assignments to team members by analyzing their capacity and previous work experience.

- **General Writer Agent**  
  - Organizes all agent outputs into coherent, easy-to-understand written reports.

- **Visualizer Agent**  
  - Enhances summaries and reports with graphs, charts, and visual data points for better decision-making.


All these specialized agents work collaboratively under the leadership of the Scrum Master Agent, helping teams manage projects more efficiently and effectively through intelligent, autonomous support.

![Architecture](https://github.com/Ankan54/scrum_n_coke/blob/main/assets/vantageai.JPG)

---

## Project Setup

The project can be run easily using docker containers. the dockerfile have been provided with the codebase. you can build the docker image and run the app using the below commands

```bash
  docker build -t <image_name>:<tag_name> .
  docker run -p 8080:8080 <image_name>:<tag_name>
```

## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

`CLICKUP_API_KEY` This is the platform we are using as project board for the app demo

`GITHUB_TOKEN` Github PAT to use the models from github marketplace

## App Demo

[![Watch the demo](https://github.com/Ankan54/scrum_n_coke/blob/main/assets/vantageaiscreen.JPG)](https://drive.google.com/file/d/1MWTzZaVP7_ApNZOL-85wIQNLSYfwU3Gr/view?usp=drivesdk)


## Authors

- [@Ankan Bera](https://www.github.com/Ankan54)
- [@Anand Vishnu](https://www.github.com/Nethereit)
- [@Arushi Gupta](https://www.github.com/arushigupta15)
- [@Amey Patil](https://www.github.com/amey-P)

