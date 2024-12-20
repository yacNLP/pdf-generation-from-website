import os
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from weasyprint import HTML

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def save_combined_html(content, output_dir, filename):
    """Sauvegarde le contenu HTML combiné dans un fichier."""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info(f"HTML combiné sauvegardé : {file_path}")
    return file_path

def convert_html_to_pdf_with_weasyprint(html_path, pdf_path):
    """Convertit un fichier HTML en PDF avec WeasyPrint."""
    try:
        HTML(html_path).write_pdf(pdf_path)
        logging.info(f"PDF généré avec WeasyPrint : {pdf_path}")
    except Exception as e:
        logging.error(f"Erreur lors de la conversion en PDF avec WeasyPrint : {e}")

def fetch_main_content(page, url, base_url):
    """Récupère le contenu principal de la page."""
    try:
        logging.info(f"Accès à la page : {url}")
        page.goto(url, timeout=20000)
        page.wait_for_load_state("networkidle")
        soup = BeautifulSoup(page.content(), "html.parser")

        # Extraire le contenu principal
        main_content = soup.select_one("article.wbh-caas-viewer > div.caas > div.caas_body")
        if not main_content:
            logging.warning(f"Contenu principal introuvable pour : {url}")
            return None, []

        # Extraire les liens internes dans le contenu principal
        links = []
        for link in main_content.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(base_url, href)
            if full_url.startswith(base_url):  # Assurer qu'il s'agit d'un lien interne
                links.append({
                    "text": link.get_text(strip=True),
                    "url": full_url
                })
        logging.info(f"Liens internes dans le contenu principal : {len(links)} trouvés.")
        for link in links:
            logging.info(f"- Texte : {link['text']}, URL : {link['url']}")

        return str(main_content), links
    except Exception as e:
        logging.error(f"Erreur lors de l'accès à la page : {url} -> {e}")
        return None, []

def main():
    base_url = "https://help.autodesk.com/view/ACD/2022/ENU/"
    section_url = "https://help.autodesk.com/view/ACD/2022/ENU/?contextId=HITCHHIKERSGUIDETOAUTOCADBASICS"
    output_dir = "outputs/pdf/The Hitchhiker's Guide to AutoCAD"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Initialiser le contenu combiné
        combined_content = "<html><head><title>The Hitchhiker's Guide to AutoCAD</title></head><body>"

        # Liste pour suivre les sections téléchargées
        downloaded_sections = []

        # Extraire le contenu principal de la page principale
        main_content, internal_links = fetch_main_content(page, section_url, base_url)

        # Ajouter le contenu principal
        if main_content:
            soup = BeautifulSoup(main_content, "html.parser")
            main_title = soup.find("h1")
            if main_title and not main_title.get("id"):
                main_title["id"] = "The_Hitchhiker's_Guide_to_AutoCAD"
            combined_content += str(soup)
            downloaded_sections.append(main_title["id"])

        # Ajouter le contenu des sous-liens internes
        for link in internal_links:
            try:
                sub_content, _ = fetch_main_content(page, link["url"], base_url)
                if sub_content:
                    soup = BeautifulSoup(sub_content, "html.parser")
                    sub_title = soup.find("h1")
                    if sub_title and not sub_title.get("id"):
                        sub_title["id"] = link["text"].replace(" ", "_")
                    combined_content += str(soup)
                    downloaded_sections.append(sub_title["id"])
            except Exception as e:
                logging.error(f"Erreur lors du traitement du sous-lien : {link['url']} -> {e}")

        # Mettre à jour les liens internes et externes
        soup = BeautifulSoup(combined_content, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            link_text = link.get_text(strip=True)
            
            if link_text.replace(" ", "_") in downloaded_sections:
                # Convertir en ancre interne
                link["href"] = f"#{link_text.replace(' ', '_')}"
                logging.info(f"Mis à jour comme ancre interne : {link_text} -> #{link_text.replace(' ', '_')}")
            elif href.startswith("?guid="):
                # Convertir les chemins relatifs en URLs absolues
                link["href"] = urljoin(base_url, href)
                logging.info(f"Converti en lien absolu : {link['href']}")
            else:
                logging.info(f"Conservé comme lien externe : {link_text} -> {link['href']}")

        # Sauvegarder le contenu combiné dans un fichier HTML
        html_path = save_combined_html(str(soup), output_dir, "combined_section.html")

        # Convertir le fichier HTML en PDF avec WeasyPrint
        pdf_path = os.path.join(output_dir, "combined_section.pdf")
        convert_html_to_pdf_with_weasyprint(html_path, pdf_path)

        browser.close()
        logging.info("Traitement terminé.")

if __name__ == "__main__":
    main()
