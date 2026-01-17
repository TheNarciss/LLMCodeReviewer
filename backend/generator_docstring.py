"""
Module de génération automatique de docstrings via LLM.
"""

import re
from llm_service import generate
from utils import read_file, write_file


def clean_llm_output(text: str) -> str:
    """
    Nettoie la sortie brute du LLM pour ne garder que le code Python.
    
    Args:
        text: Sortie brute du LLM
        
    Returns:
        Code Python nettoyé
    """
    # Supprimer les blocs markdown
    text = re.sub(r"^```(?:python)?\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```$", "", text, flags=re.MULTILINE)
    
    # Supprimer les phrases d'introduction
    text = re.sub(r"(?i)^(voici|here is|here's).*?:\n*", "", text)
    text = re.sub(r"(?i)^(le code|the code).*?:\n*", "", text)
    
    # Supprimer les notes finales
    text = re.sub(r"(?i)\n*note\s*:.*$", "", text, flags=re.DOTALL)
    
    return text.strip()


def generate_docstrings(code: str) -> str:
    """
    Génère des docstrings pour le code Python fourni.
    
    Args:
        code: Code source Python
        
    Returns:
        Code avec docstrings ajoutées
    """
    prompt = f"""Ajoute des docstrings Google-style à toutes les fonctions et classes dans ce code Python.

Règles:
- Ne modifie PAS la logique du code
- Ajoute uniquement des docstrings manquantes
- Utilise le format Google-style (Args, Returns, Raises)
- Sois concis et précis
- Retourne UNIQUEMENT le code Python, sans texte avant ou après

Code:
```python
{code}
```"""

    try:
        response = generate(prompt)
        cleaned = clean_llm_output(response)
        
        # Vérification basique que c'est du Python valide
        if cleaned and ("def " in cleaned or "class " in cleaned):
            return cleaned
        return code
        
    except Exception as e:
        print(f"Erreur génération docstrings: {e}")
        return code


def add_docstrings_to_file(input_path: str, output_path: str) -> str:
    """
    Lit un fichier Python, ajoute des docstrings et enregistre le résultat.
    
    Args:
        input_path: Chemin du fichier source
        output_path: Chemin du fichier de sortie
        
    Returns:
        Code avec docstrings
    """
    code = read_file(input_path)
    documented = generate_docstrings(code)
    write_file(output_path, documented)
    return documented
