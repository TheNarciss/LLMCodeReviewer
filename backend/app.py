"""
API Backend - AgentIA Code Standardizer
Version avec rapports consolides
"""

import os
import shutil
import zipfile
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from utils import list_python_files, read_file, write_file, get_relative_path
from analyser import analyze_file, analyze_code_string, calculate_quality_score
from corrector import correct_code
from generator_docstring import generate_docstrings
from generator_rapport import generate_report_data, generate_html_report, generate_global_report
from dependency_graph import analyze_file_dependencies, analyze_project_dependencies, generate_interactive_graph_html
from llm_service import get_backend_info

# Configuration
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
FRONTEND_DIR = BASE_DIR / "frontend"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="AgentIA Code Standardizer",
    description="Analyse, corrige et documente automatiquement du code Python",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


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


@app.get("/api/analyze/{job_id}")
async def analyze_job(job_id: str):
    """Analyse tous les fichiers d'un job."""
    job_dir = UPLOAD_DIR / job_id
    
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job non trouve")
    
    python_files = list_python_files(str(job_dir))
    
    if not python_files:
        raise HTTPException(status_code=404, detail="Aucun fichier Python trouve")
    
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
    profiling: bool = False,
    dependency_graph: bool = False
):
    """
    Traite les fichiers et genere:
    - fichier.py (code corrige)
    - fichier_rapport.html (analyse + doc + profiling)
    - fichier_graph.html (si dependency_graph=True)
    """
    job_upload_dir = UPLOAD_DIR / job_id
    job_output_dir = OUTPUT_DIR / job_id
    
    print(f"[PROCESS] Job {job_id} - PEP8:{pep8} Docstrings:{docstrings} Profiling:{profiling} Graph:{dependency_graph}")
    
    if not job_upload_dir.exists():
        raise HTTPException(status_code=404, detail="Job non trouve")
    
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
            has_docstrings = False
            
            # Correction PEP8
            if pep8:
                final_code = correct_code(final_code)
            
            # Generation docstrings
            if docstrings:
                try:
                    final_code = generate_docstrings(final_code)
                    has_docstrings = True
                except Exception as e:
                    print(f"[PROCESS] Erreur docstrings: {e}")
            
            # Sauvegarder le code corrige
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_code)
            
            # Profiling (optionnel)
            profile_data = None
            if profiling:
                try:
                    from profiler import profile_code
                    profile_data = profile_code(final_code, relative)
                except Exception as e:
                    print(f"[PROCESS] Erreur profiling: {e}")
            
            # Generer les donnees du rapport (inclut profiling si disponible)
            report_data = generate_report_data(
                filepath, original_code, final_code, 
                has_docstrings=has_docstrings,
                profile_data=profile_data
            )
            reports_data.append(report_data)
            
            # Generer le rapport HTML unifie
            report_html = generate_html_report(report_data)
            report_path = output_path.parent / (output_path.stem + "_rapport.html")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_html)
            
            # Graphe de dependances (optionnel)
            has_graph = False
            if dependency_graph:
                try:
                    graph_data = analyze_file_dependencies(str(output_path))
                    graph_html = generate_interactive_graph_html(graph_data, f"Dependances: {relative}")
                    graph_path = output_path.parent / (output_path.stem + "_graph.html")
                    with open(graph_path, 'w', encoding='utf-8') as f:
                        f.write(graph_html)
                    has_graph = True
                except Exception as e:
                    print(f"[PROCESS] Erreur graphe: {e}")
            
            print(f"[PROCESS] Score: {report_data['score_before']} -> {report_data['score_after']}")
            
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
            print(f"[PROCESS] Erreur: {e}")
            import traceback
            traceback.print_exc()
            processed.append({
                "file": relative,
                "status": "error",
                "error": str(e)
            })
    
    # Rapport global
    global_report = generate_global_report(reports_data, job_id)
    with open(job_output_dir / "_rapport_global.html", 'w', encoding='utf-8') as f:
        f.write(global_report)
    
    # Graphe projet (si plusieurs fichiers et option activee)
    if dependency_graph and len(python_files) > 1:
        try:
            project_graph = analyze_project_dependencies(str(job_output_dir))
            project_graph_html = generate_interactive_graph_html(project_graph, f"Projet - {job_id}")
            with open(job_output_dir / "_project_graph.html", 'w', encoding='utf-8') as f:
                f.write(project_graph_html)
        except Exception as e:
            print(f"[PROCESS] Erreur graphe projet: {e}")
    
    return {"job_id": job_id, "processed": processed, "count": len(processed)}


