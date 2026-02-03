"""
Module de profiling AVANCÉ (CPU + RAM).
Utilise cProfile pour le temps et tracemalloc pour la mémoire.
Gère les contextes d'exécution et les chemins d'import.
"""

import cProfile
import pstats
import io
import sys
import os
import tracemalloc
import traceback
from pathlib import Path
from contextlib import contextmanager

# --- CONTEXT MANAGERS POUR ISOLATION ---

@contextmanager
def capture_output():
    """Capture stdout et stderr pour ne pas polluer la console du serveur."""
    new_out, new_err = io.StringIO(), io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

@contextmanager
def add_to_path(path):
    """Ajoute le dossier du script au sys.path pour que les imports locaux marchent."""
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
        yield
        if path_str in sys.path:
            sys.path.remove(path_str)
    else:
        yield

# --- FONCTION PRINCIPALE ---

def profile_code(code: str, filename: str = "script.py") -> dict:
    """
    Exécute le code avec monitoring complet (CPU & RAM).
    
    Args:
        code: Le code source Python sous forme de string.
        filename: Le chemin fictif ou réel du fichier.
        
    Returns:
        Un dictionnaire complet avec temps, mémoire, logs et erreurs.
    """
    file_path = Path(filename).resolve()
    directory = file_path.parent
    
    # 1. Préparation de l'environnement sandbox
    exec_globals = {
        '__name__': '__main__',
        '__file__': str(file_path),
        '__builtins__': __builtins__,
    }
    
    # Objets de résultats
    profiler = cProfile.Profile()
    tracemalloc.start() # Démarrage du monitoring RAM
    
    stdout_val = ""
    stderr_val = ""
    error = None
    memory_peak = 0
    
    try:
        # Compilation préalable (pour attraper les SyntaxError avant d'exécuter)
        compiled_code = compile(code, str(file_path), 'exec')
        
        # 2. Exécution isolée
        with capture_output() as (out, err), add_to_path(directory):
            try:
                profiler.enable()
                exec(compiled_code, exec_globals)
                profiler.disable()
            except SystemExit:
                # Le script a fini normalement via sys.exit()
                profiler.disable()
            except Exception:
                # Le script a planté
                profiler.disable()
                traceback.print_exc()
        
        # 3. Récupération des données
        stdout_val = out.getvalue()
        stderr_val = err.getvalue()
        
        # Récupération du pic de mémoire (en octets)
        _, peak = tracemalloc.get_traced_memory()
        memory_peak = peak / 1024 / 1024 # Conversion en Mo
        
    except Exception as e:
        # Erreur grave (ex: SyntaxError lors du compile)
        return {
            "success": False,
            "error": str(e),
            "stdout": "",
            "stderr": str(e),
            "total_time": 0,
            "memory_peak_mb": 0,
            "functions": []
        }
    finally:
        tracemalloc.stop()

    # 4. Analyse des statistiques CPU
    stats = pstats.Stats(profiler)
    # Important : on doit parser les stats pour avoir les relations parent/enfant
    functions_stats = extract_advanced_stats(stats, filename)
    
    # Calcul du temps total (uniquement le code utilisateur pour être pertinent)
    total_time = sum(f['cumtime'] for f in functions_stats if f['is_user_code'])
    if total_time == 0: total_time = stats.total_tt  # Fallback
    
    return {
        "success": True,
        "error": None,
        "stdout": stdout_val[:5000], # On garde les 5000 premiers caractères
        "stderr": stderr_val[:2000],
        "total_time": round(total_time, 4),
        "memory_peak_mb": round(memory_peak, 4),
        "total_calls": stats.total_calls,
        "functions": functions_stats[:60] # Top 60 fonctions les plus gourmandes
    }

def extract_advanced_stats(stats, main_filename: str) -> list:
    """
    Transforme les stats brutes en une liste structurée avec détection
    du code utilisateur vs librairies et relations d'appels.
    """
    functions = []
    main_name = Path(main_filename).name
    
    # stats.stats est un dictionnaire : 
    # {(filename, line, name): (ncalls, totcalls, tottime, cumtime, callers)}
    
    for key, value in stats.stats.items():
        filename, line, func_name = key
        ncalls, totcalls, tottime, cumtime, callers = value
        
        short_filename = Path(filename).name
        
        # --- FILTRAGE INTELLIGENT ---
        # On essaie de déterminer si c'est "ton code" ou "python/lib"
        is_user_code = False
        
        # Si c'est le fichier qu'on analyse
        if filename == str(main_filename) or short_filename == main_name:
            is_user_code = True
        # Si ce n'est pas dans les dossiers systèmes classiques
        elif "site-packages" not in filename and "lib/python" not in filename and not filename.startswith("<"):
            is_user_code = True
            
        # On cache les fonctions internes très bruyantes sauf si c'est du code utilisateur
        if not is_user_code:
            if func_name in ('<module>', '<listcomp>', '<genexpr>'):
                continue
            if short_filename.startswith('<') or short_filename == '~':
                continue

        # --- RECUPERATION DES ENFANTS (Qui cette fonction appelle-t-elle ?) ---
        # Note: pstats stocke les 'callers' (parents), mais c'est dur à inverser ici efficacement.
        # Pour un rapport simple, on garde les stats brutes.
        
        functions.append({
            "name": func_name,
            "filename": short_filename,
            "line": line,
            "ncalls": ncalls,
            "tottime": round(tottime, 5), # Temps passé EXCLUSIVEMENT dans la fonction
            "cumtime": round(cumtime, 5), # Temps passé dans la fonction ET ses sous-fonctions
            "percall": round(cumtime/ncalls, 5) if ncalls > 0 else 0,
            "is_user_code": is_user_code
        })
    
    # Tri intelligent :
    # 1. D'abord le code utilisateur
    # 2. Ensuite les fonctions les plus lentes (cumtime)
    functions.sort(key=lambda x: (not x['is_user_code'], x['cumtime']), reverse=True)
    
    return functions