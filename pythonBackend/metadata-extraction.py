import xml.etree.ElementTree as ET
from pymongo import MongoClient
import gridfs
import requests
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF

load_dotenv()

uri = os.getenv("MongoDB-uri")

def extract_metadata_from_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    namespaces = {prefix: uri for event, (prefix, uri) in ET.iterparse(xml_file, events=['start-ns'])}

    papers = []
    for entry in root.findall(".//entry", namespaces=namespaces):
        paper = {
            "titel": entry.find("title", namespaces=namespaces).text,
            "authors": [author.find("name", namespaces=namespaces).text for author in entry.findall("author", namespaces=namespaces)],
            "published": entry.find("published", namespaces=namespaces).text if entry.find("published", namespaces=namespaces) is not None else None,
            "abstract": entry.find("summary", namespaces=namespaces).text if entry.find("summary", namespaces=namespaces) is not None else None,
            "citations": int(entry.find("citations", namespaces=namespaces).text) if entry.find("citations", namespaces=namespaces) is not None else 0,
            "relevance": 0,
            "pdf": None,
            "picture": "default_image_url.jpg",
            "content": None,
            "doi": entry.find("doi", namespaces=namespaces).text if entry.find("doi", namespaces=namespaces) else None,
            "journal": entry.find("journal", namespaces=namespaces).text if entry.find("journal", namespaces=namespaces) else None,
            "platforms": ["arXiv"],
            "views": 0
        }

        # PDF Link finden
        pdf_link = entry.find("link[@title='pdf']", namespaces=namespaces)
        if pdf_link is not None:
            paper["pdf"] = pdf_link.attrib['href']

        papers.append(paper)

    return papers

def save_pdf_to_gridfs(pdf_url, fs):
    pdf_content = requests.get(pdf_url).content
    pdf_id = fs.put(pdf_content, filename=pdf_url.split('/')[-1])
    
    # PDF-Text extrahieren
    with fitz.open(stream=pdf_content, filetype="pdf") as doc:
        content = ""
        for page in doc:
            content += page.get_text()
    
    return pdf_id, content

def save_to_mongodb(papers):
    client = MongoClient(uri)
    db = client["researchhub"]
    fs = gridfs.GridFS(db)
    collection = db["papers"]

    for paper in papers:
        if paper["pdf"]:
            pdf_id, content = save_pdf_to_gridfs(paper["pdf"], fs)
            paper["pdf_id"] = pdf_id
            paper["content"] = content
            del paper["pdf"]
        
        collection.insert_one(paper)
        print(f"Paper '{paper['titel']}' erfolgreich gespeichert.")

if __name__ == "__main__":
    papers = extract_metadata_from_xml("test.xml")
    print("Extracted Metadata:", papers)
    save_to_mongodb(papers)

       