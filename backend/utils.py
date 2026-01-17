"""
Fonctions utilitaires communes.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path


def read_file(filepath: str) -> str:
    """Lit et retourne le contenu d'un fichier texte."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(filepath: str, content: str):
    """Écrit du contenu dans un fichier (crée le dossier si besoin)."""
    path = Path(filepath)
    if path.parent and str(path.parent) != '.':
        path.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def list_python_files(folder: str) -> list:
    """Renvoie la liste des fichiers .py dans un dossier (récursif)."""
    python_files = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.endswith(".py") and not f.startswith("__"):
                python_files.append(os.path.join(root, f))
    return python_files


def ensure_dir(path: str):
    """Crée un dossier s'il n'existe pas."""
    Path(path).mkdir(parents=True, exist_ok=True)


def clean_dir(path: str):
    """Vide un dossier s'il existe."""
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


def timestamp() -> str:
    """Retourne un timestamp au format 'YYYYMMDD_HHMMSS'."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_relative_path(filepath: str, base: str) -> str:
    """Retourne le chemin relatif d'un fichier par rapport à un dossier de base."""
    return os.path.relpath(filepath, base)