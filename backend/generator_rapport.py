"""
Generateur de rapports HTML unifies - Version Complete (Architecture + Debug + Fonctions).
"""

from datetime import datetime
from pathlib import Path
from analyser import analyze_file, analyze_code_string, calculate_quality_score


def generate_report_data(filepath: str, original_code: str, corrected_code: str, 
                         has_docstrings: bool = False, profile_data: dict = None) -> dict:
    """Genere les donnees completes du rapport."""
    analysis_original = analyze_file(filepath)
    analysis_corrected = analyze_code_string(corrected_code)
    
    score_before = calculate_quality_score(analysis_original)
    score_after = calculate_quality_score(analysis_corrected)
    
    functions = analysis_original.get("functions", [])
    classes = analysis_original.get("classes", [])
    
    all_methods = functions + [m for c in classes for m in c.get("methods", [])]
    total_complexity = sum(f.get("complexity", 1) for f in all_methods)
    count_methods = len(all_methods) if all_methods else 1
    avg_complexity = round(total_complexity / count_methods, 2)

    return {
        "filename": Path(filepath).name,
        "filepath": filepath,
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "score_before": score_before,
        "score_after": score_after,
        "improvement": score_after - score_before,
        "avg_complexity": avg_complexity,
        "complexity_status": "Complexe" if avg_complexity > 10 else "Modéré" if avg_complexity > 5 else "Simple",
        "original": analysis_original,
        "has_changes": original_code != corrected_code,
        "has_docstrings": has_docstrings,
        "profile": profile_data,
        "style_issues": analysis_original.get("style_issues", []),
        "functions_list": [f["name"] for f in functions],
        "classes_list": [c["name"] for c in classes],
    }

def get_score_color(score):
    if score >= 80: return "#22c55e"
    elif score >= 60: return "#f59e0b"
    return "#ef4444"

def get_complexity_color(complexity):
    if complexity <= 5: return "#22c55e"
    elif complexity <= 10: return "#f59e0b"
    return "#ef4444"

def clean_function_name(name):
    if name == "<module>": return "(Module Principal)"
    if name == "<listcomp>": return "(List Comp.)"
    return name

def format_signature(func: dict) -> str:
    """Formate la signature d'une fonction avec types."""
    args_parts = []
    for arg in func.get("args", []):
        if isinstance(arg, dict):
            if arg.get("type"):
                args_parts.append(f'{arg["name"]}: <span class="type">{arg["type"]}</span>')
            else:
                args_parts.append(arg["name"])
        else:
            args_parts.append(str(arg))
    
    args_str = ", ".join(args_parts)
    ret = func.get("return_type")
    ret_str = f' → <span class="type">{ret}</span>' if ret else ""
    
    return f'({args_str}){ret_str}'

