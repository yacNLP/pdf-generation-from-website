from playwright.sync_api import sync_playwright

def explore_section(section, level=0):
    """Explore une section et ses sous-sections récursivement."""
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
    for sub_section in sub_sections:
        explore_section(sub_section, level + 1)  # Appel récursif pour explorer les sous-sections

def explore_sections_with_nested_subsections(url):
    # Liste des IDs des sections principales désirées
    desired_ids = [
        "AutoCAD-GettingStarted",
        # "AutoCAD-Core",
        # "AutoCAD-Platform",
        # "AutoCAD-Subscription",
        # "AutoCAD-Customization",
        # "AutoCAD-AutoLISP",
        # "AutoCAD-AutoLISP-Reference",
        # "Installation-AutoCAD_id",
        # "Autodesk-Installation-Admin-ODIS",
        # "AutoCAD-ReleaseNotes_id"
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Mode visible pour debug
        global page  # Rendre la page accessible à la fonction récursive
        page = browser.new_page()
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
