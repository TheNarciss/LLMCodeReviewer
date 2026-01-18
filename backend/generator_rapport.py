"""
Generateur de rapports HTML unifies.
Combine: analyse, documentation, profiling dans un seul fichier.
"""

from datetime import datetime
from pathlib import Path
from analyser import analyze_file, analyze_code_string, calculate_quality_score


def generate_report_data(filepath: str, original_code: str, corrected_code: str, 
                         has_docstrings: bool = False, profile_data: dict = None) -> dict:
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
        
        # Code
        "original_code": original_code,
        "corrected_code": corrected_code,
        
        # Flags
        "has_changes": original_code != corrected_code,
        "has_docstrings": has_docstrings,
        
        # Profiling
        "profile": profile_data,
        
        # Pour compatibilite
        "functions": [f["name"] for f in analysis_original.get("functions", [])],
        "classes": [c["name"] for c in analysis_original.get("classes", [])],
        "style_issues": analysis_original.get("style_issues", []),
        "status_color": get_score_color(score_after)
    }


def get_score_color(score):
    if score >= 80:
        return "#22c55e"
    elif score >= 60:
        return "#f59e0b"
    else:
        return "#ef4444"


def get_complexity_color(complexity):
    if complexity <= 5:
        return "#22c55e"
    elif complexity <= 10:
        return "#84cc16"
    elif complexity <= 20:
        return "#f59e0b"
    else:
        return "#ef4444"


