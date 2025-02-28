from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
from pydantic import BaseModel
from typing import List, Optional
# from datetime import datetime
from bson import ObjectId

# So sieht eine vollständige Abfrage aus:
#  http://127.0.0.1:8000/papers/title/llm?page=1&page_size=10&sort=date&descending=true
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
# PAPER-DATENSTRUKTUR
# ---------------------------------------

class Paper(BaseModel):
    """
    Pydantic-Modell für ein Paper, mit optionalen Standardwerten.
    Fehlende Felder in MongoDB erzeugen keine Fehler.
    """
    title: str
    published: str = ""
    authors: List[str] = []
    relevance: int = 0
    abstract: str = "unknown"
    citations: int = 0
    views: int = 0
    content: str = "unknown"
    journal: Optional[str] = "unknown"
    path: Optional[str] = "no PDF existing"
    path_image: Optional[str] = "no image found"
    is_hess_paper: str = ""
    # Felder aus Semantic Scholar
    citationCount: int = 0
    highlyInfluentialCitations: int = 0

# Mögliche Sortier-Felder (Mapping)
sort_fields = {
    "relevance": "relevance",
    "views": "views",
    "date": "published"
}

def replaceNoneTypes(field, replacer):
    if field == None:
        return replacer
    else:
        return field

def dict_to_paper(paper_dict: dict) -> Paper:
    """
    Konvertiert ein Dictionary aus MongoDB in ein Paper-Objekt (Pydantic).
    """
    if not type(paper_dict['abstract']) is str:
        print(f"type: {type(paper_dict['abstract'])}")
        print(f"type: {paper_dict['abstract'] == None }")

    # not all papers are from semantic scholar and thus have these fields
    if not "citationCount" in paper_dict:
        paper_dict.update({"citationCount": 0})
    if not "highlyInfluentialCitations" in paper_dict:
        paper_dict.update({"highlyInfluentialCitations": 0})


    return Paper(
        title= replaceNoneTypes(paper_dict['title'], 'unknown'),
        published=replaceNoneTypes(paper_dict['published'], ""),
        authors=replaceNoneTypes(paper_dict['authors'], []),
        relevance=replaceNoneTypes(paper_dict['relevance'], 0),
        abstract=replaceNoneTypes(paper_dict['abstract'], 'unknown'),
        citations=replaceNoneTypes(paper_dict['citations'], 0),
        views=replaceNoneTypes(paper_dict['views'], 0),
        content=replaceNoneTypes(paper_dict['content'], 'unknown'),
        journal=replaceNoneTypes(paper_dict['journal'], 'unknown'),
        path=replaceNoneTypes(paper_dict['path'], 'no PDF existing'),
        path_image=replaceNoneTypes(paper_dict['path_image'], 'no image found'),
        citationCount=replaceNoneTypes(paper_dict['citationCount'], 0),
        highlyInfluentialCitations=replaceNoneTypes(paper_dict['highlyInfluentialCitations'], 0)
    )


def build_filter_query(
    query, 
    year: Optional[List[int]] = Query(None),
    min_views: int = 0,  
    max_views: Optional[int] = None,
    min_citations: int = 0,  
    max_citations: Optional[int] = None,
    # min_hi_citations: int = 0,  
    # max_hi_citations: Optional[int] = None
    ):

    query.update({"published": { "$ne" : "null" }})
    
    if year:
        query.update({"$or": [{"published": {"$regex": f"{y}" }}for y in year]})
    if max_views:
        query.update({"views": {"$gte": min_views, "$lte": max_views}})
    if max_citations:
        query.update({"citations": {"$gte": min_citations, "$lte": max_citations}})
    # if max_hi_citations:
    #     query.update({"highlyInfluentialCitations": {"$gte": min_hi_citations, "$lte": max_hi_citations}})

    return query

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
        cursor = (
            papers_collection.find(query)
            .sort(sort_spec)
            .skip(skip)
            .limit(limit)
        )
    else:
        cursor = (
            papers_collection.find(query)
            .skip(skip)
            .limit(limit)
        )

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
    descending: bool = False,
    year: Optional[List[int]] = Query(None),
    min_views: int = 0,  
    max_views: Optional[int] = None,
    min_citations: int = 0,  
    max_citations: Optional[int] = None
):
    query = {}

    # update query
    query = build_filter_query(query, year, min_views, max_views, min_citations, max_citations) # , min_hi_citations, max_hi_citations)


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
    descending: bool = False,
    year: Optional[List[int]] = Query(None),
    min_views: int = 0,  
    max_views: Optional[int] = None,
    min_citations: int = 0,  
    max_citations: Optional[int] = None #,
#    min_hi_citations: int = 0,  
#    max_hi_citations: Optional[int] = None
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

    # update query
    query = build_filter_query(query, year, min_views, max_views, min_citations, max_citations) # , min_hi_citations, max_hi_citations)

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
    descending: bool = False,
    year: Optional[List[int]] = Query(None),
    min_views: int = 0,  
    max_views: Optional[int] = None,
    min_citations: int = 0,  
    max_citations: Optional[int] = None #,
