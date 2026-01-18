"""
Module de generation de graphes de dependances interactifs.
Genere des graphes SVG/HTML cliquables avec D3.js.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set


def analyze_project_dependencies(directory: str) -> dict:
    """
    Analyse les dependances entre tous les fichiers Python d'un projet.
    """
    python_files = list(Path(directory).rglob("*.py"))
    
    # Map des modules
    modules = {}
    for filepath in python_files:
        rel_path = filepath.relative_to(directory)
        module_name = str(rel_path).replace("/", ".").replace("\\", ".").replace(".py", "")
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]
        modules[module_name] = str(filepath)
    
    # Analyser chaque fichier
    nodes = []
    edges = []
    
    for module_name, filepath in modules.items():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
            
            tree = ast.parse(code)
            
            # Info du module
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Verifier si c'est une fonction de module (pas une methode)
                    functions.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            nodes.append({
                "id": module_name,
                "label": Path(filepath).stem,
                "filepath": filepath,
                "type": "module",
                "classes": classes,
                "functions": functions[:10],  # Limiter
                "imports": imports,
                "lines": len(code.splitlines())
            })
            
            # Creer les liens
            for imp in imports:
                # Chercher si c'est un module local
                if imp in modules or imp.split('.')[0] in modules:
                    edges.append({
                        "source": module_name,
                        "target": imp.split('.')[0] if '.' in imp else imp,
                        "type": "imports"
                    })
        
        except Exception as e:
            print(f"Erreur analyse {filepath}: {e}")
    
    return {
        "nodes": nodes,
        "edges": edges,
        "module_count": len(nodes)
    }


def analyze_file_dependencies(filepath: str) -> dict:
    """
    Analyse les dependances internes d'un fichier Python.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
    except:
        return {"nodes": [], "edges": [], "error": "Impossible de lire le fichier"}
    
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"nodes": [], "edges": [], "error": str(e)}
    
    nodes = []
    edges = []
    
    # --- CORRECTION MAJEURE ICI : Extraction précise des noms importés ---
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Si "import os as o", on garde "o", sinon "os"
                name = alias.asname if alias.asname else alias.name.split('.')[0]
                imports.add(name)
        elif isinstance(node, ast.ImportFrom):
            # Pour "from utils import read_file", on garde "read_file"
            # C'est ce qui permet de faire le lien avec l'appel dans le code
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imports.add(name)
    
    # Création des noeuds d'import
    for imp in imports:
        nodes.append({
            "id": f"import_{imp}",
            "label": imp,
            "type": "import",
            "group": "imports"
        })
    
    # Extraire les classes
    class_names = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_names.add(node.name)
            
            methods = []
            attributes = []
            
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        "name": item.name,
                        "line": item.lineno
                    })
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            attributes.append(target.id)
            
            nodes.append({
                "id": f"class_{node.name}",
                "label": node.name,
                "type": "class",
                "group": "classes",
                "line": node.lineno,
                "methods": methods,
                "attributes": attributes,
                "children": [{"id": f"method_{node.name}_{m['name']}", "label": m["name"], "type": "method"} for m in methods]
            })
            
            for base in node.bases:
                if isinstance(base, ast.Name):
                    edges.append({
                        "source": f"class_{node.name}",
                        "target": f"class_{base.id}",
                        "type": "inherits",
                        "label": "extends"
                    })
    
    # Extraire les fonctions
    function_calls = {}  # fonction -> liste des fonctions appelees
    
    for node in tree.body:
        # Support des fonctions async (FastAPI)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            calls = set()
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call):
                    if isinstance(subnode.func, ast.Name):
                        calls.add(subnode.func.id)
                    elif isinstance(subnode.func, ast.Attribute):
                        calls.add(subnode.func.attr)
            
            function_calls[node.name] = calls
            
            nodes.append({
                "id": f"func_{node.name}",
                "label": node.name,
                "type": "function",
                "group": "functions",
                "line": node.lineno,
                "calls": list(calls)
            })
    
    # Creer les liens entre fonctions
    func_names = set(function_calls.keys())
    for func_name, calls in function_calls.items():
        for call in calls:
            if call in func_names:
                edges.append({
                    "source": f"func_{func_name}",
                    "target": f"func_{call}",
                    "type": "calls",
                    "label": "calls"
                })
            elif call in class_names:
                edges.append({
                    "source": f"func_{func_name}",
                    "target": f"class_{call}",
                    "type": "instantiates",
                    "label": "uses"
                })
            # Lien vers les imports (maintenant que 'imports' contient les bons noms)
            elif call in imports:
                edges.append({
                    "source": f"func_{func_name}",
                    "target": f"import_{call}",
                    "type": "calls",
                    "label": "uses"
                })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "filename": Path(filepath).name
    }
    """
    Analyse les dependances internes d'un fichier Python.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
    except:
        return {"nodes": [], "edges": [], "error": "Impossible de lire le fichier"}
    
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"nodes": [], "edges": [], "error": str(e)}
    
    nodes = []
    edges = []
    
    # Extraire les imports
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    
    for imp in imports:
        nodes.append({
            "id": f"import_{imp}",
            "label": imp,
            "type": "import",
            "group": "imports"
        })
    
    # Extraire les classes
    class_names = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_names.add(node.name)
            
            methods = []
            attributes = []
            
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        "name": item.name,
                        "line": item.lineno
                    })
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            attributes.append(target.id)
            
            nodes.append({
                "id": f"class_{node.name}",
                "label": node.name,
                "type": "class",
                "group": "classes",
                "line": node.lineno,
                "methods": methods,
                "attributes": attributes,
                "children": [{"id": f"method_{node.name}_{m['name']}", "label": m["name"], "type": "method"} for m in methods]
            })
            
            # Liens d'heritage
            for base in node.bases:
                if isinstance(base, ast.Name):
                    edges.append({
                        "source": f"class_{node.name}",
                        "target": f"class_{base.id}",
                        "type": "inherits",
                        "label": "extends"
                    })
    
    # Extraire les fonctions
    function_calls = {}  # fonction -> liste des fonctions appelees
    
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            calls = set()
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call):
                    if isinstance(subnode.func, ast.Name):
                        calls.add(subnode.func.id)
                    elif isinstance(subnode.func, ast.Attribute):
                        calls.add(subnode.func.attr)
            
            function_calls[node.name] = calls
            
            nodes.append({
                "id": f"func_{node.name}",
                "label": node.name,
                "type": "function",
                "group": "functions",
                "line": node.lineno,
                "calls": list(calls)
            })
    
    # Creer les liens entre fonctions
    func_names = set(function_calls.keys())
    for func_name, calls in function_calls.items():
        for call in calls:
            if call in func_names:
                edges.append({
                    "source": f"func_{func_name}",
                    "target": f"func_{call}",
                    "type": "calls",
                    "label": "calls"
                })
            elif call in class_names:
                edges.append({
                    "source": f"func_{func_name}",
                    "target": f"class_{call}",
                    "type": "instantiates",
                    "label": "uses"
                })
            # --- CORRECTION FINALE : Lien vers les imports ---
            elif call in imports:
                edges.append({
                    "source": f"func_{func_name}",
                    "target": f"import_{call}",
                    "type": "calls",
                    "label": "uses"
                })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "filename": Path(filepath).name
    }


def generate_interactive_graph_html(graph_data: dict, title: str = "Graphe de Dependances") -> str:
    """
    Genere un graphe interactif avec D3.js.
    Optimise pour le plein ecran et les distances dynamiques.
    """
    import json
    
    nodes_json = json.dumps(graph_data.get("nodes", []))
    edges_json = json.dumps(graph_data.get("edges", []))
    
    return """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>""" + title + """</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: white;
            overflow: hidden;
            width: 100vw;
            height: 100vh;
        }
        
        .header {
            position: fixed;
            top: 0;
            left: 0;
            padding: 16px 24px;
            z-index: 100;
            pointer-events: none; /* Laisse passer les clics vers le graphe */
        }
        .header h1 { 
            font-size: 18px; 
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            pointer-events: auto;
        }
        
        .legend {
            position: fixed;
            bottom: 20px;
            left: 20px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            background: rgba(15, 23, 42, 0.8);
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #1e293b;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #94a3b8;
        }
        .legend-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        
        #graph {
            width: 100%;
            height: 100%;
        }
        
        .node { cursor: pointer; }
        .node circle {
            stroke: #1e293b;
            stroke-width: 2px;
            transition: all 0.2s;
        }
        .node:hover circle {
            stroke: white;
            stroke-width: 3px;
        }
        .node text {
            font-size: 12px;
            fill: #e2e8f0;
            pointer-events: none;
            text-shadow: 0 1px 3px rgba(0,0,0,0.8);
        }
        
        .link {
            stroke-opacity: 0.4;
            fill: none;
        }
        .link.imports { stroke: #3b82f6; }
        .link.inherits { stroke: #22c55e; stroke-width: 2; }
        .link.calls { stroke: #f59e0b; stroke-dasharray: 4; }
        .link.instantiates { stroke: #8b5cf6; }
        
        .tooltip {
            position: fixed;
            background: rgba(30, 41, 59, 0.95);
            backdrop-filter: blur(4px);
            border: 1px solid #475569;
            border-radius: 8px;
            padding: 16px;
            max-width: 300px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            z-index: 1000;
            display: none;
            pointer-events: none;
        }
        .tooltip h3 { font-size: 14px; margin-bottom: 4px; color: #f8fafc; }
        .tooltip p { font-size: 12px; color: #94a3b8; margin-bottom: 2px; }
        .tooltip .type-badge {
            display: inline-block; padding: 2px 6px; border-radius: 4px;
            font-size: 10px; text-transform: uppercase; margin-bottom: 8px; font-weight: bold;
        }
        
        .controls {
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 8px;
        }
        .controls button {
            padding: 8px 16px;
            background: #1e293b;
            border: 1px solid #334155;
            color: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.2s;
        }
        .controls button:hover { background: #334155; }
    </style>
</head>
<body>
    <div class="header">
        <h1>""" + title + """</h1>
    </div>
    
    <div id="graph"></div>
    <div class="tooltip" id="tooltip"></div>
    
    <div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:#3b82f6"></div> Import</div>
        <div class="legend-item"><div class="legend-dot" style="background:#8b5cf6"></div> Classe</div>
        <div class="legend-item"><div class="legend-dot" style="background:#f59e0b"></div> Fonction</div>
        <div class="legend-item"><div class="legend-dot" style="background:#22c55e"></div> Module</div>
    </div>
    
    <div class="controls">
        <button onclick="resetZoom()">Recentrer</button>
        <button onclick="toggleLabels()">Labels On/Off</button>
    </div>
    
    <script>
        const nodes = """ + nodes_json + """;
        const links = """ + edges_json + """;
        
        // Configuration dynamique selon la taille de l'écran
        let width = window.innerWidth;
        let height = window.innerHeight;
        
        // Facteur de taille pour ajuster les distances sur grands/petits écrans
        const scaleFactor = Math.min(width, height) / 1000; 
        
        const colorMap = {
            'import': '#3b82f6',
            'class': '#8b5cf6',
            'function': '#f59e0b',
            'module': '#22c55e',
            'method': '#67e8f9'
        };
        
        const svg = d3.select('#graph')
            .append('svg')
            .attr('width', width)
            .attr('height', height);
        
        const g = svg.append('g');
        
        const zoom = d3.zoom()
            .scaleExtent([0.1, 8])
            .on('zoom', (event) => g.attr('transform', event.transform));
        
        svg.call(zoom);
        
        // Simulation physique optimisée
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links)
                .id(d => d.id)
                .distance(d => {
                    // Distance plus grande pour les héritages et imports
                    if (d.type === 'inherits') return 150 * scaleFactor;
                    return 100 * scaleFactor;
                })
            )
            .force('charge', d3.forceManyBody()
                .strength(d => {
                    // Répulsion plus forte pour les gros noeuds (modules/classes)
                    if (d.type === 'module') return -800 * scaleFactor;
                    if (d.type === 'class') return -600 * scaleFactor;
                    return -300 * scaleFactor;
                })
            )
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collide', d3.forceCollide().radius(d => {
                 return (d.type === 'module' ? 60 : 30) * scaleFactor;
            }).iterations(2));
        
        const link = g.append('g')
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('class', d => 'link ' + d.type)
            .attr('stroke-width', 1.5);
        
        const node = g.append('g')
            .selectAll('.node')
            .data(nodes)
            .join('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));
        
        node.append('circle')
            .attr('r', d => {
                const base = d.type === 'class' ? 20 : d.type === 'module' ? 25 : 12;
                return base * (scaleFactor < 0.8 ? 0.8 : 1); // Pas trop petit sur mobile
            })
            .attr('fill', d => colorMap[d.type] || '#64748b');
        
        let showLabels = true;
        const labels = node.append('text')
            .text(d => d.label)
            .attr('dx', d => d.type === 'module' ? 30 : 18)
            .attr('dy', 4)
            .style('font-size', d => d.type === 'module' ? '14px' : '11px')
            .style('font-weight', d => d.type === 'module' || d.type === 'class' ? 'bold' : 'normal');
        
        // Tooltip logic
        const tooltip = d3.select('#tooltip');
        
        node.on('mouseover', function(event, d) {
            let content = '<div class="type-badge" style="background:' + (colorMap[d.type] || '#64748b') + '">' + d.type + '</div>';
            content += '<h3>' + d.label + '</h3>';
            
            if (d.lines) content += '<p>Lignes: ' + d.lines + '</p>';
            if (d.methods) content += '<p>' + d.methods.length + ' méthodes</p>';
            if (d.calls) content += '<p>Appels sortants: ' + d.calls.length + '</p>';

            tooltip.html(content)
                .style('display', 'block')
                .style('left', (event.pageX + 15) + 'px')
                .style('top', (event.pageY + 15) + 'px');
                
            d3.select(this).select('circle').attr('stroke', 'white').attr('stroke-width', 3);
        })
        .on('mouseout', function() {
            tooltip.style('display', 'none');
            d3.select(this).select('circle').attr('stroke', '#1e293b').attr('stroke-width', 2);
        });
        
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            node.attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');
        });
        
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x; d.fy = d.y;
        }
        function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null; d.fy = null;
        }
        
        function resetZoom() {
            svg.transition().duration(750).call(
                zoom.transform, d3.zoomIdentity.translate(width/2, height/2).scale(1).translate(-width/2, -height/2)
            );
        }
        function toggleLabels() {
            showLabels = !showLabels;
            labels.style('display', showLabels ? 'block' : 'none');
        }
        
        // Gestion redimensionnement fenêtre
        window.addEventListener('resize', () => {
            width = window.innerWidth;
            height = window.innerHeight;
            svg.attr('width', width).attr('height', height);
            simulation.force('center', d3.forceCenter(width / 2, height / 2));
            simulation.alpha(0.3).restart();
        });
    </script>
