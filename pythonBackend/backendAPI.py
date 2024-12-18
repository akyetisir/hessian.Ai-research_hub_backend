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
    date: datetime
    authors: list[str]
    relevance: int
    tags: list[str]


@app.get("/papers/all", response_model=List[Paper])
def getAllPapers():
    papers_cursor = papers_collection.find()
    papers = list(papers_cursor)

    if papers:
        return [Paper( 
            title=paper['title'],
            date=paper['date'],
            authors=paper['authors'],
            relevance=paper['relevance'],
            tags=paper['tags']
            ) for paper in papers]
    else: 
        raise HTTPException(status_code=404, detail="no papers found.")
    
    
#Get-Anfrage für alle Paper die zu einem author gehören
@app.get("/papers/author/{author_name}", response_model=List[Paper])
def getPapersViaAuthor(author_name : str):
    papers_cursor = papers_collection.find({"authors": author_name}) #cursor (wie ein Iterator) wird zurückgegeben über den iteriert werden kann
    papers = list(papers_cursor) #liste wird erstellt aus dem Cursor

    if papers: #wenn es ein paper gibt dann
        #aus papers wird für jedes paper ein neues Paper Objekt erstellt, welches dann auch returnt wird
        return [Paper( 
            title=paper['title'],
            date=paper['date'],
            authors=paper['authors'],
            relevance=paper['relevance'],
            tags=paper['tags']
            ) for paper in papers]
    else: #404 wenn nicht gefunden
        raise HTTPException(status_code=404, detail=f"no papers found for author {author_name}.")
    
#Get-Anfrage für alle Paper mit einem speziefischen Tag    
@app.get("/papers/tag/{tag}", response_model=List[Paper])
def getPapersViaTag(tag : str):
    papers_cursor = papers_collection.find({"tags": tag}) 
    papers = list(papers_cursor)

    if papers:
        return[Paper(
            title=paper['title'],
            date=paper['date'],
            authors=paper['authors'],
            relevance=paper['relevance'],
            tags=paper['tags']
            ) for paper in papers]
    else:
        raise HTTPException(status_code=404, detail=f"no papers found for tag {tag}.")
    
#Get-Anfrage für alle Paper mit einem speziefischen Tag    
@app.get("/papers/title/{title}", response_model=List[Paper])
def getPapersViaTitle(title : str):
    papers_cursor = papers_collection.find({"title": title}) 
    papers = list(papers_cursor)

    if papers:
        return[Paper(
            title=paper['title'],
            date=paper['date'],
            authors=paper['authors'],
            relevance=paper['relevance'],
            tags=paper['tags']
            ) for paper in papers]
    else:
        raise HTTPException(status_code=404, detail=f"no papers found for tag {title}.")
    
#Test für das Abfragen der movies collection
class Movie(BaseModel):
    title: str
    year: int
    genres: List[str]

@app.get("/movies/{movie_title}", response_model=Movie)
def getMovies(movie_title : str):
    movie = movies_collection.find_one({"title": movie_title})
    if movie:
        return Movie(title=movie['title'], year=movie['year'], genres=movie['genres'])
    else:
        return {"error": "Movie not found"}
    
