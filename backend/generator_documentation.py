try:
    from llm_service import generate
except ImportError:
    from backend.llm_service import generate

def generate_markdown_doc(code: str, filename: str) -> str:
    prompt = f"""
    Agis comme un rédacteur technique. Analyse le code suivant ({filename}).
    Rédige une documentation technique complète au format Markdown.
    
    Le fichier de sortie doit contenir :
    # Documentation : {filename}
    ## Résumé
    ## Classes et Fonctions (entrées/sorties)
    ## Guide d'utilisation rapide

    Code source :
    ```python
    {code}
    ```
    """
    try:
        return generate(prompt)
    except Exception as e:
        return f"Erreur lors de la génération de la doc : {e}"