def generate_html_report(report_data: dict) -> str:
    """Genere le rapport HTML complet avec documentation détaillée."""
    original = report_data.get("original", {})
    profile = report_data.get("profile")
    score_after = report_data.get("score_after", 0)
    doc_coverage = original.get("doc_coverage", 0)
    
    # === DASHBOARD ===
    dashboard_html = f"""
    <div class="dashboard-grid">
        <div class="dash-card">
            <div class="dash-label">Score</div>
            <div class="dash-value" style="color:{get_score_color(score_after)}">{score_after}/100</div>
        </div>
        <div class="dash-card">
            <div class="dash-label">Complexité</div>
            <div class="dash-value">{report_data.get('avg_complexity', 0)}</div>
        </div>
        <div class="dash-card">
            <div class="dash-label">Lignes</div>
            <div class="dash-value">{original.get('lines', 0)}</div>
        </div>
        <div class="dash-card">
            <div class="dash-label">Doc Coverage</div>
            <div class="dash-value" style="color:{get_score_color(doc_coverage)}">{doc_coverage}%</div>
        </div>
    </div>
    """

    # === SECTION CLASSES (Architecture) ===
    classes_html = ""
    classes_list = original.get("classes", [])
    if classes_list:
        classes_content = ""
        for cls in classes_list:
            # Héritage
            bases_str = ""
            if cls.get("bases"):
                bases_str = f'<span class="inheritance">hérite de {", ".join(cls["bases"])}</span>'
            
            # Méthodes détaillées
            methods_html = ""
            for m in cls.get("methods", []):
                c_bg = get_complexity_color(m.get("complexity", 1))
                signature = format_signature(m)
                doc_icon = "✓" if m.get("has_docstring") else "✗"
                doc_class = "doc-yes" if m.get("has_docstring") else "doc-no"
                
                # Docstring preview
                docstring_html = ""
                if m.get("docstring"):
                    docstring_html = f'<div class="method-docstring">{m["docstring"]}</div>'
                
                methods_html += f"""
                <div class="method-block">
                    <div class="method-header">
                        <code class="method-name">{m['name']}</code>
                        <span class="method-signature">{signature}</span>
                        <span class="complexity-badge" style="background:{c_bg}">{m.get('complexity', 1)}</span>
                        <span class="{doc_class}">{doc_icon}</span>
                    </div>
                    {docstring_html}
                </div>"""
            
            # Attributs
            attrs_html = ""
            if cls.get("attributes"):
                attrs_list = []
                for attr in cls["attributes"]:
                    if isinstance(attr, dict):
                        attrs_list.append(f'{attr["name"]}: {attr.get("type", "Any")}')
                    else:
                        attrs_list.append(str(attr))
                attrs_html = f'<div class="class-attrs">Attributs: {", ".join(attrs_list)}</div>'
            
            classes_content += f"""
            <div class="class-block">
                <div class="class-header">
                    <h3>class {cls['name']}</h3>
                    {bases_str}
                </div>
                {f'<div class="docstring">{cls.get("docstring", "")}</div>' if cls.get("docstring") else '<div class="docstring no-doc">Pas de documentation</div>'}
                {attrs_html}
                <div class="methods-list">{methods_html}</div>
            </div>
            """
        classes_html = f"""
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)"><h2>Classes ({len(classes_list)})</h2><span class="toggle">▼</span></div>
            <div class="section-content">{classes_content}</div>
        </div>"""

    # === SECTION FONCTIONS GLOBALES ===
    functions_html = ""
    functions_list = original.get("functions", [])
    if functions_list:
        funcs_content = ""
        for f in functions_list:
            c_bg = get_complexity_color(f.get("complexity", 1))
            signature = format_signature(f)
            doc_icon = "✓" if f.get("has_docstring") else "✗"
            doc_class = "doc-yes" if f.get("has_docstring") else "doc-no"
            
            # Docstring
            docstring_html = ""
            if f.get("docstring"):
                docstring_html = f'<div class="func-docstring">{f["docstring"]}</div>'
            
            # Appels
            calls_html = ""
            if f.get("calls"):
                calls_html = f'<div class="func-calls">Appelle: {", ".join(f["calls"][:5])}</div>'
            
            async_badge = '<span class="async-badge">async</span>' if f.get("is_async") else ""
            
            funcs_content += f"""
            <div class="func-block">
                <div class="func-header">
                    {async_badge}
                    <code class="func-name">{f['name']}</code>
                    <span class="func-signature">{signature}</span>
                    <div class="func-badges">
                        <span class="complexity-badge" style="background:{c_bg}">{f.get('complexity', 1)}</span>
                        <span class="{doc_class}">{doc_icon}</span>
                        <span class="lines-badge">{f.get('lines', 0)} lignes</span>
                    </div>
                </div>
                {docstring_html}
                {calls_html}
            </div>
            """
        functions_html = f"""
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)"><h2>Fonctions ({len(functions_list)})</h2><span class="toggle">▼</span></div>
            <div class="section-content">{funcs_content}</div>
        </div>"""

    # === SECTION IMPORTS ===
    imports_html = ""
    imports_list = original.get("imports", [])
    if imports_list:
        tags = "".join([f'<span class="import-tag">{i["module"]}</span>' for i in imports_list])
        imports_html = f"""
        <div class="section collapsed">
            <div class="section-header" onclick="toggleSection(this)"><h2>Imports ({len(imports_list)})</h2><span class="toggle">▶</span></div>
            <div class="section-content"><div class="imports-cloud">{tags}</div></div>
        </div>"""

    # === SECTION STYLE ISSUES ===
    issues_html = ""
    issues_list = report_data.get("style_issues", [])
    if issues_list:
        items = "".join([f'<div class="issue-item">⚠️ {i}</div>' for i in issues_list[:10]])
        if len(issues_list) > 10: items += f'<div style="font-size:11px;color:#64748b;margin-top:5px">... et {len(issues_list)-10} autres.</div>'
        issues_html = f"""
        <div class="section collapsed">
            <div class="section-header" onclick="toggleSection(this)"><h2>⚠️ Problèmes PEP8 ({len(issues_list)})</h2><span class="toggle">▶</span></div>
            <div class="section-content">{items}</div>
        </div>"""

    # === SECTION PROFILING & LOGS ===
    profile_html = ""
    logs_html = ""
    
    if profile:
        # Logs
        logs_content = ""
        if profile.get("error"): logs_content += f'<div class="log-box error"><strong>ERREUR :</strong><pre>{profile["error"]}</pre></div>'
        if profile.get("stderr"): logs_content += f'<div class="log-box stderr"><strong>STDERR :</strong><pre>{profile["stderr"]}</pre></div>'
        if profile.get("stdout"): logs_content += f'<div class="log-box stdout"><strong>CONSOLE :</strong><pre>{profile["stdout"]}</pre></div>'
            
        if logs_content:
            logs_html = f"""
            <div class="section">
                <div class="section-header" onclick="toggleSection(this)"><h2>📜 Logs d'exécution</h2><span class="toggle">▼</span></div>
                <div class="section-content">{logs_content}</div>
            </div>"""

        # Performance Table
        funcs = profile.get("functions", [])
        if funcs:
            rows = ""
            total_time = profile.get("total_time", 0.001)
            for pf in funcs[:15]:
                clean_name = clean_function_name(pf["name"])
                if "importlib" in pf.get("filename", ""): continue
                pct = (pf["cumtime"] / total_time * 100) if total_time > 0 else 0
                width = min(100, pct * 2)
                rows += f"""
                <tr>
                    <td><code>{clean_name}</code></td>
                    <td>{pf['ncalls']}</td>
                    <td>{round(pf['cumtime']*1000, 2)} ms</td>
                    <td style="width:100px"><div style="background:#e2e8f0;height:6px;border-radius:3px"><div style="width:{width}%;background:#3b82f6;height:100%"></div></div></td>
                </tr>"""
            
            mem_peak = profile.get("memory_peak_mb", 0)
            profile_html = f"""
            <div class="section">
                <div class="section-header" onclick="toggleSection(this)"><h2>⏱️ Profiling (RAM Pic: {mem_peak} Mo)</h2><span class="toggle">▼</span></div>
                <div class="section-content">
                    <table class="simple-table">
                        <thead><tr><th>Fonction</th><th>Appels</th><th>Temps</th><th>Charge</th></tr></thead>
                        <tbody>{rows}</tbody>
                    </table>
                </div>
            </div>"""

    # === HTML ASSEMBLY ===
    style = """
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f8fafc; color: #1e293b; padding: 20px; margin: 0; }
        .container { max-width: 960px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); overflow: hidden; }
        .header { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; padding: 28px; }
        .header h1 { margin: 0 0 8px 0; font-size: 22px; }
        .header p { margin: 0; opacity: 0.7; font-size: 13px; }
        
        .dashboard-grid { display: grid; grid-template-columns: repeat(4, 1fr); border-bottom: 1px solid #e2e8f0; }
        .dash-card { padding: 20px; text-align: center; border-right: 1px solid #e2e8f0; }
        .dash-card:last-child { border-right: none; }
        .dash-value { font-size: 26px; font-weight: 700; margin-top: 6px; }
        .dash-label { font-size: 10px; text-transform: uppercase; color: #64748b; letter-spacing: 0.5px; }
        
        .section { border-bottom: 1px solid #e2e8f0; }
        .section-header { padding: 16px 24px; background: #f8fafc; cursor: pointer; display: flex; justify-content: space-between; align-items: center; user-select: none; transition: background 0.15s; }
        .section-header:hover { background: #f1f5f9; }
        .section-header h2 { margin: 0; font-size: 13px; text-transform: uppercase; color: #475569; font-weight: 600; letter-spacing: 0.5px; }
        .section-content { padding: 20px 24px; }
        .section.collapsed .section-content { display: none; }
        .toggle { color: #94a3b8; font-size: 12px; }
        
        /* Classes */
        .class-block { border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px; margin-bottom: 14px; background: #fafafa; }
        .class-header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
        .class-header h3 { margin: 0; font-size: 16px; color: #0f172a; font-family: 'Consolas', monospace; }
        .inheritance { font-size: 12px; color: #6366f1; background: #eef2ff; padding: 3px 8px; border-radius: 4px; }
        .class-attrs { font-size: 12px; color: #64748b; margin: 8px 0; padding: 8px; background: #f1f5f9; border-radius: 6px; }
        
        .docstring { background: #fffbeb; padding: 12px; font-size: 13px; color: #92400e; margin: 10px 0; border-radius: 6px; border-left: 3px solid #f59e0b; line-height: 1.5; }
        .docstring.no-doc { background: #fef2f2; color: #dc2626; border-left-color: #ef4444; font-style: italic; }
        
        /* Methods */
        .methods-list { margin-top: 12px; }
        .method-block { padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }
        .method-block:last-child { border-bottom: none; }
        .method-header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .method-name { font-size: 14px; font-weight: 600; color: #0f172a; background: #e0f2fe; padding: 2px 8px; border-radius: 4px; }
        .method-signature { font-size: 12px; color: #64748b; font-family: 'Consolas', monospace; }
        .method-docstring { font-size: 12px; color: #64748b; margin-top: 6px; padding-left: 12px; border-left: 2px solid #e2e8f0; }
        
        /* Functions */
        .func-block { padding: 14px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 10px; background: white; }
        .func-header { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .func-name { font-size: 15px; font-weight: 600; color: #0f172a; background: #dcfce7; padding: 3px 10px; border-radius: 4px; }
        .func-signature { font-size: 12px; color: #64748b; font-family: 'Consolas', monospace; flex: 1; }
        .func-badges { display: flex; gap: 6px; align-items: center; }
        .func-docstring { font-size: 12px; color: #475569; margin-top: 10px; padding: 10px; background: #f8fafc; border-radius: 6px; line-height: 1.5; }
        .func-calls { font-size: 11px; color: #64748b; margin-top: 8px; }
        .func-calls::before { content: "→ "; color: #94a3b8; }
        
        /* Badges */
        .complexity-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 22px; height: 22px; border-radius: 50%; color: white; font-weight: 600; font-size: 11px; }
        .doc-yes { color: #22c55e; font-weight: bold; }
        .doc-no { color: #ef4444; font-weight: bold; }
        .lines-badge { font-size: 10px; color: #64748b; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; }
        .async-badge { font-size: 10px; color: #8b5cf6; background: #f3e8ff; padding: 2px 6px; border-radius: 4px; font-weight: 500; }
        .type { color: #0891b2; font-weight: 500; }
        
        /* Tables */
        .simple-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .simple-table th { text-align: left; padding: 10px; color: #64748b; border-bottom: 2px solid #e2e8f0; font-weight: 500; }
        .simple-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; }
        .simple-table tr:hover { background: #f8fafc; }
        
        /* Logs */
        .log-box { background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 8px; font-family: 'Consolas', monospace; font-size: 12px; margin-bottom: 12px; overflow-x: auto; }
        .log-box pre { margin: 8px 0 0 0; white-space: pre-wrap; word-break: break-word; }
        .log-box.error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
        
        /* Imports */
        .imports-cloud { display: flex; flex-wrap: wrap; gap: 8px; }
        .import-tag { background: #f1f5f9; padding: 5px 10px; border-radius: 6px; font-size: 12px; border: 1px solid #e2e8f0; font-family: 'Consolas', monospace; }
        
        /* Issues */
        .issue-item { padding: 8px 12px; background: #fef2f2; color: #b91c1c; font-size: 12px; margin-bottom: 6px; border-radius: 6px; font-family: 'Consolas', monospace; border-left: 3px solid #ef4444; }
        
        code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; color: #0f172a; font-family: 'Consolas', monospace; font-size: 13px; }
        
        @media (max-width: 600px) {
            .dashboard-grid { grid-template-columns: repeat(2, 1fr); }
            .func-header, .method-header { flex-direction: column; align-items: flex-start; }
        }
    </style>
    """

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Rapport {report_data['filename']}</title>{style}</head>
<body>
    <div class="container">
        <div class="header"><h1>📄 Analyse : {report_data['filename']}</h1><p>{report_data['date']}</p></div>
        {dashboard_html}
        {logs_html}
        {classes_html}
        {functions_html}
        {profile_html}
        {imports_html}
        {issues_html}
    </div>
    <script>
        function toggleSection(header) {{
            header.parentElement.classList.toggle('collapsed');
            header.querySelector('.toggle').textContent = header.parentElement.classList.contains('collapsed') ? '▶' : '▼';
        }}
    </script>
