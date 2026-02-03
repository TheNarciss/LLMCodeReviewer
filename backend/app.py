"""
API Backend - AgentIA Code Standardizer
Version Clean : Stockage temporaire et auto-nettoyage après téléchargement.
"""

import os
import shutil
import zipfile
import uuid
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from profiler import profile_code
from utils import list_python_files, read_file, write_file, get_relative_path
from analyser import analyze_file, analyze_code_string, calculate_quality_score
from corrector import correct_code
from generator_docstring import add_docstrings_smartly
from generator_rapport import generate_report_data, generate_html_report, generate_global_report
from dependency_graph import analyze_file_dependencies, analyze_project_dependencies, generate_interactive_graph_html
from llm_service import get_backend_info


# Modèle pour l'import GitHub
class GitHubImportRequest(BaseModel):
    url: str
    token: Optional[str] = None
    branch: Optional[str] = "main"

# --- CONFIGURATION DU STOCKAGE TEMPORAIRE ---
# On utilise le dossier temporaire du système d'exploitation pour ne pas polluer le projet
SYSTEM_TEMP_DIR = Path(tempfile.gettempdir())
UPLOAD_DIR = SYSTEM_TEMP_DIR / "agentia_uploads"
OUTPUT_DIR = SYSTEM_TEMP_DIR / "agentia_outputs"

# On s'assure que les dossiers racines existent dans /tmp
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Pour servir le frontend (inchangé)
BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="AgentIA Code Standardizer",
    description="Analyse, corrige et documente automatiquement du code Python",
    version="2.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# --- FONCTION DE NETTOYAGE ---
def cleanup_job_data(job_id: str):
    """
    Supprime définitivement les fichiers d'entrée et de sortie pour un job donné.
    Appelé automatiquement après le téléchargement.
    """
    try:
        # Supprimer le dossier d'upload
        upload_path = UPLOAD_DIR / job_id
        if upload_path.exists():
            shutil.rmtree(upload_path)
            
        # Supprimer le dossier de sortie
        output_path = OUTPUT_DIR / job_id
        if output_path.exists():
            shutil.rmtree(output_path)
            
        # Supprimer le zip temporaire s'il existe
        zip_path = OUTPUT_DIR / f"{job_id}_processed.zip"
        if zip_path.exists():
            os.remove(zip_path)
            
        print(f"🧹 [CLEANUP] Données du job {job_id} supprimées avec succès.")
    except Exception as e:
        print(f"⚠️ [CLEANUP] Erreur lors de la suppression du job {job_id}: {e}")


@app.get("/")
async def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/status")
async def status():
    return {"status": "ok", "llm": get_backend_info()}


@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """Upload des fichiers Python ou un ZIP."""
    job_id = str(uuid.uuid4())[:8]
    job_upload_dir = UPLOAD_DIR / job_id
    
    # Nettoyage préventif
    if job_upload_dir.exists():
        shutil.rmtree(job_upload_dir)
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_files = []
    
    for file in files:
        filename = file.filename
        content = await file.read()
        
        if filename.endswith(".zip"):
            zip_path = job_upload_dir / filename
            with open(zip_path, "wb") as f:
                f.write(content)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(job_upload_dir)
            os.remove(zip_path)
            
            for py_file in list_python_files(str(job_upload_dir)):
                rel_path = get_relative_path(py_file, str(job_upload_dir))
                uploaded_files.append(rel_path)
        
        elif filename.endswith(".py"):
            filepath = job_upload_dir / filename
            with open(filepath, "wb") as f:
                f.write(content)
            uploaded_files.append(filename)
    
    return {"job_id": job_id, "files": uploaded_files, "count": len(uploaded_files)}


@app.post("/api/github")
async def import_from_github(request: GitHubImportRequest):
    """Clone un repository GitHub et prépare les fichiers pour analyse."""
    
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL du repository requise")
    
    url_clean = url.replace("https://", "").replace("http://", "").replace("github.com/", "")
    url_clean = url_clean.rstrip("/").rstrip(".git")
    
    parts = url_clean.split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="URL invalide.")
    
    owner = parts[0]
    repo = parts[1]
    branch = request.branch or "main"
    
    job_id = str(uuid.uuid4())[:8]
    job_upload_dir = UPLOAD_DIR / job_id
    
    if job_upload_dir.exists():
        shutil.rmtree(job_upload_dir)
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if request.token:
            clone_url = f"https://{request.token}@github.com/{owner}/{repo}.git"
        else:
            clone_url = f"https://github.com/{owner}/{repo}.git"
        
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, clone_url, str(job_upload_dir)],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            # Retry without branch
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(job_upload_dir)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Erreur inconnue lors du clone"
                if request.token:
                    error_msg = error_msg.replace(request.token, "***")
                raise HTTPException(status_code=400, detail=f"Erreur Git: {error_msg}")
        
        git_dir = job_upload_dir / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)
        
        python_files = list_python_files(str(job_upload_dir))
        
        if not python_files:
            raise HTTPException(status_code=400, detail="Aucun fichier Python trouvé")
        
        uploaded_files = []
        for py_file in python_files:
            rel_path = get_relative_path(py_file, str(job_upload_dir))
            uploaded_files.append(rel_path)
        
        return {
            "job_id": job_id,
            "files": uploaded_files,
            "count": len(uploaded_files),
            "source": "github",
            "repo": f"{owner}/{repo}",
            "branch": branch
        }
        
    except subprocess.TimeoutExpired:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise HTTPException(status_code=408, detail="Timeout clone")
    except Exception as e:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/api/analyze/{job_id}")