@app.get("/api/preview/{job_id}/{filename:path}")
async def preview_file(job_id: str, filename: str):
    """Previsualise un fichier."""
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
        raise HTTPException(status_code=404, detail="Fichier non trouve")
    
    return result


@app.get("/api/report/{job_id}/{filename:path}")
async def get_file_report(job_id: str, filename: str):
    """Recupere le rapport HTML d'un fichier."""
    report_filename = filename.rsplit('.', 1)[0] + '_rapport.html'
    report_path = OUTPUT_DIR / job_id / report_filename
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Rapport non trouve")
    
    return HTMLResponse(content=read_file(str(report_path)))


@app.get("/api/report/{job_id}")
async def get_global_report(job_id: str):
    """Recupere le rapport global."""
    report_path = OUTPUT_DIR / job_id / "_rapport_global.html"
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Rapport global non trouve")
    
    return HTMLResponse(content=read_file(str(report_path)))


@app.get("/api/graph/{job_id}/{filename:path}")
async def get_file_graph(job_id: str, filename: str):
    """Recupere le graphe d'un fichier."""
    graph_filename = filename.rsplit('.', 1)[0] + '_graph.html'
    graph_path = OUTPUT_DIR / job_id / graph_filename
    
    if not graph_path.exists():
        raise HTTPException(status_code=404, detail="Graphe non trouve")
    
    return HTMLResponse(content=read_file(str(graph_path)))


@app.get("/api/graph/{job_id}")
async def get_project_graph(job_id: str):
    """Recupere le graphe du projet."""
    graph_path = OUTPUT_DIR / job_id / "_project_graph.html"
    
    if not graph_path.exists():
        raise HTTPException(status_code=404, detail="Graphe projet non trouve")
    
    return HTMLResponse(content=read_file(str(graph_path)))


@app.get("/api/download/{job_id}")
async def download_job(job_id: str):
    """Telecharge les fichiers traites en ZIP."""
    job_output_dir = OUTPUT_DIR / job_id
    
    if not job_output_dir.exists():
        raise HTTPException(status_code=404, detail="Aucun fichier traite")
    
    files_to_zip = [f for f in job_output_dir.rglob("*") if f.is_file()]
    
    if not files_to_zip:
        raise HTTPException(status_code=404, detail="Aucun fichier")
    
    zip_path = OUTPUT_DIR / f"{job_id}_processed.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filepath in files_to_zip:
            zipf.write(filepath, filepath.relative_to(job_output_dir))
    
    return FileResponse(path=str(zip_path), filename=f"agentia_{job_id}.zip", media_type="application/zip")


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    """Supprime les fichiers d'un job."""
    for base_dir in [UPLOAD_DIR, OUTPUT_DIR]:
        job_dir = base_dir / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir)
    
    zip_path = OUTPUT_DIR / f"{job_id}_processed.zip"
    if zip_path.exists():
        os.remove(zip_path)
    
    return {"status": "deleted", "job_id": job_id}

@app.get("/api/download/{job_id}/{filename:path}")
async def download_single_file(job_id: str, filename: str):
    """Telecharge un fichier individuel traite."""
    file_path = OUTPUT_DIR / job_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier non trouve")
        
    return FileResponse(
        path=str(file_path), 
        filename=filename, 
        media_type="application/octet-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
