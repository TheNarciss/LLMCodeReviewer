"""
Generateur de rapports HTML professionnels.
Inclut graphes de dependances, metriques detaillees, etc.
"""

from datetime import datetime
from pathlib import Path
from analyser import analyze_file, analyze_code_string, calculate_quality_score


def generate_report_data(filepath: str, original_code: str, corrected_code: str, has_docstrings: bool = False) -> dict:
    """
    Genere les donnees completes du rapport pour un fichier.
    """
    # Analyse du fichier original
    analysis_original = analyze_file(filepath)
    
    # Analyse du code corrige
    analysis_corrected = analyze_code_string(corrected_code)
    
    # Scores
    score_before = calculate_quality_score(analysis_original)
    score_after = calculate_quality_score(analysis_corrected)
    
    return {
        "filename": Path(filepath).name,
        "filepath": filepath,
        "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        
        # Scores
        "score_before": score_before,
        "score_after": score_after,
        "score": score_after,
        "improvement": score_after - score_before,
        
        # Donnees originales
        "original": analysis_original,
        
        # Donnees corrigees
        "corrected": analysis_corrected,
        
        # Flags
        "has_changes": original_code != corrected_code,
        "has_docstrings": has_docstrings,
        
        # Pour compatibilite
        "functions": [f["name"] for f in analysis_original.get("functions", [])],
        "classes": [c["name"] for c in analysis_original.get("classes", [])],
        "style_issues": analysis_original.get("style_issues", []),
        "status_color": get_score_color(score_after)
    }


def get_score_color(score):
    """Retourne la couleur selon le score."""
    if score >= 80:
        return "#22c55e"
    elif score >= 60:
        return "#f59e0b"
    else:
        return "#ef4444"


def get_complexity_color(complexity):
    """Retourne la couleur selon la complexite."""
    if complexity <= 5:
        return "#22c55e"
    elif complexity <= 10:
        return "#84cc16"
    elif complexity <= 20:
        return "#f59e0b"
    else:
        return "#ef4444"


