import ast
import logging
from llm_service import generate

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_file_content(file_path: str) -> bool:
    """
    Nettoie le fichier avant traitement :
    1. Supprime TOUTES les docstrings existantes (Module, Classe, Fonction).
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
        
        # On parcourt tout, y compris le module (racine)
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

        # Tri inversé pour suppression sans décalage
        docstrings_to_remove.sort(key=lambda x: x.lineno, reverse=True)
        
        for doc_node in docstrings_to_remove:
            start = doc_node.lineno - 1
            end = getattr(doc_node, 'end_lineno', start + 1)
            del source_lines[start:end]
            # print(f"   🗑️  Docstring supprimée (Lignes {start+1}-{end})")

        # --- ÉTAPE 2 : Suppression des commentaires purs ---
        cleaned_lines = []
        for line in source_lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            cleaned_lines.append(line)
        
        source_lines = cleaned_lines

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(source_lines)
            
        return True

    except Exception as e:
        print(f"❌ Erreur lors du nettoyage : {e}")
        return False

def generate_single_docstring(source_code: str, context_type: str = "function") -> str:
    """
    Génère une docstring adaptée au contexte (Module, Classe ou Fonction).
    """
    if context_type == "module":
        prompt = f"""Génère une docstring de MODULE Python (tout en haut du fichier).
Décris globalement ce que fait ce fichier.
Règles :
1. Retourne UNIQUEMENT la docstring (entre triple guillemets).
2. Sois concis et professionnel (Google Style).

Code du fichier :
{source_code[:2000]}... (tronqué)
"""
    else:
        prompt = f"""Génère une docstring Python (Google Style) pour cette {context_type}.
Règles :
1. Retourne UNIQUEMENT la docstring (entre triple guillemets).
2. Sois concis (Args, Returns si applicable).

Code :
{source_code}
"""

    try:
        response = generate(prompt)
        if not response: return ""

        cleaned = response.strip()
        if "```" in cleaned:
            cleaned = cleaned.replace("```python", "").replace("```", "")
        
        cleaned = cleaned.strip()
        if not (cleaned.startswith('"""') or cleaned.startswith("'''")):
            cleaned = f'"""\n{cleaned}\n"""'
            
        return cleaned
    except Exception as e:
        print(f"❌ Erreur LLM : {e}")
        return ""

def add_docstrings_smartly(file_path: str) -> bool:
    """
    Pipeline complet : Nettoyage -> AST -> Génération -> Injection.
    """
    
    # 1. Nettoyage
    if not clean_file_content(file_path):
        print("⚠️ Le nettoyage a échoué.")
    
    print(f"🚀 Génération des docstrings pour : {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_lines = f.readlines()
        
        file_content = "".join(source_lines)
        tree = ast.parse(file_content)
        
        nodes_to_document = []
        
        # 2. On repère Fonctions et Classes
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                nodes_to_document.append(node)

        # Tri inversé (pour insérer du bas vers le haut)
        nodes_to_document.sort(key=lambda x: x.lineno, reverse=True)
        
        changes_made = False

        # 3. Traitement des Fonctions et Classes
        for node in nodes_to_document:
            is_class = isinstance(node, ast.ClassDef)
            type_str = "classe" if is_class else "fonction"
            print(f"   🤖 Génération ({type_str}) : '{node.name}'...")
            
            # Extraction du code
            if hasattr(node, 'end_lineno') and node.end_lineno:
                func_lines = source_lines[node.lineno-1 : node.end_lineno]
            else:
                func_lines = source_lines[node.lineno-1 : node.lineno+15]

            func_source = "".join(func_lines)
            docstring = generate_single_docstring(func_source, context_type=type_str)
            
            if docstring:
                # Indentation
                def_line = source_lines[node.lineno - 1]
                indent_str = def_line[:len(def_line) - len(def_line.lstrip())]
                doc_indent = indent_str + "    "
                
                formatted_lines = [f"{doc_indent}{line}\n" for line in docstring.split('\n')]
                
                # Insertion après la définition
                insert_pos = node.body[0].lineno - 1
                for line in reversed(formatted_lines):
                    source_lines.insert(insert_pos, line)
                changes_made = True

        # 4. Traitement du MODULE (Tout en haut)
        print(f"   🤖 Génération (Module) : Entête du fichier...")
        # On envoie un aperçu du fichier au LLM (les 100 premières lignes suffisent souvent)
        module_preview = "".join(source_lines[:100])
        module_doc = generate_single_docstring(module_preview, context_type="module")
        
        if module_doc:
            formatted_lines = [f"{line}\n" for line in module_doc.split('\n')]
            # Insertion tout en haut (ligne 0)
            for line in reversed(formatted_lines):
                source_lines.insert(0, line)
            changes_made = True

        if changes_made:
            print("💾 Sauvegarde...")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(source_lines)
            return True
        
        return True

    except Exception as e:
        print(f"❌ Erreur critique : {e}")
        return False