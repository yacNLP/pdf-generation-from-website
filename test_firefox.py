import os
import json
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from weasyprint import HTML
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

def save_file_from_url(url, output_dir):
    """Télécharge un fichier à partir d'une URL."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        local_filename = os.path.join(output_dir, os.path.basename(url.split('?')[0]))
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Fichier téléchargé : {local_filename}")
        return local_filename
    except Exception as e:
        logging.error(f"Erreur lors du téléchargement de {url} : {e}")
        return None

def clean_html(html_content, base_url):
    """Nettoie le contenu HTML et convertit les URI relatifs en absolus."""
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup.find_all(["img", "link", "script"]):
        attr = "src" if tag.name in ["img", "script"] else "href"
        if tag.has_attr(attr):
            tag[attr] = urljoin(base_url, tag[attr])

    # Supprimer les balises inutiles
    for tag in soup.find_all(lambda t: t.name in ["style", "script"] or t.has_attr("hidden")):
        tag.decompose()

    return str(soup)

def extract_page_data(page, section_name, link_title, url):
    """Extrait les données d'une page et gère les fichiers associés."""
    try:
        logging.info(f"Chargement de la page : {link_title} ({url})")
        page.goto(url)
        page.wait_for_load_state("networkidle")

        # Analyse de la page
        soup = BeautifulSoup(page.content(), "html.parser")
        output_dir = f"outputs/{section_name}"
        os.makedirs(output_dir, exist_ok=True)

        # Titre principal
        title = soup.select_one(".head-text h1[itemprop='headline']")
        title_text = title.text.strip() if title else "Titre introuvable"
        logging.debug(f"Titre extrait : {title_text}")

        # Contenu principal
        article_body = soup.select_one(".body.conbody")
        content_text = article_body.get_text(separator="\n", strip=True) if article_body else "Contenu introuvable"

        # Nettoyage du HTML
        cleaned_html = clean_html(page.content(), url)

        # Sauvegarde du HTML nettoyé
        html_file = os.path.join(output_dir, f"{link_title}.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(cleaned_html)
        logging.info(f"HTML sauvegardé : {html_file}")

        # Génération du PDF
        pdf_file = os.path.join(output_dir, f"{link_title}.pdf")
        html = HTML(string=cleaned_html)
        html.write_pdf(pdf_file)
        logging.info(f"PDF généré avec succès : {pdf_file}")

    except Exception as e:
        logging.error(f"Erreur lors du traitement de la page {link_title} : {e}")

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
        for i in range(links.count()):
            link = links.nth(i)
            title = link.inner_text().strip()
            href = urljoin(base_url, link.get_attribute("href"))

            # Ignorer la section "AutoCAD Learning Videos"
            if "Learning Videos" in title:
                logging.info(f"Ignorer la sous-section : {title}")
                continue

            logging.info(f"Traitement de la sous-section : {title}")
            extract_page_data(page, section_name, title.replace("/", "_"), href)

        browser.close()

if __name__ == "__main__":
    main()