</body>
</html>"""
    """
    Genere un graphe interactif avec D3.js.
    Permet de cliquer sur les noeuds pour voir les details.
    """
    import json
    
    nodes_json = json.dumps(graph_data.get("nodes", []))
    edges_json = json.dumps(graph_data.get("edges", []))
    
    return """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>""" + title + """</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: white;
            overflow: hidden;
        }
        
        .header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            padding: 16px 24px;
            background: rgba(15, 23, 42, 0.9);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid #1e293b;
            z-index: 100;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { font-size: 18px; }
        
        .legend {
            display: flex;
            gap: 16px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: #94a3b8;
        }
        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        #graph {
            width: 100vw;
            height: 100vh;
            padding-top: 60px;
        }
        
        .node {
            cursor: pointer;
        }
        .node circle {
            stroke: #1e293b;
            stroke-width: 2px;
            transition: all 0.2s;
        }
        .node:hover circle {
            stroke: white;
            stroke-width: 3px;
        }
        .node text {
            font-size: 11px;
            fill: #e2e8f0;
            pointer-events: none;
        }
        
        .link {
            stroke-opacity: 0.4;
            fill: none;
        }
        .link.imports { stroke: #3b82f6; }
        .link.inherits { stroke: #22c55e; stroke-width: 2; }
        .link.calls { stroke: #f59e0b; stroke-dasharray: 4; }
        .link.instantiates { stroke: #8b5cf6; }
        
        .tooltip {
            position: fixed;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 16px;
            max-width: 300px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            z-index: 1000;
            display: none;
        }
        .tooltip h3 {
            font-size: 14px;
            margin-bottom: 8px;
            color: #f8fafc;
        }
        .tooltip p {
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 4px;
        }
        .tooltip .type-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .tooltip .methods-list {
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #334155;
        }
        .tooltip .method-item {
            font-family: monospace;
            font-size: 11px;
            color: #67e8f9;
            padding: 2px 0;
        }
        
        .controls {
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 8px;
        }
        .controls button {
            padding: 10px 16px;
            background: #1e293b;
            border: 1px solid #334155;
            color: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
        }
        .controls button:hover {
            background: #334155;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>""" + title + """</h1>
        <div class="legend">
            <div class="legend-item"><div class="legend-dot" style="background:#3b82f6"></div> Import</div>
            <div class="legend-item"><div class="legend-dot" style="background:#8b5cf6"></div> Classe</div>
            <div class="legend-item"><div class="legend-dot" style="background:#f59e0b"></div> Fonction</div>
            <div class="legend-item"><div class="legend-dot" style="background:#22c55e"></div> Module</div>
        </div>
    </div>
    
    <div id="graph"></div>
    
    <div class="tooltip" id="tooltip"></div>
    
    <div class="controls">
        <button onclick="resetZoom()">Reset Vue</button>
        <button onclick="toggleLabels()">Labels</button>
    </div>
    
    <script>
        const nodes = """ + nodes_json + """;
        const links = """ + edges_json + """;
        
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        const colorMap = {
            'import': '#3b82f6',
            'class': '#8b5cf6',
            'function': '#f59e0b',
            'module': '#22c55e',
            'method': '#67e8f9'
        };
        
        const svg = d3.select('#graph')
            .append('svg')
            .attr('width', width)
            .attr('height', height);
        
        const g = svg.append('g');
        
        // Zoom
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });
        
        svg.call(zoom);
        
        // Simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(40));
        
        // Links
        const link = g.append('g')
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('class', d => 'link ' + d.type)
            .attr('stroke-width', 1.5);
        
        // Nodes
        const node = g.append('g')
            .selectAll('.node')
            .data(nodes)
            .join('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));
        
        node.append('circle')
            .attr('r', d => d.type === 'class' ? 20 : d.type === 'module' ? 25 : 15)
            .attr('fill', d => colorMap[d.type] || '#64748b');
        
        let showLabels = true;
        const labels = node.append('text')
            .text(d => d.label)
            .attr('dx', 25)
            .attr('dy', 4);
        
        // Tooltip
        const tooltip = d3.select('#tooltip');
        
        node.on('click', function(event, d) {
            event.stopPropagation();
            
            let content = '<div class="type-badge" style="background:' + (colorMap[d.type] || '#64748b') + '">' + d.type + '</div>';
            content += '<h3>' + d.label + '</h3>';
            
            if (d.line) content += '<p>Ligne: ' + d.line + '</p>';
            if (d.lines) content += '<p>Lignes: ' + d.lines + '</p>';
            
            if (d.methods && d.methods.length > 0) {
                content += '<div class="methods-list"><p>Methodes:</p>';
                d.methods.forEach(m => {
                    content += '<div class="method-item">' + (m.name || m) + '()</div>';
                });
                content += '</div>';
            }
            
            if (d.attributes && d.attributes.length > 0) {
                content += '<p>Attributs: ' + d.attributes.join(', ') + '</p>';
            }
            
            if (d.calls && d.calls.length > 0) {
                content += '<p>Appelle: ' + d.calls.slice(0, 5).join(', ') + '</p>';
            }
            
            if (d.children && d.children.length > 0) {
                content += '<div class="methods-list"><p>Contient:</p>';
                d.children.forEach(c => {
                    content += '<div class="method-item">' + c.label + '</div>';
                });
                content += '</div>';
            }
            
            tooltip.html(content)
                .style('display', 'block')
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY + 10) + 'px');
        });
        
        svg.on('click', () => {
            tooltip.style('display', 'none');
        });
        
        // Update positions
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            node.attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');
        });
        
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        function resetZoom() {
            svg.transition().duration(750).call(
                zoom.transform,
                d3.zoomIdentity.translate(width / 2, height / 2).scale(1).translate(-width / 2, -height / 2)
            );
        }
        
        function toggleLabels() {
            showLabels = !showLabels;
            labels.style('display', showLabels ? 'block' : 'none');
        }
    </script>
</body>
</html>"""