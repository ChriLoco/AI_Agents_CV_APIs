from pydantic import BaseModel
from agents import Agent, WebSearchTool, ModelSettings, function_tool
from typing import List, Optional, Literal

# Job Scraping information
LOCATION = "Australia"
N_JOBS_TO_ANALIZE=3
#URL = f"https://www.linkedin.com/jobs/search?keywords=Python%20Developer&location=Australia"

CHROMADB_PATH = "C:\\Users\\christian.loconsole\\OneDrive - LUTECH SPA\\Desktop\\interface_italgas\\mytools\\scripts\\experiment"
MAX_TURNS = 10

# Additional commands you can give, USER_PROMPTS[i] is sent to i-1(th) Agent
USER_PROMPTS=[
    "- You should give as output just the CV without any explanation",
    "- You should give as output just the CV without any explanation.",
    "- Ensure the CV looks natural and not AI-generated. - You should give as output just the CV without any explanation",
    "Refine the wording for better readability and impact. - You should give as output just the CV without any explanation"
]

# Agents
AGENT_4 = Agent(name="Refiner", instructions="You refine CV following user indications", model="gpt-4o-mini")


#I HAD TO MOVE AGENT_1 IN THE main.py due to some lissue with decorator @function_tool
'''AGENT_1 = Agent(
    name="Contextualizer",
    instructions="You adapt the CV template to Job Description using candidate personal information",
    model="gpt-4o-mini",
    tools=[PersonalInformationTool],
    model_settings=ModelSettings(temperature=0.1))'''

AGENT_2 = Agent(
    name="Project Liar", 
    instructions=f"You search in internet the company values and scope. Add a project called 'PROJECT X' that would suit the purpose of that specific company", 
    model="gpt-4o-mini", 
    tools=[WebSearchTool()], 
    model_settings=ModelSettings(tool_choice=WebSearchTool().name, temperature=0.1))

AGENT_3 = Agent(name="AI Reducer", instructions="Make it less AI-generated", model="gpt-4o-mini")

class CVInput(BaseModel):
    user_prompts: Optional[List[str]] = None
    url: str

class ScrapeRequest(BaseModel):
    location: str
    job: str
    max_jobs: int = 10  

class Job(BaseModel):
    title: str
    place: str
    company: str
    date: str
    description: str

class Document(BaseModel):
    doc_text: str
    doc_type: Literal["ACADEMIC_EXPERIENCE", "WORK_EXPERIENCE", "OTHER"]
    #doc_date: str  
    location: str  
    title: str  

class UpdateDocument(BaseModel):
    doc_id: int
    new_doc_text: str
    new_metadata: dict

class Query(BaseModel):
    query_text: str
    top_k: int = 5

class DeleteRequest(BaseModel):
    doc_id: int