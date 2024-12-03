import os
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import pdfkit

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

def convert_html_to_pdf_with_pdfkit(html_path, pdf_path):
    """Convertit un fichier HTML en PDF avec pdfkit."""
    try:
        options = {
            'enable-local-file-access': None,  # Nécessaire pour accéder aux fichiers locaux
            'page-size': 'A4',
            'encoding': "UTF-8",
            'zoom': '1.25'
        }
        pdfkit.from_file(html_path, pdf_path, options=options)
        logging.info(f"PDF généré : {pdf_path}")
    except Exception as e:
        logging.error(f"Erreur lors de la conversion en PDF avec pdfkit : {e}")

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
        combined_content += f"<h1>Section principale : The Hitchhiker's Guide to AutoCAD</h1>"

        # Extraire le contenu principal de la page principale
        main_content, internal_links = fetch_main_content(page, section_url, base_url)

        # Ajouter le contenu principal
        if main_content:
            combined_content += f"<div>{main_content}</div>"

        # Ajouter le contenu des sous-liens internes
        combined_content += "<h2>Pages liées</h2><ul>"
        for link in internal_links:
            try:
                sub_content, _ = fetch_main_content(page, link["url"], base_url)
                if sub_content:
                    combined_content += f"<li><h3 id='{link['text'].replace(' ', '_')}'>{link['text']}</h3><div>{sub_content}</div></li>"
            except Exception as e:
                logging.error(f"Erreur lors du traitement du sous-lien : {link['url']} -> {e}")
        combined_content += "</ul>"

        # Fermer le HTML
        combined_content += "</body></html>"

        # Sauvegarder le contenu combiné dans un fichier HTML
        html_path = save_combined_html(combined_content, output_dir, "combined_section.html")

        # Convertir le fichier HTML en PDF avec pdfkit
        pdf_path = os.path.join(output_dir, "combined_section.pdf")
        convert_html_to_pdf_with_pdfkit(html_path, pdf_path)

        browser.close()
        logging.info("Traitement terminé.")

if __name__ == "__main__":
    main()
