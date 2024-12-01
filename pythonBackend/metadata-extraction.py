import xml.etree.ElementTree as ET
import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

uri = os.getenv("MongoDB-uri")


def extract_metadata(xml_file):
    
    # XML Datei parsen
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Namespace automatisch erkennen
    namespaces = {k: v for _, k, v in ET.iterparse(xml_file, events=['start-ns'])}

    # Dynamisch Metadaten extrahieren
    metadata = {
        "authors": [],
        "title": None,
        "published":None,
        "abstract": None,
        "citations": [],
    }


    # Autor(en) extrahieren
    for author in root.findall(".//author", namespaces=namespaces):
        name = author.find("name", namespaces=namespaces)
        if name is not None:
            metadata["authors"].append(name.text)


    # Titel extrahieren
    title = root.find(".//title", namespaces=namespaces)
    if title is not None:
        metadata["title"] = title.text


    # Veröffentlichungsdatum extrahieren
    published = root.find(".//published", namespaces=namespaces)
    if published is not None:
        metadata["published"] = published.text


    # Zusammenfassung extrahieren
    abstract = root.find(".//summary", namespaces=namespaces)
    if abstract is not None:
        metadata["abstract"] = abstract.text


    # Citations extrahieren
    for citation in root.findall(".//citation", namespaces=namespaces):
        if citation.text:
            metadata["citations"].append(citation.text) 


    return metadata           



def save_to_mongodb(metadata):
    # Verbindung zu MongoDB herstellen
    client = MongoClient(uri)
    db = client["researchhub"]
    collection = db["papers"]

    
    # Dokument einfügen
    collection.insert_one(metadata)
    print("Metadata successfully saved to MongoBB!")

