from bs4 import BeautifulSoup
import pandas as pd
import os
from utils import *
from settings import *
import requests
from fastapi import FastAPI, HTTPException

'''
IF THE @function_tool function is imported from settings sheet, won't work
WHY?

I'll drop them below
'''

def get_chromadb_collection():
    collection_name = "documents_collection"
    if collection_name not in client.list_collections():
        return client.create_collection(name=collection_name)
    return client.get_collection(collection_name)

@function_tool  
def PersonalInformationTool(query: str) -> str:
    """Fetch the Personal Information of the candidate

    Args:
        query: The query used to search similar content into vector db
    """
    try:
        collection = get_chromadb_collection()
        results = collection.query(query_texts=[query], n_results=5)
        
        formatted_results = ""
        for i in range(len(results["ids"][0])):
            doc_text = results["documents"][0][i] if results["documents"] else None
            formatted_results+=f"\n\nRelevant information n.{str(i)}:\n\n---\n\n{doc_text}\n\n---\n\n"

        return formatted_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
AGENT_1 = Agent(
    name="Contextualizer",
    instructions="You adapt the CV template to Job Description using candidate personal information",
    model="gpt-4o-mini",
    tools=[PersonalInformationTool],
    model_settings=ModelSettings(temperature=0.1))

# Crea un'app FastAPI
app = FastAPI()

