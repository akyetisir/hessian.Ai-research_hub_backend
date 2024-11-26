from fastapi import FastAPI
import httpx
from xml.etree import ElementTree

app = FastAPI()

@app.get("/papers/")
async def get_papers(author: str, max_results: int = 15):
    # URL für die arXiv-API
    url = f'http://export.arxiv.org/api/query?search_query=all:{author}&start=0&max_results={max_results}'
    
    # HTTP-Anfrage mit httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    # Wenn Antwort erfolgreich
    if response.status_code == 200:
        # Speichern der XML-Daten in einer Datei
        xml_filename = f"papers_{author}.xml"
        with open(xml_filename, "w", encoding="utf-8") as file:
            file.write(response.text)
        print(f"XML-Datei erfolgreich gespeichert: {xml_filename}")

        # Optional: PDFs herunterladen, falls vorhanden
        tree = ElementTree.ElementTree(ElementTree.fromstring(response.text))
        root = tree.getroot()

        # PDF-Links extrahieren und herunterladen
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            pdf_link = entry.find("{http://www.w3.org/2005/Atom}link[@title='pdf']")
            if pdf_link is not None:
                pdf_url = pdf_link.attrib['href']
                # Lade die PDF herunter und speichere sie
                pdf_filename = pdf_url.split('/')[-1]  # Name der PDF basierend auf der URL
                pdf_response = await client.get(pdf_url)
                if pdf_response.status_code == 200:
                    with open(pdf_filename, 'wb') as pdf_file:
                        pdf_file.write(pdf_response.content)
                    print(f"PDF gespeichert: {pdf_filename}")
                else:
                    print(f"Fehler beim Herunterladen der PDF: {pdf_url}")

        return {"status": "success", "message": f"XML-Datei und PDFs für {author} erfolgreich gespeichert"}
    else:
        return {"status": "error", "message": "Failed to fetch papers from arXiv"}
