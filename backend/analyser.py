"""
Analyseur de code Python avance.
Extrait toutes les metriques professionnelles pour le rapport.
"""

import ast
import subprocess
from pathlib import Path


def analyze_file(filepath: str) -> dict:
    """
    Analyse complete d'un fichier Python.
    Retourne toutes les metriques necessaires pour un rapport professionnel.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        return {"error": str(e), "code": ""}
    
    lines = code.split('\n')
    
    # Metriques de base
    total_lines = len(lines)
    blank_lines = sum(1 for line in lines if not line.strip())
    comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
    code_lines = total_lines - blank_lines - comment_lines
    
    # Analyse AST
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {
            "error": "Erreur de syntaxe: " + str(e),
            "code": code,
            "lines": total_lines,
            "functions": [],
            "classes": [],
            "style_issues": []
        }
    
    # Extraire les informations
    imports = extract_imports(tree)
    classes = extract_classes(tree)
    functions = extract_functions(tree)
    variables = extract_global_variables(tree)
    constants = extract_constants(tree)
    
    # Calculer les metriques
    all_funcs = functions + [m for c in classes for m in c.get("methods", [])]
    total_complexity = sum(f.get("complexity", 1) for f in all_funcs) if all_funcs else 0
    avg_complexity = total_complexity / len(all_funcs) if all_funcs else 0
    max_complexity = max((f.get("complexity", 1) for f in all_funcs), default=0)
    
    # Docstring coverage
    documented_functions = sum(1 for f in functions if f.get("has_docstring"))
    documented_classes = sum(1 for c in classes if c.get("has_docstring"))
    total_documentable = len(functions) + len(classes)
    doc_coverage = (documented_functions + documented_classes) / total_documentable * 100 if total_documentable > 0 else 100
    
    # Problemes de style (flake8)
    style_issues = run_flake8(filepath)
    
    # Graphe de dependances
    dependency_graph = build_dependency_graph(classes, functions, imports)
    
    return {
        "code": code,
        "filepath": filepath,
        "filename": Path(filepath).name,
        
        # Metriques de lignes
        "lines": total_lines,
        "code_lines": code_lines,
        "blank_lines": blank_lines,
        "comment_lines": comment_lines,
        "comment_ratio": round(comment_lines / code_lines * 100, 1) if code_lines > 0 else 0,
        
        # Structure
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "variables": variables,
        "constants": constants,
        
        # Metriques de complexite
        "total_complexity": total_complexity,
        "avg_complexity": round(avg_complexity, 2),
        "max_complexity": max_complexity,
        
        # Documentation
        "doc_coverage": round(doc_coverage, 1),
        "documented_functions": documented_functions,
        "documented_classes": documented_classes,
        
        # Qualite
        "style_issues": style_issues,
        
        # Dependances
        "dependency_graph": dependency_graph
    }


def analyze_code_string(code: str) -> dict:
    """
    Analyse du code depuis une string (pour analyser le code corrige).
    """
    lines = code.split('\n')
    
    total_lines = len(lines)
    blank_lines = sum(1 for line in lines if not line.strip())
    comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
    code_lines = total_lines - blank_lines - comment_lines
    
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {
            "lines": total_lines,
            "code_lines": code_lines,
            "functions": [],
            "classes": [],
            "style_issues": [],
            "avg_complexity": 0,
            "doc_coverage": 0
        }
    
    imports = extract_imports(tree)
    classes = extract_classes(tree)
    functions = extract_functions(tree)
    
    all_funcs = functions + [m for c in classes for m in c.get("methods", [])]
    total_complexity = sum(f.get("complexity", 1) for f in all_funcs) if all_funcs else 0
    avg_complexity = total_complexity / len(all_funcs) if all_funcs else 0
    
    documented_functions = sum(1 for f in functions if f.get("has_docstring"))
    documented_classes = sum(1 for c in classes if c.get("has_docstring"))
    total_documentable = len(functions) + len(classes)
    doc_coverage = (documented_functions + documented_classes) / total_documentable * 100 if total_documentable > 0 else 100
    
    return {
        "lines": total_lines,
        "code_lines": code_lines,
        "blank_lines": blank_lines,
        "comment_lines": comment_lines,
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "avg_complexity": round(avg_complexity, 2),
        "doc_coverage": round(doc_coverage, 1),
        "style_issues": []
    }


def extract_imports(tree):
    """Extrait tous les imports."""
    imports = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "type": "import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append({
                    "type": "from",
                    "module": module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno
                })
    
    return imports


def extract_classes(tree):
    """Extrait les classes avec leurs details."""
    classes = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(ast.unparse(base))
            
            methods = []
            attributes = []
            
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_info = {
                        "name": item.name,
                        "args": [arg.arg for arg in item.args.args if arg.arg != 'self'],
                        "line": item.lineno,
                        "is_private": item.name.startswith('_') and not item.name.startswith('__'),
                        "is_magic": item.name.startswith('__') and item.name.endswith('__'),
                        "has_docstring": ast.get_docstring(item) is not None,
                        "complexity": calculate_complexity(item)
                    }
                    methods.append(method_info)
                
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            attributes.append(target.id)
            
            docstring = ast.get_docstring(node)
            
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, 'end_lineno', node.lineno),
                "bases": bases,
                "methods": methods,
                "method_count": len(methods),
                "attributes": attributes,
                "has_docstring": docstring is not None,
                "docstring": docstring[:200] if docstring else None,
                "is_private": node.name.startswith('_')
            })
    
    return classes


def extract_functions(tree):
    """Extrait les fonctions (hors methodes de classe)."""
    functions = []
    class_methods = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_methods.add((item.lineno, item.name))
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.lineno, node.name) not in class_methods:
                args = []
                for arg in node.args.args:
                    arg_info = {"name": arg.arg}
                    if arg.annotation:
                        arg_info["type"] = ast.unparse(arg.annotation)
                    args.append(arg_info)
                
                return_type = None
                if node.returns:
                    return_type = ast.unparse(node.returns)
                
                docstring = ast.get_docstring(node)
                
                calls = []
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Call):
                        if isinstance(subnode.func, ast.Name):
                            calls.append(subnode.func.id)
                        elif isinstance(subnode.func, ast.Attribute):
                            calls.append(subnode.func.attr)
                
                end_line = getattr(node, 'end_lineno', node.lineno)
                
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": end_line,
                    "args": args,
                    "arg_count": len(args),
                    "return_type": return_type,
                    "has_docstring": docstring is not None,
                    "docstring": docstring[:200] if docstring else None,
                    "complexity": calculate_complexity(node),
                    "calls": list(set(calls)),
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "is_private": node.name.startswith('_'),
                    "lines": end_line - node.lineno + 1
                })
    
    return functions


def extract_global_variables(tree):
    """Extrait les variables globales."""
    variables = []
    
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    value_type = type(node.value).__name__
                    if isinstance(node.value, ast.Constant):
                        value_type = type(node.value.value).__name__
                    
                    variables.append({
                        "name": target.id,
                        "line": node.lineno,
                        "type": value_type,
                        "is_constant": target.id.isupper()
                    })
        elif isinstance(node, ast.AnnAssign) and node.target:
            if isinstance(node.target, ast.Name):
                variables.append({
                    "name": node.target.id,
                    "line": node.lineno,
                    "type": ast.unparse(node.annotation) if node.annotation else "Unknown",
                    "is_constant": node.target.id.isupper()
                })
    
    return variables


def extract_constants(tree):
    """Extrait les constantes (UPPER_CASE)."""
    constants = []
    
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    value_repr = ""
                    if isinstance(node.value, ast.Constant):
                        value_repr = repr(node.value.value)[:50]
                    
                    constants.append({
                        "name": target.id,
                        "line": node.lineno,
                        "value": value_repr
                    })
    
    return constants


def calculate_complexity(node):
    """Calcule la complexite cyclomatique."""
    complexity = 1
    
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        elif isinstance(child, ast.Assert):
            complexity += 1
        elif isinstance(child, (ast.With, ast.AsyncWith)):
            complexity += 1
    
    return complexity


def run_flake8(filepath: str) -> list:
    """Execute flake8 et retourne les problemes."""
    try:
        result = subprocess.run(
            ['flake8', '--max-line-length=120', filepath],
            capture_output=True,
            text=True,
            timeout=30
        )
        issues = []
        for line in result.stdout.strip().split('\n'):
            if line:
                issues.append(line)
        return issues
    except Exception:
        return []


def build_dependency_graph(classes, functions, imports):
    """Construit un graphe de dependances."""
    graph = {
        "nodes": [],
        "edges": []
    }
    
    # Noeuds pour les imports externes
    external_modules = set()
    for imp in imports:
        module = imp.get("module", "").split('.')[0]
        if module:
            external_modules.add(module)
    
    for module in external_modules:
        graph["nodes"].append({
            "id": "import_" + module,
            "label": module,
            "type": "import"
        })
    
    # Noeuds pour les classes
    for cls in classes:
        graph["nodes"].append({
            "id": "class_" + cls["name"],
            "label": cls["name"],
            "type": "class",
            "methods": cls.get("method_count", 0)
        })
        
        for base in cls.get("bases", []):
            graph["edges"].append({
                "from": "class_" + cls["name"],
                "to": "class_" + base,
                "type": "inherits"
            })
    
    # Noeuds pour les fonctions
    for func in functions:
        graph["nodes"].append({
            "id": "func_" + func["name"],
            "label": func["name"],
            "type": "function",
            "complexity": func.get("complexity", 1)
        })
        
        for call in func.get("calls", []):
            graph["edges"].append({
                "from": "func_" + func["name"],
                "to": "func_" + call,
                "type": "calls"
            })
    
    return graph


def calculate_quality_score(analysis: dict) -> int:
    """Calcule un score de qualite (0-100)."""
    if "error" in analysis and analysis.get("functions") is None:
        return 0
    
    score = 100
    
    # Penalite pour les problemes de style (-2 par probleme, max -30)
    style_penalty = min(30, len(analysis.get("style_issues", [])) * 2)
    score -= style_penalty
    
    # Penalite pour la complexite moyenne
    avg_complexity = analysis.get("avg_complexity", 0)
    if avg_complexity > 10:
        score -= min(20, int((avg_complexity - 10) * 2))
    elif avg_complexity > 5:
        score -= min(10, int(avg_complexity - 5))
    
    # Bonus/Penalite pour la documentation
    doc_coverage = analysis.get("doc_coverage", 0)
    if doc_coverage >= 80:
        score += 5
    elif doc_coverage < 30:
        score -= 10
    
    # Penalite pour manque de commentaires
    comment_ratio = analysis.get("comment_ratio", 0)
    if comment_ratio < 5:
        score -= 5
    
    return max(0, min(100, score))


def calculate_quality_score_from_code(code: str) -> int:
    """Calcule le score de qualite depuis une string de code."""
    analysis = analyze_code_string(code)
    return calculate_quality_score(analysis)
