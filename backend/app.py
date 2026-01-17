"""
API Backend - AgentIA Code Standardizer
"""

import os
import shutil
import zipfile
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from utils import list_python_files, read_file, write_file, get_relative_path
from analyser import analyze_file, calculate_quality_score
from corrector import correct_code
from generator_docstring import generate_docstrings
from generator_rapport import generate_report_data, generate_html_report, generate_global_report
from llm_service import get_backend_info

# Configuration
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
FRONTEND_DIR = BASE_DIR / "frontend"

# Créer les dossiers
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# App
app = FastAPI(
    title="AgentIA Code Standardizer",
    description="Analyse, corrige et documente automatiquement du code Python",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir le frontend
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def root():
    """Sert la page d'accueil."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/status")
async def status():
    """Retourne le statut de l'API et le backend LLM utilisé."""
    return {
        "status": "ok",
        "llm": get_backend_info()
    }


@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """Upload des fichiers Python ou un ZIP."""
    job_id = str(uuid.uuid4())[:8]
    job_upload_dir = UPLOAD_DIR / job_id
    
    if job_upload_dir.exists():
        shutil.rmtree(job_upload_dir)
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_files = []
    
    print(f"[UPLOAD] Job {job_id}: {len(files)} fichier(s)")
    
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
    
    return {
        "job_id": job_id,
        "files": uploaded_files,
        "count": len(uploaded_files)
    }


@app.get("/api/analyze/{job_id}")
async def analyze_job(job_id: str):
    """Analyse tous les fichiers d'un job."""
    job_dir = UPLOAD_DIR / job_id
    
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job non trouvé")
    
    python_files = list_python_files(str(job_dir))
    
    if not python_files:
        raise HTTPException(status_code=404, detail="Aucun fichier Python trouvé")
    
    results = []
    total_score = 0
    
    for filepath in python_files:
        analysis = analyze_file(filepath)
        score = calculate_quality_score(analysis)
        total_score += score
        
        # Extraire les noms des fonctions et classes
        func_names = [f["name"] for f in analysis.get("functions", [])]
        class_names = [c["name"] for c in analysis.get("classes", [])]
        
        results.append({
            "file": get_relative_path(filepath, str(job_dir)),
            "functions": func_names,
            "classes": class_names,
            "issues": len(analysis.get("style_issues", [])),
            "issues_detail": analysis.get("style_issues", [])[:10],
            "lines": analysis.get("lines", 0),
            "score": score,
            "avg_complexity": analysis.get("avg_complexity", 0),
            "doc_coverage": analysis.get("doc_coverage", 0)
        })
    
    avg_score = total_score // len(results) if results else 0
    
    return {
        "job_id": job_id,
        "files": results,
        "total_files": len(results),
        "average_score": avg_score
    }


@app.post("/api/process/{job_id}")
async def process_job(job_id: str, add_docstrings: bool = True):
    """Traite tous les fichiers d'un job."""
    job_upload_dir = UPLOAD_DIR / job_id
    job_output_dir = OUTPUT_DIR / job_id
    
    print(f"[PROCESS] Job {job_id}")
    
    if not job_upload_dir.exists():
        raise HTTPException(status_code=404, detail="Job non trouvé")
    
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
            # Lire le code original
            original_code = read_file(filepath)
            
            # Correction PEP8
            corrected = correct_code(original_code)
            
            # Génération docstrings
            has_docstrings = False
            if add_docstrings:
                try:
                    final_code = generate_docstrings(corrected)
                    has_docstrings = True
                except Exception as e:
                    print(f"[PROCESS] Erreur docstrings: {e}")
                    final_code = corrected
            else:
                final_code = corrected
            
            # Sauvegarder le code
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_code)
            
            # Générer les données du rapport (calcule automatiquement les scores avant/après)
            report_data = generate_report_data(filepath, original_code, final_code, has_docstrings)
            reports_data.append(report_data)
            
            # Générer le rapport HTML individuel
            report_html = generate_html_report(report_data)
            report_path = output_path.with_suffix('.html')
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_html)
            
            print(f"[PROCESS] Score: {report_data['score_before']} -> {report_data['score_after']}")
            
            processed.append({
                "file": relative,
                "status": "ok",
                "score_before": report_data["score_before"],
                "score_after": report_data["score_after"],
                "has_docstrings": has_docstrings
            })
            
        except Exception as e:
            print(f"[PROCESS] Erreur: {e}")
            processed.append({
                "file": relative,
                "status": "error",
                "error": str(e)
            })
    
    # Générer le rapport global
    global_report = generate_global_report(reports_data, job_id)
    global_report_path = job_output_dir / "_rapport_global.html"
    with open(global_report_path, 'w', encoding='utf-8') as f:
        f.write(global_report)
    
    return {
        "job_id": job_id,
        "processed": processed,
        "count": len(processed)
    }


@app.get("/api/preview/{job_id}/{filename:path}")
async def preview_file(job_id: str, filename: str):
    """Prévisualise un fichier (original et corrigé)."""
    original_path = UPLOAD_DIR / job_id / filename
    corrected_path = OUTPUT_DIR / job_id / filename
    
    result = {
        "filename": filename,
        "original": None,
        "corrected": None
    }
    
    if original_path.exists():
        result["original"] = read_file(str(original_path))
    
    if corrected_path.exists():
        result["corrected"] = read_file(str(corrected_path))
    
    if not result["original"] and not result["corrected"]:
        raise HTTPException(status_code=404, detail="Fichier non trouvé")
    
    return result


@app.get("/api/report/{job_id}/{filename:path}")
async def get_file_report(job_id: str, filename: str):
    """Récupère le rapport HTML d'un fichier."""
    # Remplacer .py par .html
    report_filename = filename.rsplit('.', 1)[0] + '.html'
    report_path = OUTPUT_DIR / job_id / report_filename
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Rapport non trouvé")
    
    return HTMLResponse(content=read_file(str(report_path)))


@app.get("/api/report/{job_id}")
async def get_global_report(job_id: str):
    """Récupère le rapport global du job."""
    report_path = OUTPUT_DIR / job_id / "_rapport_global.html"
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Rapport global non trouvé")
    
    return HTMLResponse(content=read_file(str(report_path)))


@app.get("/api/download/{job_id}")
async def download_job(job_id: str):
    """Télécharge les fichiers traités en ZIP."""
    job_output_dir = OUTPUT_DIR / job_id
    
    if not job_output_dir.exists():
        raise HTTPException(status_code=404, detail="Aucun fichier traité trouvé")
    
    # Tous les fichiers (code + rapports)
    all_files = list(job_output_dir.rglob("*"))
    files_to_zip = [f for f in all_files if f.is_file()]
    
    if not files_to_zip:
        raise HTTPException(status_code=404, detail="Aucun fichier à télécharger")
    
    zip_path = OUTPUT_DIR / f"{job_id}_processed.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filepath in files_to_zip:
            arcname = filepath.relative_to(job_output_dir)
            zipf.write(filepath, arcname)
    
    return FileResponse(
        path=str(zip_path),
        filename=f"agentia_{job_id}.zip",
        media_type="application/zip"
    )


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)