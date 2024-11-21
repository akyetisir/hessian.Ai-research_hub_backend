# Backend

Backend mit FastAPI

Steps für Mac:

Check ob Python installiert
**python3 --version** 

Wenn Python noch nicht installiert dann
**brew install python**

Check ob drauf ist
**python3 --version**

In das Projekt Hauptverzeichnis navigieren
**cd pythonBackend**

Virtuelle umgebung kreiren
**python3 -m venv venv**

Virtuelle Umgebung starten. Erkennt man an (venv) vor der shell
**source venv/bin/activate**

Alle Dependencies ziehen
**pip install -r requirements.txt**

Server starten
**uvicorn pythonBackend.main:app --reload**

Dann mal localhost schauen

Wenn man wieder aus der virtuel enviroment raus will dann

**deactivate**
