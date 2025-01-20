from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# So sieht eine folgständinge Abfrage aus: 
# http://127.0.0.1:8000/papers/title/llm?page=1&page_size=10&sort=date&descending=true
# einmal wird die gewünschte Seite spezifiziert, dann die Anzahl der geladenen Ergebnisse pro Seite
# Dann kann man eine Sortiertung angeben: relevance, views, date
# man kann auch descending order einstellen. Ist default auf false gesetzt.
# Default Anfrage ohne spezifizierung ist: page=1; page_size=15; keine Sortierung; descending=false

load_dotenv()

uri = os.getenv("MongoDB-uri")
db_name = os.getenv("db")

client = MongoClient(uri, server_api=ServerApi('1'))
db = client[db_name]

papers_collection = db["papers"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "pdfs")
IMAGE_DIR = os.path.join(BASE_DIR, "images")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/pdfs", StaticFiles(directory=PDF_DIR), name="pdfs")
app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")

@app.get("/")
def welcome():
    return "Hallo!"

# Paper-Klasse
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
    path_image: Optional[str] = None

# Mögliche Sortier-Felder (Mapping)
sort_fields = {
    "relevance": "relevance",
    "views": "views",
    "date": "published"
}

def dict_to_paper(paper_dict: dict) -> Paper:
    """
    Konvertiert ein Dictionary aus MongoDB in ein Paper-Objekt.
    """
    return Paper(
        title=paper_dict.get('title', 'unknown'),
        published=paper_dict.get('published'),
        authors=paper_dict.get('authors', []),
        relevance=paper_dict.get('relevance', 0),
        abstract=paper_dict.get('abstract', 'unknown'),
        citations=paper_dict.get('citations', 0),
        views=paper_dict.get('views', 0),
        content=paper_dict.get('content', 'unknown'),
        journal=paper_dict.get('journal', 'unknown'),
        path=paper_dict.get('path', 'no PDF existing'),
        path_image=paper_dict.get('path_image', 'no image found')
    )

def apply_sorting_and_pagination(
    query: dict,
    page: int,
    page_size: int,
    sort: Optional[str],
    descending: bool
):
    """
    Hilfsfunktion, die die Datenbank-Abfrage ausführt,
    Sortierung und Paginierung anwendet und die Resultate liefert.
    """
    skip = (page - 1) * page_size
    limit = page_size

    # Zuerst Count ermitteln
    total_count = papers_collection.count_documents(query)
    
    if total_count == 0:
        return ([], 0)

    # Sortierung vorbereiten
    sort_spec = None
    if sort and sort in sort_fields:
        sort_field = sort_fields[sort]
        sort_dir = DESCENDING if descending else ASCENDING
        sort_spec = [(sort_field, sort_dir)]

    if sort_spec:
        cursor = (papers_collection.find(query)
                  .sort(sort_spec)
                  .skip(skip)
                  .limit(limit))
    else:
        cursor = (papers_collection.find(query)
                  .skip(skip)
                  .limit(limit))
        
    return (list(cursor), total_count)

@app.get("/papers")
def papers():
    return "Hier werden als nächstes die Papers kommen"

@app.get("/papers/all")
def get_all_papers(
    page: int = 1,
    page_size: int = 15,
    sort: Optional[str] = None,
    descending: bool = False
):
    query = {}
    results, total = apply_sorting_and_pagination(query, page, page_size, sort, descending)

    # Wenn keine Treffer, HTTP 404 (kann man auch anders lösen)
    if not results:
        raise HTTPException(status_code=404, detail="No papers found.")

    return {
        "total_count": total,
        "page": page,
        "page_size": page_size,
        "papers": [dict_to_paper(r) for r in results]
    }

@app.get("/papers/author/{author_name}")
def get_papers_via_author(
    author_name: str,
    page: int = 1,
    page_size: int = 15,
    sort: Optional[str] = None,
    descending: bool = False
):
    """
    Liefert alle Papers für einen bestimmten Autor
    (case-insensitive Suche im Feld 'authors'),
    mit Paginierung & optionaler Sortierung.
    """
    query = {
        "authors": {
            "$regex": f".*{author_name}.*",
            "$options": "i"
        }
    }

    results, total = apply_sorting_and_pagination(query, page, page_size, sort, descending)

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No papers found for author '{author_name}'"
        )

    return {
        "total_count": total,
        "page": page,
        "page_size": page_size,
        "papers": [dict_to_paper(r) for r in results]
    }

@app.get("/papers/tag/{tag}")
def get_papers_via_tag(
    tag: str,
    page: int = 1,
    page_size: int = 15,
    sort: Optional[str] = None,
    descending: bool = False
):
    """
    Liefert alle Papers, die einen bestimmten Tag haben,
    mit Paginierung & optionaler Sortierung.
    """
    query = {"tag": tag}

    results, total = apply_sorting_and_pagination(query, page, page_size, sort, descending)

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No papers found for tag '{tag}'."
        )

    return {
        "total_count": total,
        "page": page,
        "page_size": page_size,
        "papers": [dict_to_paper(r) for r in results]
    }

@app.get("/papers/title/{title}")
def get_papers_via_title(
    title: str,
    page: int = 1,
    page_size: int = 15,
    sort: Optional[str] = None,
    descending: bool = False
):
    """
    Liefert alle Papers, die im 'title' den gesuchten String enthalten
    (case-insensitive),
    mit Paginierung & optionaler Sortierung.
    """
    query = {
        "title": {
            "$regex": f".*{title}.*",
            "$options": "i"
        }
    }
    results, total = apply_sorting_and_pagination(query, page, page_size, sort, descending)

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No papers found for title containing '{title}'."
        )
    
    return {
        "total_count": total,
        "page": page,
        "page_size": page_size,
        "papers": [dict_to_paper(r) for r in results]
    }

@app.get("/papers/content/{content}")
def get_papers_via_content(
    content: str,
    page: int = 1,
    page_size: int = 15,
    sort: Optional[str] = None,
    descending: bool = False
):
    """
    Neuer Endpunkt: sucht in 'content' nach dem gesuchten String (case-insensitive).
    """
    query = {
        "content": {
            "$regex": f".*{content}.*",
            "$options": "i"
        }
    }
    results, total = apply_sorting_and_pagination(query, page, page_size, sort, descending)

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No papers found for content containing '{content}'."
        )
    
    return {
        "total_count": total,
        "page": page,
        "page_size": page_size,
        "papers": [dict_to_paper(r) for r in results]
    }
