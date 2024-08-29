import wikipediaapi

# https://randomincategory.toolforge.org/?category=Wikipedia%20level-5%20vital%20articles&server=en.wikipedia.org&cmnamespace=&cmtype=&returntype=subject

from dotenv import load_dotenv
import json
import os
import random
import requests
from thefuzz import fuzz

load_dotenv()

def get_random_article() -> wikipediaapi.WikipediaPage:
    """Gets random article from Wikipedia:Vital articles/Level/4"""
    # sublists: list[str] = [
    #     "People",
    #     "History",
    #     "Geography",
    #     "Arts",
    #     "Philosophy and religion",
    #     "Everyday life",
    #     "Society and social sciences",
    #     "Biology and health sciences",
    #     "Physical sciences",
    #     "Technology",
    #     "Mathematics"
    # ]
    # sublists: list[str] = [
    #     "People/Writers and journalists",
    #     "People/Artists, musicians, and composers",
    #     "People/Entertainers, directors, producers, and screenwriters",
    #     "People/Philosophers, historians, and social scientists",
    #     "People/Religious figures",
    #     "People/Politicians and leaders",
    #     "People/Military personnel, revolutionaries, and activists",
    #     "People/Scientists, inventors, and mathematicians",
    #     "People/Sports figures",
    #     "People/Miscellaneous",
    #     "History",
    #     "Geography/Physical",
    #     "Geography/Countries",
    #     "Geography/Cities",
    #     "Arts",
    #     "Philosophy and religion",
    #     "Everyday life",
    #     "Everyday life/Sports, games, and recreation",
    #     "Society and social sciences/Social studies",
    #     "Society and social sciences/Politics and economics",
    #     "Society and social sciences/Culture",
    #     "Biology and health sciences/Biology",
    #     "Biology and health sciences/Animals",
    #     "Biology and health sciences/Plants",
    #     "Biology and health sciences/Health",
    #     "Physical sciences/Basics and measurement",
    #     "Physical sciences/Astronomy",
    #     "Physical sciences/Chemistry",
    #     "Physical sciences/Earth science",
    #     "Physical sciences/Physics",
    #     "Technology",
    #     "Mathematics"
    # ]
    wiki_wiki = wikipediaapi.Wikipedia(os.getenv("USER_AGENT"))
    # random_sublist = random.choice(sublists)
    # print(random_sublist)
    # page = wiki_wiki.page(f"Wikipedia:Vital articles/Level/4/{random_sublist}")
    page = wiki_wiki.page("Wikipedia:Vital articles/Level/3")
    links = []
    for link in page.links.values():
        if link.namespace == wikipediaapi.Namespace.MAIN:
            links.append(link.title)
    return wiki_wiki.page(random.choice(links))

def get_article(title: str) -> wikipediaapi.WikipediaPage:
    wiki_wiki = wikipediaapi.Wikipedia(os.getenv("USER_AGENT"))
    return wiki_wiki.page(title)

def get_categories(page_title: str) -> list[str]:
    response = requests.get(
        f"http://en.wikipedia.org/w/api.php?action=query&titles={page_title}&redirects&prop=categories&format=json&clshow=!hidden",
        headers={"User-Agent": os.getenv("USER_AGENT")}
    )
    data = json.loads(response.text)
    category_titles = []
    try:
        pages = data["query"]["pages"]
        for page in pages.values():
            categories = page.get("categories", [])
            for category in categories:
                print(page_title, category["title"], (closeness := fuzz.partial_ratio(page_title.lower(), category["title"].lower())))
                if closeness < 85:
                    category_titles.append(category["title"][len("Category:"):])
    except KeyError: pass # should probably add some logging here
    finally: return category_titles

def get_thumbnail(page_title: str) -> str | None:
    response = requests.get(
        f"https://en.wikipedia.org/w/api.php?action=query&titles={page_title}&prop=pageimages&format=json&pithumbsize=500",
        headers={"User-Agent": os.getenv("USER_AGENT")}
    )
    data = json.loads(response.text)
    try:
        pages = data["query"]["pages"]
        for page in pages.values():
            if "thumbnail" in page:
                return page["thumbnail"]["source"]
    finally: return None

def get_condensed_summary(page_title: str) -> str:
    wiki_wiki = wikipediaapi.Wikipedia(os.getenv("USER_AGENT"))
    page = wiki_wiki.page(page_title)
    return page.summary.split("\n")[0]

if __name__ == "__main__":
    print(get_condensed_summary(get_random_article().title))