async def analyze_job(job_id: str):
    job_dir = UPLOAD_DIR / job_id
    
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job expiré ou introuvable")
    
    python_files = list_python_files(str(job_dir))
    
    results = []
    total_score = 0
    
    for filepath in python_files:
        analysis = analyze_file(filepath)
        score = calculate_quality_score(analysis)
        total_score += score
        
        results.append({
            "file": get_relative_path(filepath, str(job_dir)),
            "functions": [f["name"] for f in analysis.get("functions", [])],
            "classes": [c["name"] for c in analysis.get("classes", [])],
            "issues": len(analysis.get("style_issues", [])),
            "issues_detail": analysis.get("style_issues", [])[:10],
            "lines": analysis.get("lines", 0),
            "score": score,
            "avg_complexity": analysis.get("avg_complexity", 0),
            "doc_coverage": analysis.get("doc_coverage", 0)
        })
    
    return {
        "job_id": job_id,
        "files": results,
        "total_files": len(results),
        "average_score": total_score // len(results) if results else 0
    }


@app.post("/api/process/{job_id}")
async def process_job(
    job_id: str,
    pep8: bool = True,
    docstrings: bool = True,
    generate_markdown: bool = False,
    profiling: bool = False,
    dependency_graph: bool = False,
    ai_type: str = "ollama",
    ollama_model: str = "llama3.2:3b",
    api_url: str = "",
    api_key: str = "",
    api_model: str = "gpt-4"
):
    import llm_service
    original_config = {
        'LLM_API_URL': llm_service.LLM_API_URL,
        'LLM_API_TOKEN': llm_service.LLM_API_TOKEN,
        'LLM_MODEL': llm_service.LLM_MODEL
    }
    
    if ai_type == "api" and api_url and api_key:
        llm_service.LLM_API_URL = api_url
        llm_service.LLM_API_TOKEN = api_key
        llm_service.LLM_MODEL = api_model
    elif ai_type == "ollama":
        llm_service.LLM_API_URL = ""
        llm_service.LLM_API_TOKEN = ""
        llm_service.LLM_MODEL = ollama_model
    
    try:
        job_upload_dir = UPLOAD_DIR / job_id
        job_output_dir = OUTPUT_DIR / job_id
        
        if not job_upload_dir.exists():
            raise HTTPException(status_code=404, detail="Job introuvable")
        
        if job_output_dir.exists():
            shutil.rmtree(job_output_dir)
        job_output_dir.mkdir(parents=True, exist_ok=True)
        
        python_files = list_python_files(str(job_upload_dir))
        processed = []
        reports_data = []
        
        for filepath in python_files:
            relative = get_relative_path(filepath, str(job_upload_dir))
            output_path = job_output_dir / relative
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"[PROCESS] {relative}")
            
            try:
                original_code = read_file(filepath)
                final_code = original_code
                
                if pep8:
                    final_code = correct_code(final_code)
                
                # Sauvegarde intermédiaire pour l'AST
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(final_code)
                
                has_docstrings = False
                if docstrings:
                    try:
                        doc_success = add_docstrings_smartly(str(output_path))
                        if doc_success:
                            has_docstrings = True
                            with open(output_path, 'r', encoding='utf-8') as f:
                                final_code = f.read()
                    except Exception as e:
                        print(f"Erreur docstrings: {e}")

                if generate_markdown:
                    try:
                        from generator_documentation import generate_markdown_doc
                        md_content = generate_markdown_doc(final_code, relative)
                        md_path = output_path.parent / (output_path.stem + "_DOC.md")
                        with open(md_path, 'w', encoding='utf-8') as f:
                            f.write(md_content)
                    except Exception as e:
                        print(f"Erreur doc MD: {e}")
                
                profile_data = None
                if profiling:
                    try:
                        profile_data = profile_code(final_code, str(output_path))
                    except Exception as e:
                        print(f"Erreur profiling: {e}")
                
                report_data = generate_report_data(
                    filepath, original_code, final_code, 
                    has_docstrings=has_docstrings,
                    profile_data=profile_data
                )
                reports_data.append(report_data)
                
                report_html = generate_html_report(report_data)
                report_path = output_path.parent / (output_path.stem + "_rapport.html")
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report_html)
                
                has_graph = False
                if dependency_graph:
                    try:
                        graph_data = analyze_file_dependencies(str(output_path))
                        graph_html = generate_interactive_graph_html(graph_data, f"Dependances: {relative}")
                        graph_path = output_path.parent / (output_path.stem + "_graph.html")
                        with open(graph_path, 'w', encoding='utf-8') as f:
                            f.write(graph_html)
                        has_graph = True
                    except Exception:
                        pass
                
                processed.append({
                    "file": relative,
                    "status": "ok",
                    "score_before": report_data["score_before"],
                    "score_after": report_data["score_after"],
                    "has_docstrings": has_docstrings,
                    "has_profiling": profile_data is not None,
                    "has_graph": has_graph
                })
                
            except Exception as e:
                print(f"Erreur fichier {relative}: {e}")
                processed.append({"file": relative, "status": "error", "error": str(e)})
    
        global_report = generate_global_report(reports_data, job_id)
        with open(job_output_dir / "_rapport_global.html", 'w', encoding='utf-8') as f:
            f.write(global_report)
        
        if dependency_graph and len(python_files) > 1:
            try:
                project_graph = analyze_project_dependencies(str(job_output_dir))
                project_graph_html = generate_interactive_graph_html(project_graph, f"Projet - {job_id}")
                with open(job_output_dir / "_project_graph.html", 'w', encoding='utf-8') as f:
                    f.write(project_graph_html)
            except Exception:
                pass
        
        return {"job_id": job_id, "processed": processed, "count": len(processed)}
        
    finally:
        llm_service.LLM_API_URL = original_config['LLM_API_URL']
        llm_service.LLM_API_TOKEN = original_config['LLM_API_TOKEN']
        llm_service.LLM_MODEL = original_config['LLM_MODEL']


