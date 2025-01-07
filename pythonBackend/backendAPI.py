from fastapi import FastAPI
from fastapi import HTTPException
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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP
    allow_headers=["*"],  # Allows all headers
)

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


@app.get("/papers/all", response_model=List[Paper])
def get_all_papers():
    papers_cursor = papers_collection.find()
    papers = list(papers_cursor)

    if not papers:
        raise HTTPException(status_code=404, detail="No papers found.")

    return [dict_to_paper(paper_dict) for paper_dict in papers]

    
    
#Get-Anfrage für alle Paper die zu einem author gehören
@app.get("/papers/author/{author_name}", response_model=List[Paper])
def get_papers_via_author(author_name: str):
    papers_cursor = papers_collection.find({"authors": author_name})
    papers = list(papers_cursor)

    if not papers:
        raise HTTPException(status_code=404, detail=f"No papers found for author {author_name}.")

    return [dict_to_paper(paper_dict) for paper_dict in papers]

    
#Get-Anfrage für alle Paper mit einem speziefischen Tag    
@app.get("/papers/tag/{tag}", response_model=List[Paper])
def getPapersViaTag(tag : str):
    papers_cursor = papers_collection.find({"tags": tag}) 
    papers = list(papers_cursor)

    if not papers:
        raise HTTPException(status_code=404, detail=f"no papers found for tag {tag}.")
    
    return [dict_to_paper(paper_dict) for paper_dict in papers]
    
#Get-Anfrage für alle Paper mit einem speziefischen Tag    
@app.get("/papers/title/{title}", response_model=List[Paper])
def getPapersViaTitle(title : str):
    papers_cursor = papers_collection.find({"title": title}) 
    papers = list(papers_cursor)

    if not papers:
        raise HTTPException(status_code=404, detail=f"no papers found for tag {title}.")
    
    return [dict_to_paper(paper_dict) for paper_dict in papers]
    
    

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

