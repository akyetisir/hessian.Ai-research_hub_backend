from fastapi import FastAPI
import httpx
from xml.etree import ElementTree
import os

app = FastAPI()

@app.get("/papers/")
async def get_papers(author: str, max_results: int = 15):
    # URL für die arXiv-API
    url = f'http://export.arxiv.org/api/query?search_query=all:{author}&start=0&max_results={max_results}'
    
    # HTTP-Anfrage mit httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    # Überprüfe den Statuscode der Antwort
    if response.status_code == 200:

        xml_folder = "xmls"
        if not os.path.exists(xml_folder):  # Ordner erstellen, wenn er nicht existiert
            os.mkdir(xml_folder)

        # Antwort erfolgreich, speichere die XML-Datei
        xml_filename = f"{xml_folder}/papers_{author}.xml"
        with open(xml_filename, "w", encoding="utf-8") as file:
            file.write(response.text)
        print(f"XML-Datei erfolgreich gespeichert: {xml_filename}")

        tree = ElementTree.ElementTree(ElementTree.fromstring(response.text))
        root = tree.getroot()

        downloaded_pdfs = []
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
        pdfErhalten = "nein"
        anfrageGeschickt = "nein"
        errorM = "kein error"

        for entry in root.findall('atom:entry', namespaces):
            pdf_link = entry.find("atom:link[@title='pdf']", namespaces)

            if pdf_link is not None:
                pdf_url = pdf_link.attrib['href']
                downloaded_pdfs.append(pdf_url)
                
                try:
                    # Sende eine GET-Anfrage, um die PDF-Datei herunterzuladen
                    async with httpx.AsyncClient() as pdf_client:
                        pdf_response = await pdf_client.get(pdf_url)

                    anfrageGeschickt = "jaa"
                    if pdf_response.status_code == 200:
                        pdfErhalten = "ja"
                    # Extrahiere den Titel oder eine eindeutige ID aus dem XML (z.B. den Titel des Artikels)
                        title = entry.find('atom:title', namespaces).text
                    # Verwende den Titel als Dateinamen (ersetze ungültige Zeichen)
                        pdf_filename = f"pdfs/{title[:50].replace('/', '_').replace(' ', '_')}.pdf"
                    # speichern der PDF
                        with open(pdf_filename, "wb") as pdf_file:
                            pdf_file.write(pdf_response.content)
                        print(f"PDF erfolgreich gespeichert: {pdf_filename}")

                except httpx.HTTPStatusError as e:
                     errorM = f"Fehler beim Herunterladen der PDF ({pdf_url}): {e}"
                except Exception as e:
                    errorM = f"Unbekannter Fehler beim Herunterladen der PDF ({pdf_url}): {e}"

        
        return {"status": "success", "message": f"XML-Datei für {author} erfolgreich gespeichert","PDF": f"PDF-URL {downloaded_pdfs}", "PDF erhalten?": pdfErhalten, "Anfrage geschickt?": anfrageGeschickt, "Fehler bei try?": errorM}
    

    
    else:
        # Gebe detaillierte Fehlermeldung aus
        print(f"Fehler: Status Code: {response.status_code}")
        print(f"Antwort Text: {response.text}")
        return {"status": "error", "message": f"Fehler {response.status_code}: {response.text}"}