# Endpoint per fare scraping dei post
@app.post("/jobs/get_list", tags=["jobs"])
async def scrape_linkedin_all(request: ScrapeRequest):
    try:
        job=(request.job).replace(" ", "%20")
        url=f"https://www.linkedin.com/jobs/search?keywords={job}&location={request.location}"
        job_data = scroll_and_scrape(url, request.max_jobs)
        
        # Lista per raccogliere i dati aggiuntivi
        data = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        }
        
        # Fai una richiesta GET per ogni URL del post e prendi la descrizione
        for job in job_data:
            job_url = job['url']
            job_response = requests.get(job_url, headers=headers)
            
            if job_response.status_code == 200:
                job_soup = BeautifulSoup(job_response.text, "html.parser")
                description_section = job_soup.find('div', {'class': 'description_text description_text--rich'})
                
                if description_section:
                    job_description = description_section.get_text(strip=True, separator=" ")
                else:
                    job_description = "Descrizione non trovata"
                
                # Aggiungi la descrizione ai dati esistenti
                job['description'] = job_description
                data.append(job)
            else:
                data.append({**job, "description": "Errore durante la richiesta del post"})
        
        # Salva i dati in un file Excel
        df = pd.DataFrame(data)
        file_path = "job_offers.xlsx"
        df.to_excel(file_path, index=False)
        
        # Restituisci i risultati come JSON con il link al file
        return {"data": data, "file": os.path.abspath(file_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante lo scraping: {str(e)}")

@app.post("/jobs/upload_job", tags=["jobs"])
async def upload_job(job_url: str):
    try:
        if "linkedin" in job_url:
            # Chiamata alla funzione che esegue lo scraping della pagina LinkedIn
            job_data = estrai_dati_completi(job_url)

            job_data=Job(
                title= job_data["title"],
                place= job_data["place"],
                company= job_data["company"],
                date= job_data["date"],
                candidates=job_data["candidates"],
                description= job_data["description"])
            
            # Restituisci i dati estratti come JSON
            return job_data
        
        # Se l'URL non contiene "linkedin"
        raise HTTPException(status_code=400, detail="URL non valido, deve essere un URL di LinkedIn.")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante lo scraping: {str(e)}")
    

@app.post("/my_data/add/", tags=["my_data"])
def add_document(doc: Document):
    try:
        collection = get_chromadb_collection()
        doc_id = get_next_doc_id(collection)  # Automatically assign the next available ID
        
        '''# Parse the doc_date string into a list using json.loads
        try:
            date_list = json.loads(doc.doc_date.replace('/', '-'))  # Replace '/' with '-' to avoid issues
            if not isinstance(date_list, list) or len(date_list) != 2:
                raise ValueError("doc_date must be a string representing a list of exactly two elements.")
            doc_date_str = str(date_list)  # Convert back to string
        except json.JSONDecodeError:
            raise ValueError("Invalid format for doc_date. Must be a string representing a list of two dates.")'''
        
        # Include the new "title" field in the metadata
        metadata = {
            "id": doc_id,
            "type": doc.doc_type,
            #"date": doc_date_str,
            "location": doc.location,
            "title": doc.title  # Add the title field
        }
        collection.add(documents=[doc.doc_text], metadatas=[metadata], ids=[str(doc_id)])
        return {"message": f"Document with ID {doc_id} added successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/my_data/update/", tags=["my_data"])
def update_document(update: UpdateDocument):
    try:
        collection = get_chromadb_collection()
        # Update the document text and metadata (including the title if provided)
        collection.update(ids=[str(update.doc_id)], documents=[update.new_doc_text], metadatas=[update.new_metadata])
        return {"message": f"Document with ID {update.doc_id} updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/my_data/delete/", tags=["my_data"])
def delete_document(request: DeleteRequest):
    try:
        collection = get_chromadb_collection()
        collection.delete(ids=[str(request.doc_id)])
        return {"message": f"Document with ID {request.doc_id} deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/my_data/semantic_search/", tags=["my_data"])
def semantic_search(query: Query):
    try:
        collection = get_chromadb_collection()
        results = collection.query(query_texts=[query.query_text], n_results=query.top_k)
        
        formatted_results = []
        for i in range(len(results["ids"][0])):
            doc_id = results["ids"][0][i]
            doc_text = results["documents"][0][i] if results["documents"] else None
            doc_metadata = results["metadatas"][0][i] if results["metadatas"] else None
            doc_distance = results["distances"][0][i] if results["distances"] else None
            
            formatted_results.append({
                "id": doc_id,
                "document": doc_text,
                "metadata": doc_metadata,
                "distance": doc_distance
            })
        
        return formatted_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/my_data/get_list/", tags=["my_data"])
def get_collection_content():
    try:
        collection = get_chromadb_collection()
        documents = collection.get()
        
        # Rimappa i documenti nel formato desiderato
        formatted_documents = []
        for i in range(len(documents["ids"])):
            doc_id = documents["ids"][i]
            doc_text = documents["documents"][i]
            doc_metadata = documents["metadatas"][i]
            
            formatted_documents.append({
                "id": doc_id,
                "document": doc_text,
                "metadata": doc_metadata
            })
        
        return formatted_documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process_cv/")
async def process_cv(input_data: CVInput):
    """
    Processa il CV in base alla descrizione del lavoro
    
    Args:
        input_data: Oggetto contenente ambito, user_prompts e url
    """
    try:
        # Carica il contenuto del file cv.tex
        with open("cv.tex", "r", encoding="utf-8") as file:
            context = file.read()


        job_data = await upload_job(input_data.url)

        input_text = f"""
        Follow this style of CVs ignoring the content itself:
        {context}

        JOB DESCRIPTION you have to adapt to, using only the information taken from Personal Information Tool:
        {job_data.description}

        Search up for personal information to be used into CV writing
        """

    
        USER_PROMPTS[1] += f"- The company name to search on the internet is {job_data.company}"

        turn_count = 0
        result_1, _ = await run_agent(AGENT_1, input_text + "\n" + USER_PROMPTS[0], turn_count)
        if result_1 is None: return "AGENT_1 error"
        turn_count += 1 
        result_2, _ = await run_agent(AGENT_2, result_1.final_output + "\n" + USER_PROMPTS[1], turn_count)
        if result_2 is None: return "AGENT_2 error"
        turn_count += 1  
        result_3, _ = await run_agent(AGENT_3, result_2.final_output + "\n" + USER_PROMPTS[2], turn_count)
        if result_3 is None: return "AGENT_3 error"
        turn_count += 1  
        final_result, _ = await run_agent(AGENT_4, result_3.final_output + "\n" + USER_PROMPTS[3], turn_count)
        if final_result is None: return "AGENT_0 error"

        return {"processed_cv": result_1.final_output}
    except Exception as e:
        logging.error(f"Running error: {e}")
        return {"error": str(e)}
    