@app.get("/api/preview/{job_id}/{filename:path}")
async def preview_file(job_id: str, filename: str):
    original_path = UPLOAD_DIR / job_id / filename
    corrected_path = OUTPUT_DIR / job_id / filename
    
    result = {"filename": filename, "original": None, "corrected": None, "score_before": None, "score_after": None}
    
    if original_path.exists():
        result["original"] = read_file(str(original_path))
        analysis = analyze_file(str(original_path))
        result["score_before"] = calculate_quality_score(analysis)
    
    if corrected_path.exists():
        result["corrected"] = read_file(str(corrected_path))
        analysis = analyze_code_string(result["corrected"])
        result["score_after"] = calculate_quality_score(analysis)
    
    if not result["original"] and not result["corrected"]:
        raise HTTPException(status_code=404, detail="Fichier non trouvé (peut-être supprimé ?)")
    
    return result


@app.get("/api/report/{job_id}/{filename:path}")
async def get_file_report(job_id: str, filename: str):
    report_filename = filename.rsplit('.', 1)[0] + '_rapport.html'
    report_path = OUTPUT_DIR / job_id / report_filename
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    
    return HTMLResponse(content=read_file(str(report_path)))


@app.get("/api/report/{job_id}")
async def get_global_report(job_id: str):
    report_path = OUTPUT_DIR / job_id / "_rapport_global.html"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Rapport global introuvable")
    return HTMLResponse(content=read_file(str(report_path)))


@app.get("/api/graph/{job_id}/{filename:path}")
async def get_file_graph(job_id: str, filename: str):
    graph_filename = filename.rsplit('.', 1)[0] + '_graph.html'
    graph_path = OUTPUT_DIR / job_id / graph_filename
    if not graph_path.exists():
        raise HTTPException(status_code=404, detail="Graphe introuvable")
    return HTMLResponse(content=read_file(str(graph_path)))


@app.get("/api/graph/{job_id}")
async def get_project_graph(job_id: str):
    graph_path = OUTPUT_DIR / job_id / "_project_graph.html"
    if not graph_path.exists():
        raise HTTPException(status_code=404, detail="Graphe projet introuvable")
    return HTMLResponse(content=read_file(str(graph_path)))


