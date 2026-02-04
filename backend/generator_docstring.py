"""
Générateur de docstrings intelligent (AST).
Force le format Google Style (Description, Args, Returns, Raises) et assure la fermeture des quotes.
"""

import ast
import re
import logging
from llm_service import generate

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_file_content(file_path: str) -> bool:
    """
    Nettoie le fichier avant traitement :
    1. Supprime les docstrings existantes (via AST).
    2. Supprime les lignes de commentaires purs (via Regex).
    """
    print(f"🧹 Nettoyage préliminaire de : {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_lines = f.readlines()
        
        file_content = "".join(source_lines)
        
        try:
            tree = ast.parse(file_content)
        except SyntaxError:
            print("❌ Impossible de parser le fichier pour le nettoyage (SyntaxError).")
            return False

        # --- ÉTAPE 1 : Suppression des Docstrings ---
        docstrings_to_remove = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                # Vérifie si le premier nœud du corps est une expression (string) = docstring
                if (node.body and isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, (ast.Str, ast.Constant))):
                    
                    doc_node = node.body[0]
                    # Vérification pour Python 3.8+ (ast.Constant) et antérieurs (ast.Str)
                    if isinstance(doc_node.value, ast.Constant) and isinstance(doc_node.value.value, str):
                        docstrings_to_remove.append(doc_node)
                    elif isinstance(doc_node.value, ast.Str):
                        docstrings_to_remove.append(doc_node)

        # On trie du bas vers le haut pour ne pas décaler les lignes lors de la suppression
        docstrings_to_remove.sort(key=lambda x: x.lineno, reverse=True)
        
        for doc_node in docstrings_to_remove:
            start = doc_node.lineno - 1
            # end_lineno existe depuis Python 3.8
            end = getattr(doc_node, 'end_lineno', start + 1)
            
            # On supprime les lignes concernées
            del source_lines[start:end]

        # --- ÉTAPE 2 : Suppression des commentaires purs (# ...) ---
        cleaned_lines = []
        for line in source_lines:
            stripped = line.strip()
            # Si la ligne commence par # (ignorer l'indentation), on la saute
            if stripped.startswith("#"):
                continue
            cleaned_lines.append(line)
        
        source_lines = cleaned_lines

        # Sauvegarde du fichier propre
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(source_lines)
            
        return True

    except Exception as e:
        print(f"❌ Erreur lors du nettoyage : {e}")
        return False

def generate_single_docstring(source_code: str) -> str:
    """Demande au LLM de générer une docstring structurée."""
    
    prompt = f"""Tu es un expert en documentation Python (PEP8).
Génère une docstring au format PEP8 pour le code ci-dessous.

Structure OBLIGATOIRE :
1. Description : Une phrase concise expliquant à quoi sert la fonction/classe.
2. Args : (Si applicable) Liste des arguments avec leur type et description.
3. Returns : (Si applicable) Type et description de ce qui est retourné.
4. Raises : (Si applicable) Liste des erreurs explicites levées.

Exemple de format attendu :

Desc : Calcule la racine carrée d'un nombre.

Args:
    x (float): Le nombre positif.

Returns:
    float: La racine carrée.

Raises:
    ValueError: Si x est négatif.

Règles strictes :
- Retourne UNIQUEMENT la docstring.
- Pas de texte avant ou après (pas de "Voici la docstring").
- Ne pas inventer d'arguments qui n'existent pas.

Code à documenter :
{source_code}
"""
    try:
        response = generate(prompt)
        if not response: return ""

        cleaned = response.strip()
        
        # Nettoyage des balises markdown si le LLM en met (ex: ```python ... ```)
        if "```" in cleaned:
            cleaned = cleaned.replace("```python", "").replace("```", "")
        
        cleaned = cleaned.strip()
        
        # --- SECURITÉ CRITIQUE : AJOUT DES QUOTES ---
        # Si le LLM a oublié les triple quotes, on les ajoute artificiellement ici
        if not (cleaned.startswith('"""') or cleaned.startswith("'''")):
            # On s'assure qu'on n'ajoute pas des quotes s'il y en a déjà une partie
            cleaned = cleaned.strip('"').strip("'")
            cleaned = f'"""\n{cleaned}\n"""'
            
        return cleaned
    except Exception as e:
        print(f"❌ Erreur LLM : {e}")
        return ""

def add_docstrings_smartly(file_path: str) -> bool:
    """
    1. Nettoie le fichier (supprime vieux docs & commentaires).
    2. Injecte les nouvelles docstrings via AST.
    """
    
    # 1. D'abord, on fait le ménage !
    if not clean_file_content(file_path):
        print("⚠️ Le nettoyage a échoué, on continue sur le fichier tel quel.")
    
    print(f"🚀 Démarrage de la génération pour : {file_path}")
    
    try:
        # Re-lecture du fichier nettoyé
        with open(file_path, 'r', encoding='utf-8') as f:
            source_lines = f.readlines()
        
        file_content = "".join(source_lines)
        tree = ast.parse(file_content)
        
        nodes_to_document = []
        
        # On prend TOUTES les fonctions et classes
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                nodes_to_document.append(node)

        # Tri inversé (bas vers haut) pour ne pas casser les index de ligne lors de l'insertion
        nodes_to_document.sort(key=lambda x: x.lineno, reverse=True)
        
        print(f"📝 {len(nodes_to_document)} éléments à documenter.")
        changes_made = False

        for node in nodes_to_document:
            print(f"   🤖 Génération pour '{node.name}'...")
            
            # Extraction du code de l'élément pour le contexte du LLM
            if hasattr(node, 'end_lineno') and node.end_lineno:
                func_lines = source_lines[node.lineno-1 : node.end_lineno]
            else:
                func_lines = source_lines[node.lineno-1 : node.lineno+10]

            func_source = "".join(func_lines)
            docstring = generate_single_docstring(func_source)
            
            if docstring:
                # Calcul de l'indentation correcte (alignement sur le 'def' ou 'class')
                def_line = source_lines[node.lineno - 1]
                indent_str = def_line[:len(def_line) - len(def_line.lstrip())]
                doc_indent = indent_str + "    "
                
                # Formatage de chaque ligne de la docstring avec l'indentation
                formatted_lines = [f" # {doc_indent}{line}\n" for line in docstring.split('\n')]
                
                # Insertion après la ligne de définition
                # node.body[0].lineno est la première ligne du corps de la fonction
                # On insère juste avant le corps
                insert_pos = node.body[0].lineno - 1
                
                for line in reversed(formatted_lines):
                    source_lines.insert(insert_pos, line)
                
                changes_made = True
            else:
                print(f"      ⚠️ Pas de réponse LLM pour '{node.name}'")

        if changes_made:
            print("💾 Sauvegarde finale...")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(source_lines)
            return True
        
        return True

    except Exception as e:
        print(f"❌ Erreur critique : {e}")
        return False