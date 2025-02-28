import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

# Diese Datei sollte in einer anderen Datei integriert werden.
# Sie macht genau, was ihr Name sagt und zusätzlich erstellt und füllt sie das Attribut "profil_url" in der DB bei jedem Autor.
# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

MONGO_URI = os.getenv("MongoDB-uri", "mongodb://localhost:27017/")
DB_NAME = os.getenv("db", "testdb")
AUTHORS_COLLECTION = "authors"

def load_author_image_mapping(authors_file):
    """
    Liest die Authors.json und erstellt ein Mapping:
      { "Autor Name": {"image_URL": <value>, "profile_URL": <value>} }
    aus den Gruppen: "executeive_board", "faculty", 
    "research_group_leaders" und "fellows".
    """
    with open(authors_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    mapping = {}
    groups = ["executeive_board", "faculty", "research_group_leaders", "fellows"]
    for group in groups:
        for entry in data.get(group, []):
            # Jedes Element ist ein Dict mit einem Schlüssel (Autorname)
            for name, details in entry.items():
                image_url = details.get("image_URL", "")
                profile_url = details.get("profile_URL", "")
                mapping[name] = {"image_URL": image_url, "profile_URL": profile_url}
    return mapping

def update_authors_image_path(mapping):
    """
    Überschreibt die Felder "image_path" und "profil_url" in jedem Dokument der Collection "authors"
    mit den Werten, die im Mapping für den entsprechenden Autor (basierend auf "name") gefunden werden.
    Existiert kein Mapping-Eintrag, werden leere Strings gesetzt.
    """
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    authors_col = db[AUTHORS_COLLECTION]

    for author in authors_col.find({}):
        name = author.get("name", "")
        data = mapping.get(name, {})
        new_image_path = data.get("image_URL", "")
        new_profile_url = data.get("profile_URL", "")
        authors_col.update_one(
            {"_id": author["_id"]},
            {"$set": {"image_path": new_image_path, "profil_url": new_profile_url}}
        )
        print(f"Updated '{name}' with image_path: '{new_image_path}' and profil_url: '{new_profile_url}'")
    
    client.close()

def main():
    authors_file = "Authors.json"  # Pfad zur Authors.json-Datei
    mapping = load_author_image_mapping(authors_file)
    update_authors_image_path(mapping)

if __name__ == "__main__":
    main()
