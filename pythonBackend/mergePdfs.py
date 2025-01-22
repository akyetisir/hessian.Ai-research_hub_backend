import os
import hashlib
import shutil
import re

def sanitize_filename(title: str, max_length: int = 50) -> str:
    """
    Bereinigt einen Titel für die Verwendung als Dateiname:
    - Alles zu Kleinbuchstaben
    - Ersetzt unerwünschte Zeichen (inkl. ', ", {, }, etc.) durch Unterstriche
    - Kürzt auf die maximal zulässige Länge
    """
    sanitized = title.lower()
    # Ersetze alles außer a-z, 0-9, ., -, _ durch "_"
    sanitized = re.sub(r'[^a-z0-9._-]', '_', sanitized)
    # Mehrere Unterstriche hintereinander zu einem machen
    sanitized = re.sub(r'_+', '_', sanitized)
    # Auf max_length kürzen und ggf. trailing underscores entfernen
    sanitized = sanitized[:max_length].strip('_')
    return sanitized


def generate_unique_filename(folder: str, filename: str, extension: str) -> str:
    """
    Prüft, ob ein Dateiname bereits existiert, und fügt bei Bedarf einen Zähler hinzu.
    """
    base_filename = filename
    counter = 1
    new_path = os.path.join(folder, f"{filename}{extension}")
    while os.path.exists(new_path):
        filename = f"{base_filename}_{counter}"
        counter += 1
        new_path = os.path.join(folder, f"{filename}{extension}")
    return new_path


def merge_pdfs(source_root="pdfs", target_folder="alle_pdfs"):
    """
    Durchsucht rekursiv den Ordner `pdfs/` nach PDF-Dateien, kopiert jede Datei
    in den Ordner `alle_pdfs/`, aber nur, wenn dort noch keine identische PDF existiert.
    (Duplikate werden anhand des MD5-Hashes erkannt.)
    """
    # Zielordner erstellen (falls nicht vorhanden)
    os.makedirs(target_folder, exist_ok=True)

    # Set für bereits bekannte Hashes
    seen_hashes = set()

    # Rekursives Durchlaufen von `pdfs`
    for root, dirs, files in os.walk(source_root):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_path = os.path.join(root, file)

                # MD5-Hash der PDF berechnen
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()
                    md5_hash = hashlib.md5(file_bytes).hexdigest()

                # Prüfen, ob dieser Hash schon bekannt ist
                if md5_hash not in seen_hashes:
                    # Noch nicht vorhanden -> Datei kopieren
                    seen_hashes.add(md5_hash)

                    # Dateiname ohne Extension bereinigen
                    file_stem, _ = os.path.splitext(file)
                    sanitized_stem = sanitize_filename(file_stem)

                    # Eindeutigen Zielpfad ermitteln
                    new_pdf_path = generate_unique_filename(
                        folder=target_folder,
                        filename=sanitized_stem,
                        extension=".pdf"
                    )

                    # Datei kopieren
                    with open(new_pdf_path, "wb") as out_f:
                        out_f.write(file_bytes)

                    print(f"Kopiert: {pdf_path} -> {new_pdf_path}")
                else:
                    print(f"Duplikat gefunden (übersprungen): {pdf_path}")


if __name__ == "__main__":
    merge_pdfs()