def generate_dependency_svg(graph):
    """Genere un SVG simple pour le graphe de dependances."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    
    if not nodes:
        return ""
    
    # Positions simples
    width = 800
    height = max(400, len(nodes) * 60)
    
    # Grouper par type
    imports = [n for n in nodes if n["type"] == "import"]
    classes = [n for n in nodes if n["type"] == "class"]
    functions = [n for n in nodes if n["type"] == "function"]
    
    svg_parts = []
    svg_parts.append('<svg viewBox="0 0 ' + str(width) + ' ' + str(height) + '" xmlns="http://www.w3.org/2000/svg">')
    svg_parts.append('<style>')
    svg_parts.append('.node-import { fill: #dbeafe; stroke: #3b82f6; }')
    svg_parts.append('.node-class { fill: #dcfce7; stroke: #22c55e; }')
    svg_parts.append('.node-function { fill: #fef3c7; stroke: #f59e0b; }')
    svg_parts.append('.node-text { font-family: system-ui; font-size: 12px; }')
    svg_parts.append('.edge { stroke: #94a3b8; stroke-width: 1; fill: none; }')
    svg_parts.append('.edge-inherits { stroke: #22c55e; stroke-width: 2; }')
    svg_parts.append('.edge-calls { stroke: #3b82f6; stroke-dasharray: 4; }')
    svg_parts.append('</style>')
    
    # Positions des noeuds
    positions = {}
    y_offset = 40
    
    # Colonne 1: Imports
    for i, node in enumerate(imports):
        x = 80
        y = y_offset + i * 50
        positions[node["id"]] = (x, y)
        svg_parts.append('<rect x="' + str(x-60) + '" y="' + str(y-15) + '" width="120" height="30" rx="4" class="node-import"/>')
        svg_parts.append('<text x="' + str(x) + '" y="' + str(y+4) + '" text-anchor="middle" class="node-text">' + node["label"][:15] + '</text>')
    
    # Colonne 2: Classes
    col2_y = y_offset
    for i, node in enumerate(classes):
        x = 300
        y = col2_y + i * 70
        positions[node["id"]] = (x, y)
        svg_parts.append('<rect x="' + str(x-70) + '" y="' + str(y-20) + '" width="140" height="40" rx="4" class="node-class"/>')
        svg_parts.append('<text x="' + str(x) + '" y="' + str(y) + '" text-anchor="middle" class="node-text" font-weight="bold">' + node["label"][:18] + '</text>')
        svg_parts.append('<text x="' + str(x) + '" y="' + str(y+14) + '" text-anchor="middle" class="node-text" font-size="10">' + str(node.get("methods", 0)) + ' methods</text>')
    
    # Colonne 3: Fonctions
    col3_y = y_offset
    for i, node in enumerate(functions):
        x = 550
        y = col3_y + i * 50
        positions[node["id"]] = (x, y)
        complexity = node.get("complexity", 1)
        color = get_complexity_color(complexity)
        svg_parts.append('<rect x="' + str(x-70) + '" y="' + str(y-15) + '" width="140" height="30" rx="4" class="node-function"/>')
        svg_parts.append('<text x="' + str(x) + '" y="' + str(y+4) + '" text-anchor="middle" class="node-text">' + node["label"][:18] + '</text>')
        svg_parts.append('<circle cx="' + str(x+60) + '" cy="' + str(y) + '" r="10" fill="' + color + '"/>')
        svg_parts.append('<text x="' + str(x+60) + '" y="' + str(y+4) + '" text-anchor="middle" class="node-text" fill="white" font-size="10">' + str(complexity) + '</text>')
    
    # Edges
    for edge in edges:
        from_pos = positions.get(edge["from"])
        to_pos = positions.get(edge["to"])
        if from_pos and to_pos:
            edge_class = "edge"
            if edge["type"] == "inherits":
                edge_class = "edge edge-inherits"
            elif edge["type"] == "calls":
                edge_class = "edge edge-calls"
            
            svg_parts.append('<path d="M' + str(from_pos[0]+70) + ',' + str(from_pos[1]) + ' C' + str(from_pos[0]+100) + ',' + str(from_pos[1]) + ' ' + str(to_pos[0]-100) + ',' + str(to_pos[1]) + ' ' + str(to_pos[0]-70) + ',' + str(to_pos[1]) + '" class="' + edge_class + '"/>')
    
    # Legende
    svg_parts.append('<rect x="' + str(width-180) + '" y="' + str(height-90) + '" width="170" height="80" fill="white" stroke="#e2e8f0" rx="4"/>')
    svg_parts.append('<text x="' + str(width-170) + '" y="' + str(height-70) + '" class="node-text" font-weight="bold">Legende</text>')
    svg_parts.append('<rect x="' + str(width-170) + '" y="' + str(height-55) + '" width="12" height="12" class="node-import"/>')
    svg_parts.append('<text x="' + str(width-155) + '" y="' + str(height-45) + '" class="node-text">Import</text>')
    svg_parts.append('<rect x="' + str(width-170) + '" y="' + str(height-40) + '" width="12" height="12" class="node-class"/>')
    svg_parts.append('<text x="' + str(width-155) + '" y="' + str(height-30) + '" class="node-text">Classe</text>')
    svg_parts.append('<rect x="' + str(width-170) + '" y="' + str(height-25) + '" width="12" height="12" class="node-function"/>')
    svg_parts.append('<text x="' + str(width-155) + '" y="' + str(height-15) + '" class="node-text">Fonction</text>')
    
    svg_parts.append('</svg>')
    
    return '\n'.join(svg_parts)


def generate_html_report(report_data: dict) -> str:
    """
    Genere un rapport HTML professionnel complet.
    """
    original = report_data.get("original", {})
    corrected = report_data.get("corrected", {})
    
    score_before = report_data.get("score_before", 0)
    score_after = report_data.get("score_after", 0)
    improvement = report_data.get("improvement", 0)
    
    # Construire les sections
    
    # Section Imports
    imports = original.get("imports", [])
    imports_html = ""
    if imports:
        imports_rows = ""
        for imp in imports:
            module = imp.get("module", "")
            name = imp.get("name", "")
            if imp["type"] == "from":
                imports_rows += "<tr><td>from " + module + "</td><td>" + name + "</td><td>" + str(imp.get("line", "")) + "</td></tr>"
            else:
                imports_rows += "<tr><td>import</td><td>" + module + "</td><td>" + str(imp.get("line", "")) + "</td></tr>"
        imports_html = """
        <div class="section">
            <h2>Imports (""" + str(len(imports)) + """)</h2>
            <table class="data-table">
                <thead><tr><th>Type</th><th>Module</th><th>Ligne</th></tr></thead>
                <tbody>""" + imports_rows + """</tbody>
            </table>
        </div>
        """
    
    # Section Classes
    classes = original.get("classes", [])
    classes_html = ""
    if classes:
        classes_content = ""
        for cls in classes:
            methods_list = ""
            for m in cls.get("methods", []):
                complexity_color = get_complexity_color(m.get("complexity", 1))
                doc_icon = "check" if m.get("has_docstring") else "x"
                doc_color = "#22c55e" if m.get("has_docstring") else "#ef4444"
                methods_list += """
                <div class="method-item">
                    <span class="method-name">""" + m["name"] + """()</span>
                    <span class="method-meta">
                        <span class="complexity-badge" style="background:""" + complexity_color + """">C:""" + str(m.get("complexity", 1)) + """</span>
                        <span class="doc-indicator" style="color:""" + doc_color + """">""" + doc_icon + """</span>
                    </span>
                </div>
                """
            
            bases_str = ""
            if cls.get("bases"):
                bases_str = " extends " + ", ".join(cls["bases"])
            
            doc_status = "Documentee" if cls.get("has_docstring") else "Non documentee"
            doc_color = "#22c55e" if cls.get("has_docstring") else "#ef4444"
            
            classes_content += """
            <div class="class-card">
                <div class="class-header">
                    <h3>""" + cls["name"] + bases_str + """</h3>
                    <span class="badge" style="background:""" + doc_color + """;color:white">""" + doc_status + """</span>
                </div>
                <div class="class-meta">
                    <span>""" + str(cls.get("method_count", 0)) + """ methodes</span>
                    <span>""" + str(len(cls.get("attributes", []))) + """ attributs</span>
                    <span>Lignes """ + str(cls.get("line", "")) + """-""" + str(cls.get("end_line", "")) + """</span>
                </div>
                <div class="methods-list">""" + methods_list + """</div>
            </div>
            """
        
        classes_html = """
        <div class="section">
            <h2>Classes (""" + str(len(classes)) + """)</h2>
            """ + classes_content + """
        </div>
        """
    
    # Section Fonctions
    functions = original.get("functions", [])
    functions_html = ""
    if functions:
        func_rows = ""
        for func in functions:
            complexity = func.get("complexity", 1)
            complexity_color = get_complexity_color(complexity)
            doc_icon = "Oui" if func.get("has_docstring") else "Non"
            doc_color = "#22c55e" if func.get("has_docstring") else "#ef4444"
            
            args_str = ", ".join([a["name"] for a in func.get("args", [])])
            return_type = func.get("return_type", "-")
            
            func_rows += """
            <tr>
                <td><code>""" + func["name"] + """</code></td>
                <td>""" + args_str + """</td>
                <td>""" + str(return_type) + """</td>
                <td><span class="complexity-badge" style="background:""" + complexity_color + """">""" + str(complexity) + """</span></td>
                <td style="color:""" + doc_color + """">""" + doc_icon + """</td>
                <td>""" + str(func.get("lines", 0)) + """</td>
            </tr>
            """
        
        functions_html = """
        <div class="section">
            <h2>Fonctions (""" + str(len(functions)) + """)</h2>
            <table class="data-table">
                <thead><tr><th>Nom</th><th>Arguments</th><th>Retour</th><th>Complexite</th><th>Doc</th><th>Lignes</th></tr></thead>
                <tbody>""" + func_rows + """</tbody>
            </table>
        </div>
        """
    
    # Section Variables/Constantes
    variables = original.get("variables", [])
    constants = original.get("constants", [])
    vars_html = ""
    if variables or constants:
        var_items = ""
        for v in constants:
            var_items += '<div class="var-item const"><span class="var-name">' + v["name"] + '</span><span class="var-value">' + str(v.get("value", ""))[:30] + '</span></div>'
        for v in variables:
            if not v.get("is_constant"):
                var_items += '<div class="var-item"><span class="var-name">' + v["name"] + '</span><span class="var-type">' + v.get("type", "")[:20] + '</span></div>'
        
        vars_html = """
        <div class="section">
            <h2>Variables Globales</h2>
            <div class="vars-grid">""" + var_items + """</div>
        </div>
        """
    
    # Section Style Issues
    style_issues = original.get("style_issues", [])
    issues_html = ""
    if style_issues:
        issues_list = ""
        for issue in style_issues[:30]:
            issues_list += '<div class="issue-item">' + str(issue) + '</div>'
        more_text = ""
        if len(style_issues) > 30:
            more_text = '<p class="more-text">... et ' + str(len(style_issues) - 30) + ' autres problemes</p>'
        
        issues_html = """
        <div class="section">
            <h2>Problemes de Style (""" + str(len(style_issues)) + """)</h2>
            """ + issues_list + more_text + """
        </div>
        """
    
    # Section Graphe de dependances
    graph = original.get("dependency_graph", {})
    graph_svg = generate_dependency_svg(graph)
    graph_html = ""
    if graph_svg:
        graph_html = """
        <div class="section">
            <h2>Graphe de Dependances</h2>
            <div class="graph-container">""" + graph_svg + """</div>
        </div>
        """
    
    # Couleurs pour les scores
    before_color = get_score_color(score_before)
    after_color = get_score_color(score_after)
    
    # Texte d'amelioration
    if improvement > 0:
        improvement_text = "+" + str(improvement) + " points"
        improvement_bg = "#dcfce7"
        improvement_color = "#166534"
    elif improvement == 0:
        improvement_text = "Pas de changement"
        improvement_bg = "#f1f5f9"
        improvement_color = "#64748b"
    else:
        improvement_text = str(improvement) + " points"
        improvement_bg = "#fef2f2"
        improvement_color = "#991b1b"
    
    # Badges de statut
    if report_data.get("has_changes"):
        pep8_badge = '<span class="status-badge success">PEP8 corrige</span>'
    else:
        pep8_badge = '<span class="status-badge neutral">Deja conforme</span>'
    
    if report_data.get("has_docstrings"):
        doc_badge = '<span class="status-badge success">Docstrings ajoutees</span>'
    else:
        doc_badge = '<span class="status-badge neutral">Sans docstrings IA</span>'
    
    # Assemblage du HTML
    html = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport - """ + report_data["filename"] + """</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f1f5f9;
            color: #1e293b;
            line-height: 1.6;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 24px;
        }
        .header {
            background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
            color: white;
            padding: 40px;
            margin: -24px -24px 24px -24px;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 8px;
        }
        .header p {
            opacity: 0.8;
            font-size: 14px;
        }
        
        .scores-panel {
            display: grid;
            grid-template-columns: 1fr 1fr auto;
            gap: 20px;
            margin-bottom: 24px;
        }
        .score-card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .score-card.before { border-top: 4px solid """ + before_color + """; }
        .score-card.after { border-top: 4px solid """ + after_color + """; }
        .score-value {
            font-size: 48px;
            font-weight: 700;
        }
        .score-card.before .score-value { color: """ + before_color + """; }
        .score-card.after .score-value { color: """ + after_color + """; }
        .score-label {
            color: #64748b;
            font-size: 14px;
            margin-top: 4px;
        }
        .improvement-card {
            background: """ + improvement_bg + """;
            border-radius: 12px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .improvement-value {
            font-size: 24px;
            font-weight: 700;
            color: """ + improvement_color + """;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .metric-value {
            font-size: 28px;
            font-weight: 700;
            color: #3b82f6;
        }
        .metric-label {
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
        }
        
        .status-bar {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
        }
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
        }
        .status-badge.success { background: #dcfce7; color: #166534; }
        .status-badge.neutral { background: #f1f5f9; color: #64748b; }
        
        .section {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .section h2 {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid #e2e8f0;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
        }
        .data-table th, .data-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        .data-table th {
            background: #f8fafc;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            color: #64748b;
        }
        .data-table td {
            font-size: 13px;
        }
        .data-table code {
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }
        
        .complexity-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
            color: white;
        }
        
        .class-card {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            margin-bottom: 16px;
            overflow: hidden;
        }
        .class-header {
            background: #f8fafc;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .class-header h3 {
            font-size: 15px;
            font-weight: 600;
        }
        .class-meta {
            padding: 8px 16px;
            font-size: 12px;
            color: #64748b;
            display: flex;
            gap: 16px;
            border-bottom: 1px solid #e2e8f0;
        }
        .methods-list {
            padding: 12px 16px;
        }
        .method-item {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid #f1f5f9;
        }
        .method-item:last-child { border-bottom: none; }
        .method-name {
            font-family: monospace;
            font-size: 13px;
        }
        .method-meta {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        
        .vars-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 8px;
        }
        .var-item {
            background: #f8fafc;
            padding: 10px 14px;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            font-size: 13px;
        }
        .var-item.const {
            background: #fef3c7;
        }
        .var-name {
            font-family: monospace;
            font-weight: 500;
        }
        .var-type, .var-value {
            color: #64748b;
            font-size: 12px;
        }
        
        .issue-item {
            padding: 8px 12px;
            background: #fef2f2;
            border-left: 3px solid #ef4444;
            margin-bottom: 6px;
            font-size: 12px;
            font-family: monospace;
            color: #991b1b;
            border-radius: 0 6px 6px 0;
        }
        .more-text {
            color: #64748b;
            font-size: 13px;
            margin-top: 12px;
        }
        
        .graph-container {
            background: #f8fafc;
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
        }
        .graph-container svg {
            max-width: 100%;
            height: auto;
        }
        
        .badge {
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }
        
        .footer {
            text-align: center;
            padding: 24px;
            color: #94a3b8;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>""" + report_data["filename"] + """</h1>
            <p>Rapport genere le """ + report_data["date"] + """</p>
        </div>
        
        <div class="scores-panel">
            <div class="score-card before">
                <div class="score-value">""" + str(score_before) + """</div>
                <div class="score-label">Score Avant</div>
            </div>
            <div class="score-card after">
                <div class="score-value">""" + str(score_after) + """</div>
                <div class="score-label">Score Apres</div>
            </div>
            <div class="improvement-card">
                <div class="improvement-value">""" + improvement_text + """</div>
                <div class="score-label">Amelioration</div>
            </div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">""" + str(original.get("lines", 0)) + """</div>
                <div class="metric-label">Lignes totales</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">""" + str(original.get("code_lines", 0)) + """</div>
                <div class="metric-label">Lignes de code</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">""" + str(len(functions)) + """</div>
                <div class="metric-label">Fonctions</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">""" + str(len(classes)) + """</div>
                <div class="metric-label">Classes</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">""" + str(original.get("avg_complexity", 0)) + """</div>
                <div class="metric-label">Complexite moy.</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">""" + str(original.get("doc_coverage", 0)) + """%</div>
                <div class="metric-label">Couverture doc</div>
            </div>
        </div>
        
        <div class="status-bar">
            """ + pep8_badge + """
            """ + doc_badge + """
        </div>
        
        """ + graph_html + """
        """ + classes_html + """
        """ + functions_html + """
        """ + imports_html + """
        """ + vars_html + """
        """ + issues_html + """
        
        <div class="footer">
            Rapport genere par AgentIA Code Standardizer
        </div>
    </div>
</body>
</html>"""
    
    return html


def generate_global_report(files_data: list, job_id: str) -> str:
    """Genere un rapport global pour tous les fichiers."""
    
    total_files = len(files_data)
    if total_files == 0:
        return "<html><body>Aucun fichier</body></html>"
    
    total_functions = sum(len(f.get("functions", [])) for f in files_data)
    total_classes = sum(len(f.get("classes", [])) for f in files_data)
    total_issues = sum(len(f.get("style_issues", [])) for f in files_data)
    avg_score = sum(f.get("score", 0) for f in files_data) // total_files
    
    avg_improvement = sum(f.get("improvement", 0) for f in files_data) // total_files
    
    files_rows = ""
    for f in files_data:
        score_before = f.get("score_before", 0)
        score_after = f.get("score_after", 0)
        improvement = f.get("improvement", 0)
        
        imp_color = "#22c55e" if improvement > 0 else "#64748b"
        imp_text = "+" + str(improvement) if improvement > 0 else str(improvement)
        
        files_rows += """
        <tr>
            <td><code>""" + f.get("filename", "") + """</code></td>
            <td>""" + str(score_before) + """</td>
            <td style="color:""" + get_score_color(score_after) + """;font-weight:600">""" + str(score_after) + """</td>
            <td style="color:""" + imp_color + """">""" + imp_text + """</td>
            <td>""" + str(len(f.get("functions", []))) + """</td>
            <td>""" + str(len(f.get("classes", []))) + """</td>
            <td>""" + str(len(f.get("style_issues", []))) + """</td>
        </tr>
        """
    
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    return """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Rapport Global - Job """ + job_id + """</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f1f5f9;
            color: #1e293b;
            padding: 24px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
            color: white;
            padding: 40px;
            border-radius: 12px 12px 0 0;
        }
        .header h1 { font-size: 28px; margin-bottom: 8px; }
        .header p { opacity: 0.8; }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            background: white;
        }
        .stat {
            padding: 24px;
            text-align: center;
            border-right: 1px solid #e2e8f0;
        }
        .stat:last-child { border-right: none; }
        .stat-value { font-size: 32px; font-weight: 700; color: #3b82f6; }
        .stat-label { font-size: 12px; color: #64748b; margin-top: 4px; }
        
        .content {
            background: white;
            padding: 24px;
            border-radius: 0 0 12px 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }
        .content h2 {
            font-size: 16px;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid #e2e8f0;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 14px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            background: #f8fafc;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            color: #64748b;
        }
        td { font-size: 14px; }
        td code {
            background: #f1f5f9;
            padding: 4px 8px;
            border-radius: 4px;
        }
        
        .footer {
            text-align: center;
            padding: 24px;
            color: #94a3b8;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Rapport Global</h1>
            <p>Job """ + job_id + """ - """ + current_date + """</p>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value">""" + str(avg_score) + """</div>
                <div class="stat-label">Score moyen</div>
            </div>
            <div class="stat">
                <div class="stat-value">+""" + str(avg_improvement) + """</div>
                <div class="stat-label">Amelioration moy.</div>
            </div>
            <div class="stat">
                <div class="stat-value">""" + str(total_files) + """</div>
                <div class="stat-label">Fichiers</div>
            </div>
            <div class="stat">
                <div class="stat-value">""" + str(total_functions) + """</div>
                <div class="stat-label">Fonctions</div>
            </div>
            <div class="stat">
                <div class="stat-value">""" + str(total_classes) + """</div>
                <div class="stat-label">Classes</div>
            </div>
        </div>
        
        <div class="content">
            <h2>Details par fichier</h2>
            <table>
                <thead>
                    <tr>
                        <th>Fichier</th>
                        <th>Avant</th>
                        <th>Apres</th>
                        <th>+/-</th>
                        <th>Fonctions</th>
                        <th>Classes</th>
                        <th>Problemes</th>
                    </tr>
                </thead>
                <tbody>""" + files_rows + """</tbody>
            </table>
        </div>
        
        <div class="footer">
            Rapport genere par AgentIA Code Standardizer
        </div>
    </div>
</body>
</html>"""