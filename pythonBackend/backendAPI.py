from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
from pydantic import BaseModel
from typing import List
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

load_dotenv()

uri = os.getenv("MongoDB-uri")
db = os.getenv("db")

client = MongoClient(uri, server_api=ServerApi('1'))  # Hier die URI zur MongoDB-Datenbank

db = client[db]  # Aktueller Name der Sample DB. Muss später geändert werden. Ggf sollte wir den auch nicht hier
movies_collection = db["movies"]  #movies collection. Nur für Test
papers_collection = db["papers"]  #papers collection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "pdfs")

print("BASE_DIR:", BASE_DIR)
print("PDF_DIR:", PDF_DIR)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP
    allow_headers=["*"],  # Allows all headers
)


# "pdfs" ist der lokale Ordner; 
# "/pdfs" wird die URL, unter der die Dateien abrufbar sind.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "..", "pdfs")
app.mount("/pdfs", StaticFiles(directory=PDF_DIR), name="pdfs")

@app.get("/")
def welcome():
    return ("hallo")

#hier kann später auch was anders angezeigt werden wenn überhaupt
@app.get("/papers")
def papers():  
    return("hier werden als nächstes die Papers kommen")

#Paper Klasse definieren
class Paper(BaseModel):
    title: str
    published: Optional[datetime] = None
    authors: list[str]
    relevance: int
    abstract: str
    citations: int
    views: int
    content: str
    journal: Optional[str] = None
    path: Optional[str] = None
    #tags: list[str]


@app.get("/papers/all")
def get_all_papers(page: int = 1, page_size: int = 15):
    skip = (page - 1) * page_size
    limit = page_size

    # Abfrage
    papers_cursor = papers_collection.find().skip(skip).limit(limit)
    papers = list(papers_cursor)

    # Gesamtanzahl
    total_count = papers_collection.count_documents({})

    return {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "papers": [dict_to_paper(paper_dict) for paper_dict in papers]
    }

    
    
#Get-Anfrage für alle Paper die zu einem author gehören
@app.get("/papers/author/{author_name}")
def get_papers_via_author(
    author_name: str,
    page: int = 1,
    page_size: int = 15
):
    """
    Liefert alle Papers für einen bestimmten Autor,
    paginiert nach 'page' und 'page_size'.
    """

    # Anzahl Einträge überspringen
    skip = (page - 1) * page_size
    limit = page_size

    query = {
        "authors": {
            "$regex": f".*{author_name}.*",  
            "$options": "i"
        }
    }

    # Gesamtanzahl (um im Frontend z. B. die letzte Seite zu berechnen)
    total_count = papers_collection.count_documents(query)

    # Falls kein Dokument für diesen Autor existiert
    if total_count == 0:
        raise HTTPException(
            status_code=404, 
            detail=f"No papers found for author {author_name}."
        )

    # Nur einen Teil (page_size) zurückliefern
    papers_cursor = (
        papers_collection
        .find(query)
        .skip(skip)
        .limit(limit)
    )
    papers = list(papers_cursor)

    # Optional: Wenn 'page' so hoch ist, dass keine Ergebnisse mehr kommen,
    # könnte man hier ebenfalls 404 oder eine leere Liste zurückgeben.
    if not papers:
        raise HTTPException(
            status_code=404,
            detail=f"No papers found for author {author_name} on page {page}."
        )

    return {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "papers": [dict_to_paper(paper_dict) for paper_dict in papers]
    }

    
#Get-Anfrage für alle Paper mit einem speziefischen Tag    
@app.get("/papers/tag/{tag}", response_model=List[Paper])
def getPapersViaTag(
    tag : str,
    page: int = 1,
    page_size: int = 15
):
    skip = (page - 1) * page_size
    limit = page_size

    # Gesamtanzahl (um im Frontend z. B. die letzte Seite zu berechnen)
    total_count = papers_collection.count_documents({"tag": tag})

    if total_count == 0:
        raise HTTPException(
            status_code=404, 
            detail=f"No papers found for tag {tag}."
        )

    papers_cursor = (
        papers_collection
        .find({"tag": tag})
        .skip(skip)
        .limit(limit)
    )
    papers = list(papers_cursor)

    if not papers:
        raise HTTPException(status_code=404, detail=f"no papers found for tag {tag}.")
    
    return {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "papers": [dict_to_paper(paper_dict) for paper_dict in papers]
    }
    
#Get-Anfrage für alle Paper mit einem speziefischen Tag    
@app.get("/papers/title/{title}")
def get_papers_via_title(
    title: str,
    page: int = 1,
    page_size: int = 15
):
    """
    Liefert alle Papers mit 'title'-Substring (teilweise Suche),
    paginiert nach 'page' und 'page_size'.
    Groß-/Kleinschreibung wird ignoriert (case-insensitive).
    """

    skip = (page - 1) * page_size
    limit = page_size

    # Regex für Teiltextsuche (.*title.* => "title" kommt irgendwo im String vor)
    # "$options": "i" => case-insensitive
    query = {
        "title": {
            "$regex": f".*{title}.*",  
            "$options": "i"
        }
    }

    total_count = papers_collection.count_documents(query)

    if total_count == 0:
        raise HTTPException(
            status_code=404, 
            detail=f"No papers found for title containing '{title}'."
        )

    papers_cursor = (
        papers_collection
        .find(query)
        .skip(skip)
        .limit(limit)
    )
    papers = list(papers_cursor)

    # Optional: Wenn 'page' so hoch ist, dass keine Ergebnisse mehr kommen:
    if not papers:
        raise HTTPException(
            status_code=404,
            detail=f"No papers found for title containing '{title}' on page {page}."
        )

    return {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "papers": [dict_to_paper(paper_dict) for paper_dict in papers]
    }

    
    

def dict_to_paper(paper_dict: dict) -> Paper:
    """
    Konvertiert ein Dictionary aus MongoDB in ein Paper-Objekt.
    Fehlende Felder werden mit Defaultwerten oder None gefüllt.
    """
    return Paper(
        title=paper_dict.get('title', 'unknown'),
        published=paper_dict.get('published'),  # falls optional im Modell
        authors=paper_dict.get('authors', []),
        relevance=paper_dict.get('relevance', 0),
        abstract=paper_dict.get('abstract', 'unknown'),
        citations=paper_dict.get('citations', 0),
        views=paper_dict.get('views', 0),
        content=paper_dict.get('content', 'unknown'),
        journal=paper_dict.get('journal', 'unknown'),
        path=paper_dict.get('path','no PDF existing')
    )

