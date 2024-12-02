import os
import json
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("detailed_logs.log", encoding="utf-8")
    ]
)

def explore_section(page, section_name, url):
    """
    Explore une section pour identifier les patterns structurels.
    
    Args:
        page: Instance de la page Playwright.
        section_name: Nom de la section analysée.
        url: URL de la section.
        
    Returns:
        Un dictionnaire contenant les patterns et les liens internes détectés.
    """
    try:
        logging.info(f"Exploration de la section : {section_name} ({url})")
        page.goto(url)
        page.wait_for_load_state("networkidle")

        # Analyse du contenu de la page avec BeautifulSoup
        soup = BeautifulSoup(page.content(), "html.parser")

        # Extraction des liens internes
        links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("/view/") or urljoin(url, href).startswith("https://help.autodesk.com"):
                links.append({
                    "text": link.get_text(strip=True),
                    "url": urljoin(url, href)
                })

        # Analyse des structures HTML
        patterns = {
            "titles": [h.text.strip() for h in soup.find_all(["h1", "h2", "h3"])],
            "classes": list(set(tag.get("class", [])[0] for tag in soup.find_all() if tag.get("class"))),
            "ids": list(set(tag.get("id") for tag in soup.find_all() if tag.get("id"))),
        }

        # Retourner les résultats
        return {
            "section_name": section_name,
            "url": url,
            "links": links,
            "patterns": patterns
        }

    except Exception as e:
        logging.error(f"Erreur lors de l'exploration de la section {section_name} : {e}")
        return {}

def main():
    base_url = "https://help.autodesk.com/view/ACD/2022/ENU/"
    section_name = "Getting Started"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        logging.info(f"Accès à l'URL de base : {base_url}")
        page.goto(base_url)
        page.wait_for_load_state("networkidle")

        # Ouvrir la section "Getting Started"
        section_menu = page.locator(f"[role='treeitem'][data-id='AutoCAD-GettingStarted']")
        if section_menu.count() == 0:
            logging.error(f"Section '{section_name}' introuvable.")
            return

        section_menu.locator("span.expand-collapse[role='button']").click()
        page.wait_for_timeout(1000)

        # Parcourir les sous-sections
        links = section_menu.locator("ul[role='group'] a[href]")
        patterns_list = []
        for i in range(links.count()):
            link = links.nth(i)
            title = link.inner_text().strip()
            href = urljoin(base_url, link.get_attribute("href"))

            # Ignorer la section "AutoCAD Learning Videos"
            if "Learning Videos" in title:
                logging.info(f"Ignorer la sous-section : {title}")
                continue

            # Explorer la sous-section
            logging.info(f"Exploration de la sous-section : {title}")
            patterns = explore_section(page, title.replace("/", "_"), href)
            if patterns:
                patterns_list.append(patterns)

        # Sauvegarde des patterns en JSON
        output_file = "patterns.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(patterns_list, f, indent=4, ensure_ascii=False)
        logging.info(f"Patterns sauvegardés dans {output_file}")

        browser.close()

if __name__ == "__main__":
    main()
