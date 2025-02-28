"""
    Script to scrape all authors from the following site:
    https://hessian.ai/de/ueber-uns/#researchers
 """

#$ python -m pip install beautifulsoup4
import requests 
import re
import json
from bs4 import BeautifulSoup

URL = "https://hessian.ai/de/ueber-uns/#researchers"

def select_list_container(container, selector:str):
    return container.find('h3', string=selector).find_next_sibling("div").find_next_sibling("div")

def select_listitem_container(container, selector:str):
    return container.find('li')

def extract_authors(container):
    authors = container.find_all('a', {'href': re.compile(r"https:\/\/hessian\.ai\/de\/personen\/")})
    author_dict = {}
    auth_data = {}
    for author in authors:
        if author.img != None:
            auth_data["image_URL"] = author.img.get('src')
            auth_data["profile_URL"] = author.get('href')
        else:
            author_dict.update({f"{author.text}": auth_data})
    return author_dict

if __name__ == "__main__":    
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    tags = {"executeive_board": "Vorstand",
            "faculty": "Mitglied",
            "research_group_leaders": "Nachwuchsgruppenleitung",
            "fellows": "Fellows"
            }
    # dont use these tags:
    # "alumni": "Alumni", "managing_office":"Geschäftsstelle"
    
    author_list = {key:[] for key,_ in tags.items()}
    for tag, selector in tags.items():
        groups_container = select_list_container(soup, selector)
        author_groups = []
        for auth_container in groups_container.select("li"):
            author_groups.append(extract_authors(auth_container)) 
        author_list[tag] = author_groups
    
    with open('authors.json', 'w', encoding='utf8') as f:
        json.dump(author_list, f, indent=4, ensure_ascii=False)