def generate_html_report(report_data: dict) -> str:
    """
    Genere un rapport HTML unifie avec toutes les sections:
    - Scores et metriques
    - Documentation (classes, fonctions, imports)
    - Profiling (si disponible)
    - Problemes de style
    """
    original = report_data.get("original", {})
    profile = report_data.get("profile")
    
    score_before = report_data.get("score_before", 0)
    score_after = report_data.get("score_after", 0)
    improvement = report_data.get("improvement", 0)
    
    # === SECTION IMPORTS ===
    imports = original.get("imports", [])
    imports_html = ""
    if imports:
        imports_rows = ""
        for imp in imports:
            module = imp.get("module", "")
            name = imp.get("name", "")
            line = str(imp.get("line", ""))
            if imp["type"] == "from":
                imports_rows += "<tr><td><code>from " + module + " import " + name + "</code></td><td>" + line + "</td></tr>"
            else:
                imports_rows += "<tr><td><code>import " + module + "</code></td><td>" + line + "</td></tr>"
        imports_html = """
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>📦 Imports (""" + str(len(imports)) + """)</h2>
                <span class="toggle">▼</span>
            </div>
            <div class="section-content">
                <table><thead><tr><th>Import</th><th>Ligne</th></tr></thead>
                <tbody>""" + imports_rows + """</tbody></table>
            </div>
        </div>
        """
    
    # === SECTION CLASSES (DOCUMENTATION) ===
    classes = original.get("classes", [])
    classes_html = ""
    if classes:
        classes_content = ""
        for cls in classes:
            # Bases
            bases_str = ""
            if cls.get("bases"):
                bases_str = "(" + ", ".join(cls["bases"]) + ")"
            
            # Docstring
            doc_html = ""
            if cls.get("docstring"):
                doc_html = '<p class="docstring">' + cls["docstring"].replace('\n', '<br>') + '</p>'
            
            # Attributs
            attrs_html = ""
            if cls.get("attributes"):
                attrs_html = '<div class="attrs"><strong>Attributs:</strong> ' + ", ".join(cls["attributes"]) + '</div>'
            
            # Methodes
            methods_html = ""
            for m in cls.get("methods", []):
                complexity = m.get("complexity", 1)
                c_color = get_complexity_color(complexity)
                doc_icon = "✓" if m.get("has_docstring") else "✗"
                doc_color = "#22c55e" if m.get("has_docstring") else "#ef4444"
                args_str = ", ".join(m.get("args", []))
                
                methods_html += """
                <div class="method">
                    <code>""" + m["name"] + """(""" + args_str + """)</code>
                    <span class="badge" style="background:""" + c_color + """">C:""" + str(complexity) + """</span>
                    <span style="color:""" + doc_color + """">""" + doc_icon + """</span>
                </div>
                """
            
            doc_badge = '<span class="badge badge-green">Doc ✓</span>' if cls.get("has_docstring") else '<span class="badge badge-gray">Doc ✗</span>'
            
            classes_content += """
            <div class="class-card">
                <div class="class-header">
                    <h3>class """ + cls["name"] + bases_str + """</h3>
                    """ + doc_badge + """
                    <span class="line-info">L.""" + str(cls.get("line", "")) + """</span>
                </div>
                """ + doc_html + """
                """ + attrs_html + """
                <div class="methods">""" + methods_html + """</div>
            </div>
            """
        
        classes_html = """
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>🏗️ Classes (""" + str(len(classes)) + """)</h2>
                <span class="toggle">▼</span>
            </div>
            <div class="section-content">""" + classes_content + """</div>
        </div>
        """
    
    # === SECTION FONCTIONS (DOCUMENTATION) ===
    functions = original.get("functions", [])
    functions_html = ""
    if functions:
        func_rows = ""
        for func in functions:
            complexity = func.get("complexity", 1)
            c_color = get_complexity_color(complexity)
            doc_icon = "✓" if func.get("has_docstring") else "✗"
            doc_color = "#22c55e" if func.get("has_docstring") else "#ef4444"
            
            args_list = func.get("args", [])
            args_str = ", ".join([a["name"] + (": " + a.get("type", "") if a.get("type") else "") for a in args_list])
            return_type = func.get("return_type") or "-"
            
            # Docstring tooltip
            doc_preview = ""
            if func.get("docstring"):
                doc_preview = func["docstring"][:100].replace('"', "'")
            
            func_rows += """
            <tr title=\"""" + doc_preview + """\">
                <td><code>""" + func["name"] + """</code></td>
                <td class="args">""" + args_str + """</td>
                <td>""" + return_type + """</td>
                <td><span class="badge" style="background:""" + c_color + """">""" + str(complexity) + """</span></td>
                <td style="color:""" + doc_color + """">""" + doc_icon + """</td>
                <td>""" + str(func.get("lines", 0)) + """</td>
            </tr>
            """
        
        functions_html = """
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>⚡ Fonctions (""" + str(len(functions)) + """)</h2>
                <span class="toggle">▼</span>
            </div>
            <div class="section-content">
                <table>
                    <thead><tr><th>Nom</th><th>Arguments</th><th>Retour</th><th>Complexite</th><th>Doc</th><th>Lignes</th></tr></thead>
                    <tbody>""" + func_rows + """</tbody>
                </table>
            </div>
        </div>
        """
    
    # === SECTION VARIABLES ===
    variables = original.get("variables", [])
    constants = original.get("constants", [])
    vars_html = ""
    if variables or constants:
        var_items = ""
        for v in constants:
            var_items += '<div class="var const"><code>' + v["name"] + '</code> = ' + str(v.get("value", ""))[:30] + '</div>'
        for v in variables:
            if not v.get("is_constant"):
                var_items += '<div class="var"><code>' + v["name"] + '</code> <span class="type">' + v.get("type", "")[:20] + '</span></div>'
        
        vars_html = """
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>📊 Variables Globales (""" + str(len(variables) + len(constants)) + """)</h2>
                <span class="toggle">▼</span>
            </div>
            <div class="section-content">
                <div class="vars-grid">""" + var_items + """</div>
            </div>
        </div>
        """
    
    # === SECTION PROFILING ===
    profile_html = ""
    if profile and profile.get("functions"):
        profile_funcs = profile.get("functions", [])[:15]
        total_time = profile.get("total_time", 0.001)
        
        profile_rows = ""
        for pf in profile_funcs:
            pct = (pf["cumtime"] / total_time * 100) if total_time > 0 else 0
            color = "#22c55e" if pct < 10 else "#f59e0b" if pct < 30 else "#ef4444"
            bar_width = min(100, pct * 2)
            
            profile_rows += """
            <tr>
                <td><code>""" + pf["name"] + """</code></td>
                <td>""" + str(pf["ncalls"]) + """</td>
                <td>""" + str(round(pf["cumtime"] * 1000, 2)) + """ms</td>
                <td>
                    <div class="bar-container">
                        <div class="bar" style="width:""" + str(bar_width) + """%;background:""" + color + """"></div>
                        <span>""" + str(round(pct, 1)) + """%</span>
                    </div>
                </td>
            </tr>
            """
        
        profile_html = """
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>⏱️ Profiling (""" + str(round(total_time * 1000, 2)) + """ms total)</h2>
                <span class="toggle">▼</span>
            </div>
            <div class="section-content">
                <table>
                    <thead><tr><th>Fonction</th><th>Appels</th><th>Temps</th><th>% du total</th></tr></thead>
                    <tbody>""" + profile_rows + """</tbody>
                </table>
            </div>
        </div>
        """
    
    # === SECTION PROBLEMES ===
    style_issues = original.get("style_issues", [])
    issues_html = ""
    if style_issues:
        issues_list = ""
        for issue in style_issues[:25]:
            issues_list += '<div class="issue">' + str(issue) + '</div>'
        more_text = ""
        if len(style_issues) > 25:
            more_text = '<p class="more">... et ' + str(len(style_issues) - 25) + ' autres problemes</p>'
        
        issues_html = """
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>⚠️ Problemes de Style (""" + str(len(style_issues)) + """)</h2>
                <span class="toggle">▼</span>
            </div>
            <div class="section-content">
                """ + issues_list + more_text + """
            </div>
        </div>
        """
    
    # === COULEURS SCORES ===
    before_color = get_score_color(score_before)
    after_color = get_score_color(score_after)
    
    if improvement > 0:
        imp_text = "+" + str(improvement)
        imp_bg = "#dcfce7"
        imp_color = "#166534"
    elif improvement == 0:
        imp_text = "="
        imp_bg = "#f1f5f9"
        imp_color = "#64748b"
    else:
        imp_text = str(improvement)
        imp_bg = "#fef2f2"
        imp_color = "#991b1b"
    
    # === BADGES STATUT ===
    pep8_badge = '<span class="status-badge green">PEP8 ✓</span>' if report_data.get("has_changes") else '<span class="status-badge gray">Deja conforme</span>'
    doc_badge = '<span class="status-badge green">Docstrings IA ✓</span>' if report_data.get("has_docstrings") else '<span class="status-badge gray">Sans docstrings IA</span>'
    
    # === HTML FINAL ===
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
        .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
        
        .header {
            background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
            color: white;
            padding: 32px;
            border-radius: 16px 16px 0 0;
            margin-bottom: 0;
        }
        .header h1 { font-size: 24px; margin-bottom: 6px; }
        .header p { opacity: 0.7; font-size: 13px; }
        
        .scores {
            display: flex;
            background: white;
            border-bottom: 1px solid #e2e8f0;
        }
        .score-box {
            flex: 1;
            padding: 24px;
            text-align: center;
            border-right: 1px solid #e2e8f0;
        }
        .score-box:last-child { border-right: none; }
        .score-box.before { border-top: 4px solid """ + before_color + """; }
        .score-box.after { border-top: 4px solid """ + after_color + """; }
        .score-box.imp { border-top: 4px solid """ + imp_color + """; background: """ + imp_bg + """; }
        .score-value { font-size: 36px; font-weight: 700; }
        .score-box.before .score-value { color: """ + before_color + """; }
        .score-box.after .score-value { color: """ + after_color + """; }
        .score-box.imp .score-value { color: """ + imp_color + """; }
        .score-label { font-size: 12px; color: #64748b; margin-top: 4px; }
        
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
            padding: 20px;
            background: white;
            border-bottom: 1px solid #e2e8f0;
        }
        .metric {
            background: #f8fafc;
            padding: 16px;
            border-radius: 10px;
            text-align: center;
        }
        .metric-value { font-size: 24px; font-weight: 700; color: #3b82f6; }
        .metric-label { font-size: 11px; color: #64748b; }
        
        .status-bar {
            display: flex;
            gap: 10px;
            padding: 16px 20px;
            background: white;
            border-bottom: 1px solid #e2e8f0;
        }
        .status-badge {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-badge.green { background: #dcfce7; color: #166534; }
        .status-badge.gray { background: #f1f5f9; color: #64748b; }
        
        .content {
            background: white;
            border-radius: 0 0 16px 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        }
        
        .section { border-bottom: 1px solid #e2e8f0; }
        .section:last-child { border-bottom: none; }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            cursor: pointer;
            background: #f8fafc;
            transition: background 0.2s;
        }
        .section-header:hover { background: #f1f5f9; }
        .section-header h2 { font-size: 15px; font-weight: 600; }
        .toggle { color: #64748b; transition: transform 0.2s; }
        .section.collapsed .toggle { transform: rotate(-90deg); }
        .section.collapsed .section-content { display: none; }
        
        .section-content { padding: 16px 20px; }
        
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
        th { background: #f8fafc; font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; }
        td { font-size: 13px; }
        td.args { font-size: 11px; color: #64748b; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
        
        code {
            font-family: 'SF Mono', Monaco, monospace;
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }
        
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: 600;
            color: white;
        }
        .badge-green { background: #22c55e; }
        .badge-gray { background: #94a3b8; }
        
        .class-card {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            margin-bottom: 12px;
            overflow: hidden;
        }
        .class-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 16px;
            background: #f8fafc;
        }
        .class-header h3 { font-size: 14px; font-weight: 600; flex: 1; }
        .line-info { font-size: 11px; color: #94a3b8; }
        .docstring {
            padding: 12px 16px;
            background: #fffbeb;
            font-size: 12px;
            color: #92400e;
            border-bottom: 1px solid #e2e8f0;
        }
        .attrs {
            padding: 10px 16px;
            font-size: 12px;
            color: #64748b;
            border-bottom: 1px solid #e2e8f0;
        }
        .methods { padding: 12px 16px; }
        .method {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 0;
            border-bottom: 1px solid #f1f5f9;
        }
        .method:last-child { border-bottom: none; }
        .method code { flex: 1; }
        
        .vars-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 8px;
        }
        .var {
            background: #f8fafc;
            padding: 10px 12px;
            border-radius: 6px;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
        }
        .var.const { background: #fef3c7; }
        .var .type { color: #64748b; font-size: 11px; }
        
        .bar-container {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .bar {
            height: 16px;
            border-radius: 4px;
            min-width: 4px;
        }
        .bar-container span { font-size: 11px; color: #64748b; min-width: 45px; }
        
        .issue {
            padding: 8px 12px;
            background: #fef2f2;
            border-left: 3px solid #ef4444;
            margin-bottom: 4px;
            font-size: 11px;
            font-family: monospace;
            color: #991b1b;
            border-radius: 0 6px 6px 0;
        }
        .more { font-size: 12px; color: #64748b; margin-top: 8px; }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #94a3b8;
            font-size: 11px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 """ + report_data["filename"] + """</h1>
            <p>Rapport genere le """ + report_data["date"] + """</p>
        </div>
        
        <div class="scores">
            <div class="score-box before">
                <div class="score-value">""" + str(score_before) + """</div>
                <div class="score-label">Score Avant</div>
            </div>
            <div class="score-box after">
                <div class="score-value">""" + str(score_after) + """</div>
                <div class="score-label">Score Apres</div>
            </div>
            <div class="score-box imp">
                <div class="score-value">""" + imp_text + """</div>
                <div class="score-label">Amelioration</div>
            </div>
        </div>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">""" + str(original.get("lines", 0)) + """</div>
                <div class="metric-label">Lignes</div>
            </div>
            <div class="metric">
                <div class="metric-value">""" + str(original.get("code_lines", 0)) + """</div>
                <div class="metric-label">Code</div>
            </div>
            <div class="metric">
                <div class="metric-value">""" + str(len(functions)) + """</div>
                <div class="metric-label">Fonctions</div>
            </div>
            <div class="metric">
                <div class="metric-value">""" + str(len(classes)) + """</div>
                <div class="metric-label">Classes</div>
            </div>
            <div class="metric">
                <div class="metric-value">""" + str(original.get("avg_complexity", 0)) + """</div>
                <div class="metric-label">Complexite</div>
            </div>
            <div class="metric">
                <div class="metric-value">""" + str(original.get("doc_coverage", 0)) + """%</div>
                <div class="metric-label">Doc</div>
            </div>
        </div>
        
        <div class="status-bar">
            """ + pep8_badge + """
            """ + doc_badge + """
        </div>
        
        <div class="content">
            """ + classes_html + """
            """ + functions_html + """
            """ + imports_html + """
            """ + vars_html + """
            """ + profile_html + """
            """ + issues_html + """
        </div>
        
        <div class="footer">
            Rapport genere par AgentIA Code Standardizer
        </div>
    </div>
    
    <script>
        function toggleSection(header) {
            header.parentElement.classList.toggle('collapsed');
        }
    </script>
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
            padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
            color: white;
            padding: 32px;
            border-radius: 16px 16px 0 0;
        }
        .header h1 { font-size: 24px; margin-bottom: 6px; }
        .header p { opacity: 0.7; }
        .stats {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            background: white;
        }
        .stat {
            padding: 20px;
            text-align: center;
            border-right: 1px solid #e2e8f0;
        }
        .stat:last-child { border-right: none; }
        .stat-value { font-size: 28px; font-weight: 700; color: #3b82f6; }
        .stat-label { font-size: 11px; color: #64748b; margin-top: 4px; }
        .content {
            background: white;
            padding: 20px;
            border-radius: 0 0 16px 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        }
        .content h2 { font-size: 16px; margin-bottom: 16px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
        th { background: #f8fafc; font-size: 11px; text-transform: uppercase; color: #64748b; }
        td { font-size: 13px; }
        code { background: #f1f5f9; padding: 4px 8px; border-radius: 4px; }
        .footer { text-align: center; padding: 20px; color: #94a3b8; font-size: 11px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Rapport Global</h1>
            <p>Job """ + job_id + """ - """ + current_date + """</p>
        </div>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">""" + str(avg_score) + """</div>
                <div class="stat-label">Score moyen</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color:#22c55e">+""" + str(avg_improvement) + """</div>
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
                    <tr><th>Fichier</th><th>Avant</th><th>Apres</th><th>+/-</th><th>Fonctions</th><th>Classes</th><th>Problemes</th></tr>
                </thead>
                <tbody>""" + files_rows + """</tbody>
            </table>
        </div>
        <div class="footer">AgentIA Code Standardizer</div>
    </div>
</body>
</html>"""