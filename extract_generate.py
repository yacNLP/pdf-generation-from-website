from playwright.sync_api import sync_playwright
from urllib.parse import urljoin

# Ensemble pour traquer les liens déjà vérifiés
checked_links = set()

def explore_section(section, level=0):
    """Explore une section et ses sous-sections récursivement, et vérifie l'accès aux liens."""
    # Indentation pour représenter les niveaux
    indent = "  " * level

    # Récupérer l'ID de la section
    section_id = section.get_attribute('data-id')

    # Essayer de récupérer le titre via un sélecteur alternatif si nécessaire
    title_element = section.query_selector('a[role="button"]') or section.query_selector('a[href]')
    title = title_element.inner_text().strip() if title_element else "Unknown Title"

    print(f"{indent}Section: {title}, ID: {section_id}")

    # Vérifier s'il y a un bouton pour déplier
    expand_button = section.query_selector('.expand-collapse')
    is_expanded = section.get_attribute('aria-expanded')

    # Déplier la section si nécessaire
    if expand_button and is_expanded == "false":
        expand_button.click()
        page.wait_for_timeout(500)  # Pause pour laisser charger les sous-sections

    # Explorer les sous-sections
    sub_sections = section.query_selector_all('ul.node-tree > .node-tree-item')
    has_sub_sections = len(sub_sections) > 0  # Vérifier si des sous-sections existent
    for sub_section in sub_sections:
        explore_section(sub_section, level + 1)  # Appel récursif pour explorer les sous-sections

    # Vérifier les liens de la section principale uniquement si elle n'a pas de sous-sections
    if not has_sub_sections:
        link_element = section.query_selector('a[href]')
        if link_element:
            link = link_element.get_attribute('href')
            link = urljoin(base_url, link)  # Construire l'URL complète
            if link not in checked_links:  # Vérifier si le lien a déjà été traité
                checked_links.add(link)  # Ajouter à l'ensemble des liens vérifiés
                print(f"{indent}  Checking link: {link}")
                try:
                    # Ouvrir le lien dans un nouvel onglet
                    new_page = browser.new_page()
                    new_page.goto(link, timeout=10000)
                    # Vérifier si le contenu est chargé
                    if new_page.title():  # Vérifie que la page a un titre
                        print(f"{indent}  Link is accessible: {link}")
                    else:
                        print(f"{indent}  Link is NOT accessible: {link}")
                    new_page.close()  # Fermer l'onglet
                except Exception as e:
                    print(f"{indent}  Failed to access link: {link} - Error: {e}")

def explore_sections_with_nested_subsections(url):
    # Liste des IDs des sections principales désirées
    desired_ids = [
        "AutoCAD-GettingStarted",
    ]

    with sync_playwright() as p:
        global browser, page, base_url
        browser = p.chromium.launch(headless=False)  # Mode visible pour debug
        page = browser.new_page()
        base_url = url  # Base URL pour urljoin
        page.goto(url)

        # Attendre que le menu principal soit chargé
        page.wait_for_selector('.node-tree-container')

        # Récupérer uniquement les enfants directs (sections principales)
        sections = page.query_selector_all('.node-tree > .node-tree-item')

        for section in sections:
            section_id = section.get_attribute('data-id')
            if section_id and section_id in desired_ids:  # Filtrer par ID désirés
                explore_section(section)  # Explorer récursivement cette section

        browser.close()

# URL de base
base_url = "https://help.autodesk.com/view/ACD/2022/ENU/"
explore_sections_with_nested_subsections(base_url)