#    min_hi_citations: int = 0,  
#    max_hi_citations: Optional[int] = None
):
    """
    Sucht nach Papers, die ein Feld "tag" mit passendem Wert haben.
    """
    query = {"tag": tag}
    # update query
    query = build_filter_query(query, year, min_views, max_views, min_citations, max_citations) # , min_hi_citations, max_hi_citations)
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
    descending: bool = False,
    year: Optional[List[int]] = Query(None),
    min_views: int = 0,  
    max_views: Optional[int] = None,
    min_citations: int = 0,  
    max_citations: Optional[int] = None #,
#    min_hi_citations: int = 0,  
#    max_hi_citations: Optional[int] = None
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
    # update query
    query = build_filter_query(query, year, min_views, max_views, min_citations, max_citations) # , min_hi_citations, max_hi_citations)
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
    descending: bool = False,
    year: Optional[List[int]] = Query(None),
    min_views: int = 0,  
    max_views: Optional[int] = None,
    min_citations: int = 0,  
    max_citations: Optional[int] = None #,
#    min_hi_citations: int = 0,  
#    max_hi_citations: Optional[int] = None
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
    # update query
    query = build_filter_query(query, year, min_views, max_views, min_citations, max_citations) # , min_hi_citations, max_hi_citations)
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
# AUTHORS: Pydantic-Model & Endpunkte
# ---------------------------------------

# A) Modell für einen einzelnen Autor (ohne "papers")
class AuthorModel(BaseModel):
    objectId: str
    name: str
    h_index: int = 0
    citations: int = 0
    highly_influential_citations: int = 0
    image_path: str = "images/placeholder_author.png"

# B) Modell für paginierte Antwort
class AuthorsPaginationResponse(BaseModel):
    total_count: int
    page: int
    page_size: int
    authors: List[AuthorModel]

def author_doc_to_model(doc: dict) -> AuthorModel:
    """
    Wandelt ein Autor-Dokument in ein AuthorModel um.
    papers wird ignoriert.
    """
    return AuthorModel(
        objectId=str(doc["_id"]),
        name=doc.get("name", ""),
        h_index=doc.get("h_index", 0),
        citations=doc.get("citations", 0),
        highly_influential_citations=doc.get("highly_influential_citations", 0),
        image_path=doc.get("image_path", "images/placeholder_author.png")
    )

@app.get("/authors/{author_name}", response_model=AuthorModel)
def get_author_by_name(author_name: str):
    """
    Sucht (case-insensitive) nach einem Autor mit passendem Namen.
    Gibt das Ergebnis als AuthorModel zurück.
    """
    # Exakte Suche (case-insensitive); entferne ^ und $, wenn du Teilstring-Suche möchtest.
    regex_query = {
        "name": {
            "$regex": f"^{author_name}$",
            "$options": "i"
        }
    }
    author_doc = authors_collection.find_one(regex_query)

    if not author_doc:
        raise HTTPException(status_code=404, detail=f"No author found for name '{author_name}'")

    return author_doc_to_model(author_doc)

@app.get("/authors", response_model=AuthorsPaginationResponse)
def get_all_authors(
    page: int = 1,
    page_size: int = 15,
    sort: Optional[str] = None,
    descending: bool = False
):
    """
    Gibt eine paginierte Liste aller Autoren zurück, mit optionaler Sortierung.
    """
    skip = (page - 1) * page_size
    limit = page_size

    # Mögliche Sortierfelder
    sort_fields_authors = {
        "name": "name",
        "h_index": "h_index",
        "citations": "citations",
        "highly_influential_citations": "highly_influential_citations"
    }

    total_count = authors_collection.count_documents({})

    if total_count == 0:
        raise HTTPException(status_code=404, detail="No authors found")

    sort_spec = None
    if sort and sort in sort_fields_authors:
        sort_field = sort_fields_authors[sort]
        sort_dir = DESCENDING if descending else ASCENDING
        sort_spec = [(sort_field, sort_dir)]

    if sort_spec:
        cursor = authors_collection.find({}).sort(sort_spec).skip(skip).limit(limit)
    else:
        cursor = authors_collection.find({}).skip(skip).limit(limit)

    author_docs = list(cursor)
    authors_list = [author_doc_to_model(doc) for doc in author_docs]

    return AuthorsPaginationResponse(
        total_count=total_count,
        page=page,
        page_size=page_size,
        authors=authors_list
    )

@app.get("/authors/objnr/{obj_id}", response_model=AuthorModel)
def get_author_by_objectid(obj_id: str):
    """
    Sucht nach einem Autor mit bestimmter MongoDB-ObjektID.
    Gibt das komplette Dokument zurück (als AuthorModel).
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

    return author_doc_to_model(author_doc)
