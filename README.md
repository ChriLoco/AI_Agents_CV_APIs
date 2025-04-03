WHAT IS THIS    
-----------------------

It's a little Python FastAPI server you can run locally that allows you to:

1) Scrape Linkedin's jobs you like (beautifulsoup + selenium)
2) Add personal information to a local vectordb (chromadb)
3) Run an agentic environment that adapts the cv template you like to the job description you like taking personal information you have put into vectordb

and once you configure settings' paths and (eventually) agents' prompts, you have to pass the url to the CV api and that's it.

result is a latex file


WHY THIS      
----------------------

It's no secret people nowadays use LLMs to adapt CV to Job applications. Problem is, when the conversation with the LLM becomes longer than LLM ability to remember it (aka context window)
it looks like it starts forgetting stuff, making you waste time. 

Also for extensive CV spamming sessions you have to copy paste same stuff into new chats and it becomes boring. After a certain point i believe giving 10 dollars for token consumption to
Sam Altman can positvely benefit your time and mental health. 

This is achieved by saving once for all your past experiences, skills, academic milestones, etc. into a vectordb and retrieving it contextually.

Fork it, leave a star pls ⭐. You can modify it, steal it, love it, hate, got it.

HOW TO USE THIS FAST 
------------------------

1) You install requirements (eventually into an env):

   `pip install -r requirements.txt`

2) You modify some variables into the "settings.py" file 

  CHROMADB_PATH --> i suggest you the same working directory in which you forked everything
  
  USER_PROMPTS --> additional commands you can give, USER_PROMPTS[i] is sent to i-1(th) Agent
  
  AGENT_1, AGENT_2, AGENT_3, AGENT_4 --> they can be modified to experiment new purposes

3) You set your openai key:
   
   `$env:OPENAI_API_KEY="{YOUR OPENAI API KEY}"`

4) put this into browser:
   `http://127.0.0.1:8080/docs`

API DESCRIPTION   
------------------------

### **1. Job Data Collection APIs**
#### **`/jobs/get_list`**  
- **Input:** `ScrapeRequest`
  - `location`: Job search location  
  - `job`: Job title/keywords  
  - `max_jobs`: Max number of job listings to scrape (default: 10)  
- **Output:**  
  - A JSON list of scraped job postings  
  - An Excel file (`job_offers.xlsx`) with the scraped data  

#### **`/jobs/upload_job`**  
- **Input:**  
  - A **LinkedIn job URL** (as a string)  
- **Output:**  
  - Extracted job data in **`Job`** format:  
    - `title`, `place`, `company`, `date`, `description`  

---

### **2. Personal Data Management APIs**
#### **`/my_data/add/`**  
- **Input:** `Document`
  - Stores personal details like work/academic experience  
- **Output:**  
  - Confirmation message that the document was added  

#### **`/my_data/update/`**  
- **Input:** `UpdateDocument`
  - `doc_id`: ID of the document to update  
  - `new_doc_text`: Updated content  
  - `new_metadata`: Updated metadata (including title, location, etc.)  
- **Output:**  
  - Confirmation message  

#### **`/my_data/delete/`**  
- **Input:** `DeleteRequest`
  - `doc_id`: ID of the document to delete  
- **Output:**  
  - Confirmation message  

#### **`/my_data/semantic_search/`**  
- **Input:** `Query`
  - `query_text`: The search query  
  - `top_k`: Number of results to return (default: 5)  
- **Output:**  
  - A list of matching documents from the vector database  

#### **`/my_data/get_list/`**  
- **Output:**  
  - Returns **all** stored documents with metadata  

---

### **3. CV Processing API**
#### **`/process_cv/`**  
- **Input:** `CVInput`
  - `url`: LinkedIn job post URL  
- **Process:**  
  1. Fetches job details (`Job`) using `/jobs/upload_job`  
  2. Searches for personal info in the database using `PersonalInformationTool`  
  3. Runs a **multi-step AI process** to generate a **personalized CV**  
- **Output:**  
  - Returns the **final optimized CV** as text  

---

