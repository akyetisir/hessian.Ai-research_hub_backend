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
from bson import ObjectId

# So sieht eine vollständige Abfrage aus:
# http://127.0.0.1:8000/papers/title/llm?page=1&page_size=10&sort=date&descending=true
# - page: gewünschte Seite
# - page_size: Anzahl Ergebnisse pro Seite
# - sort: "relevance", "views", oder "date"
# - descending: true/false

load_dotenv()

uri = os.getenv("MongoDB-uri")
db_name = os.getenv("db")

client = MongoClient(uri, server_api=ServerApi('1'))
db = client[db_name]

papers_collection = db["papers"]
authors_collection = db["authors"]

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

# ---------------------------------------
# PAPIER-DATENSTRUKTUR
# ---------------------------------------

class Paper(BaseModel):
    """
    Pydantic-Modell für ein Paper, mit optionalen und Standardwerten,
    damit fehlende Felder keine Fehler erzeugen.
    """
    title: str
    published: Optional[datetime] = None
    authors: List[str]
    relevance: int = 0
    abstract: str = "unknown"
    # Ursprüngliches Feld "citations":
    citations: int = 0
    views: int = 0
    content: str = "unknown"
    journal: Optional[str] = "unknown"
    path: Optional[str] = "no PDF existing"
    path_image: Optional[str] = "no image found"
    # Neue Felder (aus Semantic Scholar) – optional, Standard=0:
    citationCount: int = 0
    highlyInfluentialCitations: int = 0

# Mögliche Sortier-Felder (Mapping)
sort_fields = {
    "relevance": "relevance",
    "views": "views",
    "date": "published"
}

def dict_to_paper(paper_dict: dict) -> Paper:
    """
    Konvertiert ein Dictionary aus MongoDB in ein Paper-Objekt (Pydantic).
    Felder, die nicht existieren, bekommen ihre Defaults.
    """
    return Paper(
        title=paper_dict.get('title', 'unknown'),
        published=paper_dict.get('published', None),
        authors=paper_dict.get('authors', []),
        relevance=paper_dict.get('relevance', 0),
        abstract=paper_dict.get('abstract', 'unknown'),
        citations=paper_dict.get('citations', 0),  # Altes Feld
        views=paper_dict.get('views', 0),
        content=paper_dict.get('content', 'unknown'),
        journal=paper_dict.get('journal', 'unknown'),
        path=paper_dict.get('path', 'no PDF existing'),
        path_image=paper_dict.get('path_image', 'no image found'),
        citationCount=paper_dict.get('citationCount', 0),
        highlyInfluentialCitations=paper_dict.get('highlyInfluentialCitations', 0)
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

    total_count = papers_collection.count_documents(query)

    if total_count == 0:
        return ([], 0)

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

# ---------------------------------------
# PAPERS ENDPOINTS
# ---------------------------------------

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
    Sucht nach Papers, die ein Feld "tag" mit passendem Wert haben.
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
    Sucht nach Papers, deren "title" den gesuchten String enthält.
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
    Sucht in "content" nach dem String (case-insensitive).
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

# ---------------------------------------
# AUTHORS ENDPOINTS
# ---------------------------------------

def author_doc_to_dict(author_doc) -> dict:
    """
    Wandelt das MongoDB-Dokument eines Autors in ein ausgabefreundliches Dictionary um,
    konvertiert _id -> string und IGNORIERT das Feld 'papers'.
    """
    return {
        "objectId": str(author_doc["_id"]),  # _id als String
        "name": author_doc.get("name", ""),
        "h_index": author_doc.get("h_index", 0),
        "citations": author_doc.get("citations", 0),
        "highly_influential_citations": author_doc.get("highly_influential_citations", 0),
        "image_path": author_doc.get("image_path", "images/placeholder_author.png")
    }


@app.get("/authors/{author_name}")
def get_author_by_name(author_name: str):
    """
    Sucht (case-insensitive) nach einem Autor mit passendem Namen.
    Gibt das komplette Dokument inkl. objectId zurück.
    """
    # Exakte Suche (case-insensitive), d.h. "Stefan Roth" findet "Stefan Roth",
    #   aber nicht "Stefan Rother".
    # Entferne ^ und $, wenn du Teilstring-Suche möchtest.
    regex_query = {
        "name": {
            "$regex": f"^{author_name}$",
            "$options": "i"
        }
    }
    author_doc = authors_collection.find_one(regex_query)

    if not author_doc:
        raise HTTPException(status_code=404, detail=f"No author found for name '{author_name}'")

    return author_doc_to_dict(author_doc)

@app.get("/authors/objnr/{obj_id}")
def get_author_by_objectid(obj_id: str):
    """
    Sucht nach einem Autor mit bestimmter MongoDB-ObjektID.
    Gibt das komplette Dokument zurück.
    """
    try:
        oid = ObjectId(obj_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format.")

    author_doc = authors_collection.find_one({"_id": oid})
    if not author_doc:
        raise HTTPException(
            status_code=404,
            detail=f"No author found for _id '{obj_id}'"
        )

    return author_doc_to_dict(author_doc)
