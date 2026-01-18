"""
Module de profiling du code Python.
Utilise cProfile pour analyser les temps d'execution.
"""

import cProfile
import pstats
import io
import sys
import tempfile
import os
from pathlib import Path


def profile_code(code: str, filename: str = "script.py") -> dict:
    """
    Profile le code Python et retourne les statistiques.
    
    Args:
        code: Code Python a profiler
        filename: Nom du fichier pour les traces
        
    Returns:
        Dictionnaire avec les stats de profiling
    """
    # Creer un profiler
    profiler = cProfile.Profile()
    
    # Preparer l'environnement d'execution
    exec_globals = {
        '__name__': '__main__',
        '__file__': filename,
    }
    
    # Capturer stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    
    error = None
    
    try:
        # Compiler le code
        compiled = compile(code, filename, 'exec')
        
        # Profiler l'execution
        profiler.enable()
        exec(compiled, exec_globals)
        profiler.disable()
        
    except Exception as e:
        error = str(e)
    finally:
        # Restaurer stdout/stderr
        stdout_output = sys.stdout.getvalue()
        stderr_output = sys.stderr.getvalue()
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    # Extraire les statistiques
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream)
    stats.sort_stats('cumulative')
    stats.print_stats(50)  # Top 50 fonctions
    
    # Parser les stats
    functions_stats = extract_function_stats(profiler)
    
    # Calculer les totaux
    total_time = sum(f['cumtime'] for f in functions_stats)
    total_calls = sum(f['ncalls'] for f in functions_stats)
    
    return {
        "success": error is None,
        "error": error,
        "stdout": stdout_output[:1000] if stdout_output else None,
        "stderr": stderr_output[:500] if stderr_output else None,
        "total_time": round(total_time, 6),
        "total_calls": total_calls,
        "functions": functions_stats[:30],  # Top 30
        "raw_stats": stats_stream.getvalue()
    }


def extract_function_stats(profiler) -> list:
    """
    Extrait les statistiques par fonction depuis le profiler.
    """
    stats = pstats.Stats(profiler)
    
    functions = []
    
    for key, value in stats.stats.items():
        filename, line, func_name = key
        ncalls, totcalls, tottime, cumtime, callers = value
        
        # Filtrer les fonctions internes Python
        if '<' in filename or 'importlib' in filename:
            continue
        
        # Simplifier le nom du fichier
        if filename:
            filename = Path(filename).name
        
        functions.append({
            "name": func_name,
            "filename": filename,
            "line": line,
            "ncalls": ncalls,
            "totcalls": totcalls,
            "tottime": round(tottime, 6),
            "cumtime": round(cumtime, 6),
            "percall": round(cumtime / ncalls, 6) if ncalls > 0 else 0
        })
    
    # Trier par temps cumulatif
    functions.sort(key=lambda x: x['cumtime'], reverse=True)
    
    return functions


def generate_profile_html(profile_data: dict, filename: str) -> str:
    """
    Genere un rapport HTML du profiling.
    """
    functions = profile_data.get("functions", [])
    total_time = profile_data.get("total_time", 0)
    
    # Generer les barres de temps
    rows_html = ""
    max_time = functions[0]["cumtime"] if functions else 1
    
    for func in functions:
        pct = (func["cumtime"] / total_time * 100) if total_time > 0 else 0
        bar_width = (func["cumtime"] / max_time * 100) if max_time > 0 else 0
        
        color = "#22c55e" if pct < 10 else "#f59e0b" if pct < 30 else "#ef4444"
        
        rows_html += """
        <tr>
            <td><code>""" + func["name"] + """</code></td>
            <td>""" + str(func["ncalls"]) + """</td>
            <td>""" + str(func["tottime"]) + """s</td>
            <td>""" + str(func["cumtime"]) + """s</td>
            <td>
                <div class="bar-container">
                    <div class="bar" style="width:""" + str(bar_width) + """%;background:""" + color + """"></div>
                    <span>""" + str(round(pct, 1)) + """%</span>
                </div>
            </td>
        </tr>
        """
    
    error_html = ""
    if profile_data.get("error"):
        error_html = '<div class="error-box">Erreur: ' + profile_data["error"] + '</div>'
    
    return """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Profiling - """ + filename + """</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            padding: 24px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #7c3aed 0%, #4c1d95 100%);
            color: white;
            padding: 32px;
            border-radius: 12px 12px 0 0;
        }
        .header h1 { font-size: 24px; margin-bottom: 8px; }
        .stats {
            display: flex;
            gap: 24px;
            background: white;
            padding: 24px;
            border-bottom: 1px solid #e2e8f0;
        }
        .stat {
            text-align: center;
        }
        .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #7c3aed;
        }
        .stat-label {
            font-size: 12px;
            color: #64748b;
        }
        .content {
            background: white;
            padding: 24px;
            border-radius: 0 0 12px 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            background: #f8fafc;
            font-size: 12px;
            text-transform: uppercase;
            color: #64748b;
        }
        code {
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
        }
        .bar-container {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .bar {
            height: 20px;
            border-radius: 4px;
            min-width: 4px;
        }
        .bar-container span {
            font-size: 12px;
            color: #64748b;
            min-width: 50px;
        }
        .error-box {
            background: #fef2f2;
            border: 1px solid #ef4444;
            color: #991b1b;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Profiling du Code</h1>
            <p>""" + filename + """</p>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value">""" + str(round(total_time * 1000, 2)) + """ms</div>
                <div class="stat-label">Temps total</div>
            </div>
            <div class="stat">
                <div class="stat-value">""" + str(profile_data.get("total_calls", 0)) + """</div>
                <div class="stat-label">Appels totaux</div>
            </div>
            <div class="stat">
                <div class="stat-value">""" + str(len(functions)) + """</div>
                <div class="stat-label">Fonctions</div>
            </div>
        </div>
        
        <div class="content">
            """ + error_html + """
            <table>
                <thead>
                    <tr>
                        <th>Fonction</th>
                        <th>Appels</th>
                        <th>Temps propre</th>
                        <th>Temps cumule</th>
                        <th>% du total</th>
                    </tr>
                </thead>
                <tbody>""" + rows_html + """</tbody>
            </table>
        </div>
    </div>
</body>
</html>"""


def generate_snakeviz_data(profile_data: dict) -> dict:
    """
    Genere les donnees pour une visualisation style SnakeViz.
    Retourne un format JSON pour le frontend.
    """
    functions = profile_data.get("functions", [])
    total_time = profile_data.get("total_time", 0.001)
    
    # Construire la hierarchie
    nodes = []
    
    for i, func in enumerate(functions[:20]):  # Top 20
        pct = func["cumtime"] / total_time * 100
        
        nodes.append({
            "id": i,
            "name": func["name"],
            "filename": func.get("filename", ""),
            "value": func["cumtime"],
            "calls": func["ncalls"],
            "percent": round(pct, 1),
            "color": get_time_color(pct)
        })
    
    return {
        "total_time": total_time,
        "nodes": nodes
    }


def get_time_color(percent: float) -> str:
    """Retourne une couleur selon le pourcentage de temps."""
    if percent < 5:
        return "#22c55e"  # Vert
    elif percent < 15:
        return "#84cc16"  # Vert clair
    elif percent < 30:
        return "#f59e0b"  # Orange
    elif percent < 50:
        return "#f97316"  # Orange fonce
    else:
        return "#ef4444"  # Rouge