@app.get("/api/doc/{job_id}/{filename:path}")
async def get_file_doc(job_id: str, filename: str):
    """Retourne la documentation MD convertie en HTML."""
    doc_filename = filename.rsplit('.', 1)[0] + '_DOC.md'
    doc_path = OUTPUT_DIR / job_id / doc_filename
    
    if not doc_path.exists():
        # Pas de doc générée - afficher un message
        html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body { font-family: system-ui; padding: 40px; text-align: center; color: #64748b; }
h2 { color: #1e293b; }
</style></head><body>
<h2>Documentation non disponible</h2>
<p>Activez l'option "Documentation Markdown" lors du traitement pour générer la documentation.</p>
</body></html>"""
        return HTMLResponse(content=html)
    
    # Lire le contenu MD
    md_content = read_file(str(doc_path))
    
    # Conversion simple MD -> HTML (basique mais suffisant)
    html_content = convert_md_to_html(md_content, filename)
    
    return HTMLResponse(content=html_content)


def convert_md_to_html(md_content: str, filename: str) -> str:
    """Convertit le Markdown en HTML avec style."""
    import re
    
    # Échapper les caractères HTML
    def escape_html(text):
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    lines = md_content.split('\n')
    html_lines = []
    in_code_block = False
    code_lang = ""
    code_content = []
    
    for line in lines:
        # Code blocks
        if line.startswith('```'):
            if in_code_block:
                # Fin du bloc de code
                html_lines.append(f'<pre><code class="language-{code_lang}">{escape_html(chr(10).join(code_content))}</code></pre>')
                code_content = []
                in_code_block = False
            else:
                # Début du bloc de code
                code_lang = line[3:].strip() or "text"
                in_code_block = True
            continue
        
        if in_code_block:
            code_content.append(line)
            continue
        
        # Headers
        if line.startswith('### '):
            html_lines.append(f'<h3>{escape_html(line[4:])}</h3>')
        elif line.startswith('## '):
            html_lines.append(f'<h2>{escape_html(line[3:])}</h2>')
        elif line.startswith('# '):
            html_lines.append(f'<h1>{escape_html(line[2:])}</h1>')
        # Lists
        elif line.strip().startswith('- '):
            html_lines.append(f'<li>{escape_html(line.strip()[2:])}</li>')
        elif line.strip().startswith('* '):
            html_lines.append(f'<li>{escape_html(line.strip()[2:])}</li>')
        # Bold et code inline
        elif line.strip():
            processed = escape_html(line)
            # **bold**
            processed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', processed)
            # `code`
            processed = re.sub(r'`([^`]+)`', r'<code>\1</code>', processed)
            html_lines.append(f'<p>{processed}</p>')
        else:
            html_lines.append('<br>')
    
    body = '\n'.join(html_lines)
    
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Documentation - {filename}</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', system-ui, sans-serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 30px; 
            background: #f8fafc; 
            color: #1e293b;
            line-height: 1.6;
        }}
        h1 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
        h2 {{ color: #1e293b; margin-top: 30px; }}
        h3 {{ color: #475569; }}
        code {{ 
            background: #f1f5f9; 
            padding: 2px 6px; 
            border-radius: 4px; 
            font-family: 'Consolas', monospace;
            font-size: 14px;
        }}
        pre {{ 
            background: #1e293b; 
            color: #e2e8f0; 
            padding: 16px; 
            border-radius: 8px; 
            overflow-x: auto;
        }}
        pre code {{ 
            background: none; 
            padding: 0; 
            color: inherit;
        }}
        li {{ margin: 8px 0; }}
        strong {{ color: #0f172a; }}
        p {{ margin: 12px 0; }}
    </style>
</head>
<body>
{body}
</body>
</html>"""


@app.get("/api/download/{job_id}")
async def download_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Télécharge les fichiers et SUPPRIME TOUT (nettoyage) après l'envoi.
    """
    job_output_dir = OUTPUT_DIR / job_id
    
    if not job_output_dir.exists():
        raise HTTPException(status_code=404, detail="Fichiers expirés ou introuvables")
    
    files_to_zip = [f for f in job_output_dir.rglob("*") if f.is_file()]
    
    if not files_to_zip:
        raise HTTPException(status_code=404, detail="Dossier vide")
    
    # Création du ZIP dans le dossier temporaire général (pas dans le job_id qui va être suppr)
    zip_path = OUTPUT_DIR / f"{job_id}_processed.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filepath in files_to_zip:
            zipf.write(filepath, filepath.relative_to(job_output_dir))
    
    # AJOUT DE LA TÂCHE DE FOND : Nettoyage après envoi
    background_tasks.add_task(cleanup_job_data, job_id)
    
    return FileResponse(
        path=str(zip_path), 
        filename=f"agentia_{job_id}.zip", 
        media_type="application/zip"
    )


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    """Suppression manuelle."""
    cleanup_job_data(job_id)
    return {"status": "deleted", "job_id": job_id}


@app.get("/api/download/{job_id}/{filename:path}")
async def download_single_file(job_id: str, filename: str):
    file_path = OUTPUT_DIR / job_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(path=str(file_path), filename=filename, media_type="application/octet-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)