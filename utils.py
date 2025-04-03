from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
from webdriver_manager.chrome import ChromeDriverManager
import chromadb
import logging 
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from agents import Runner
from settings import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
client = chromadb.PersistentClient(path=CHROMADB_PATH)

def scroll_and_scrape(url, max_jobs):
    # Configura il WebDriver di Chrome
    options = Options()
    options.headless = True  # Non aprire una finestra del browser
    driver = Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    driver.get(url)
    
    # Simula lo scroll verso il basso per caricare dinamicamente più offerte
    job_data = []
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while len(job_data) < max_jobs:
        # Trova i job links dalla pagina
        soup = BeautifulSoup(driver.page_source, "html.parser")
        page_jobs = soup.find_all('div', {'class': 'base-card'})  # Ora cerchiamo dentro questa div
        
        for job in page_jobs:
            job_url = job.find('a', {'class': 'base-card__full-link'})['href']  # Ottieni il link del lavoro
            logger.info("job_url")
            logger.info(job_url)
            if job_url and job_url not in [data['url'] for data in job_data]:  # Evita duplicati
                # Estrai il titolo, sottotitolo e location
                job_title = job.find('h3', {'class': 'base-search-card__title'})
                job_subtitle = job.find('h4', {'class': 'base-search-card__subtitle'})
                job_location = job.find('span', {'class': 'job-search-card__location'})
                
                # Rendi facoltativi gli elementi: Se non trovati, ritorna None
                job_title_text = job_title.get_text(strip=True) if job_title else None
                job_subtitle_text = job_subtitle.get_text(strip=True) if job_subtitle else None
                job_location_text = job_location.get_text(strip=True) if job_location else None
                
                # Aggiungi i dati al job_data
                job_data.append({
                    'url': job_url,
                    'title': job_title_text,
                    'subtitle': job_subtitle_text,
                    'location': job_location_text
                })
        
        # Scorri verso il basso
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Aumenta il tempo di attesa tra uno scroll e l'altro
        time.sleep(5)  # Attendi più a lungo per garantire che i nuovi contenuti vengano caricati
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:  # Se non c'è più contenuto da caricare, esci
            break
        last_height = new_height

    driver.quit()
    return job_data[:max_jobs]
    
def estrai_dati_completi(url):
    # Configura il driver in modalità headless
    options = ChromeOptions()
    options.add_argument('--headless')  # Esegui il browser in modalità headless
    options.add_argument('--disable-gpu')  # Evita errori GPU
    service = Service(ChromeDriverManager().install())
    driver = Chrome(service=service, options=options)
    
    try:
        driver.get(url)
        
        # Aspetta che il div principale (contenuto descrizione) venga caricato
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.show-more-less-html__markup"))
        )
        
        # Una pausa extra per sicurezza (se il contenuto è caricato dinamicamente)
        time.sleep(6)
        
        # Parsing del contenuto della pagina con BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Estrai la descrizione
        div_contenuto = soup.find('div', class_='show-more-less-html__markup')
        
        def estrai_testo(elemento):
            testo = ''
            if elemento.name in ['p', 'li']:
                testo += elemento.get_text(strip=True) + ' '
            elif elemento.name in ['ul', 'ol']:
                for item in elemento.find_all('li'):
                    testo += estrai_testo(item)
            for figlio in elemento.find_all(True, recursive=False):
                testo += estrai_testo(figlio)
            return testo
        
        descrizione = estrai_testo(div_contenuto).strip() if div_contenuto else "Descrizione non trovata."
        
        # Estrai i dati del "top card"
        container = soup.find('div', class_="top-card-layout__entity-info")
        dati_top_card = {}
        
        if container:
            title_elem = container.find('h1', class_="top-card-layout__title")
            dati_top_card["title"] = title_elem.get_text(strip=True) if title_elem else ""
            
            company_elem = container.find('a', class_="topcard__org-name-link")
            dati_top_card["company"] = company_elem.get_text(strip=True) if company_elem else ""
            
            first_row = container.find('div', class_="topcard__flavor-row")
            dati_top_card["place"] = ""
            if first_row:
                span_place = first_row.find('span', class_="topcard_flavor topcard_flavor--bullet")
                dati_top_card["place"] = span_place.get_text(strip=True) if span_place else ""
            
            date_elem = container.find('span', class_="posted-time-ago_text topcard_flavor--metadata")
            dati_top_card["date"] = date_elem.get_text(strip=True) if date_elem else ""
            
            candidates_elem = container.find('span', class_="num-applicants_caption topcardflavor--metadata topcard_flavor--bullet")
            dati_top_card["candidates"] = candidates_elem.get_text(strip=True) if candidates_elem else ""
        
        # Combina i dati in un dizionario finale
        risultato = {
            "description": descrizione,
            **dati_top_card
        }

        return risultato
    
    finally:
        driver.quit()

async def run_agent(agent, input_text, turn_count: int):
    if turn_count >= MAX_TURNS:
        logging.error("Superato il numero massimo di turni consentiti!")
        return None, turn_count
    turn_count += 1
    result = await Runner.run(agent, input_text, max_turns=MAX_TURNS - turn_count)
    #logging.info(result.__str__)
    logging.info(f"Output intermedio dopo {agent.name}: {result.final_output}")
    return result, turn_count

# Function to get the next available document ID
def get_next_doc_id(collection):
    documents = collection.get()
    if documents and "ids" in documents and documents["ids"]:
        return max(map(int, documents["ids"])) + 1
    return 1