</body>
</html>"""


def generate_global_report(files_data: list, job_id: str) -> str:
    """Génère le rapport global."""
    files_rows = ""
    for f in files_data:
        files_rows += f"""
        <tr>
            <td><strong>{f.get("filename", "")}</strong></td>
            <td>{f.get("score_after")}/100</td>
            <td>{len(f.get("classes_list", []))}</td>
            <td>{len(f.get("functions_list", []))}</td>
            <td><a href="{f.get('filename', '').replace('.py', '_rapport.html')}" style="color:#3b82f6">Voir</a></td>
        </tr>"""
        
    return f"""<!DOCTYPE html>
<html lang="fr"><head><style>
body{{font-family:system-ui;padding:20px;background:#f1f5f9}} .container{{max-width:800px;margin:0 auto;background:white;padding:30px;border-radius:12px}} table{{width:100%;border-collapse:collapse;margin-top:20px}} th{{text-align:left;padding:10px;background:#f8fafc}} td{{padding:10px;border-bottom:1px solid #f1f5f9}}
</style></head><body><div class="container"><h1>📊 Rapport Global {job_id}</h1><table><thead><tr><th>Fichier</th><th>Score</th><th>Classes</th><th>Fonctions</th><th>Lien</th></tr></thead><tbody>{files_rows}</tbody></table></div></body></html>"""