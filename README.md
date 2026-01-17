# AgentIA - Python Code Standardizer

Application web pour analyser, corriger (PEP8) et documenter automatiquement du code Python.

![Stack](https://img.shields.io/badge/Stack-Python%20%2B%20FastAPI%20%2B%20JS-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Fonctionnalités

- 📁 **Upload de dossiers** — Importez plusieurs fichiers Python ou un ZIP
- 🔍 **Analyse statique** — Détection des erreurs PEP8 avec Flake8
- 🛠️ **Correction automatique** — Correction PEP8 avec autopep8
- 🤖 **Docstrings IA** — Génération automatique via LLM (API ou Ollama)
- 📦 **Export ZIP** — Téléchargez vos fichiers corrigés

## Architecture

```
agentia_v2/
├── backend/
│   ├── app.py              # API FastAPI
│   ├── analyser.py         # Analyse statique (AST, Flake8)
│   ├── corrector.py        # Correction PEP8
│   ├── generator_docstring.py  # Génération docstrings
│   ├── llm_service.py      # Service LLM (API ou Ollama)
│   └── utils.py            # Utilitaires
├── frontend/
│   ├── index.html          # Interface web
│   ├── style.css           # Styles
│   └── app.js              # Logic JS
├── uploads/                # Fichiers uploadés (temporaire)
├── outputs/                # Fichiers traités
├── .env.example            # Configuration exemple
├── requirements.txt
└── README.md
```

## Installation

### 1. Cloner et installer

```bash
# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configurer le LLM

**Option A : Ollama (local, gratuit)**

```bash
# Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh  # Linux/Mac
# ou: winget install Ollama.Ollama  # Windows

# Télécharger un modèle
ollama pull llama3.2:3b
```

**Option B : API externe (OpenAI, etc.)**

```bash
# Copier le fichier de configuration
cp .env.example .env

# Éditer .env avec vos credentials
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_TOKEN=sk-...
LLM_MODEL=gpt-4
```

### 3. Lancer l'application

```bash
cd backend
python app.py
```

Ouvrir http://localhost:8000

## API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/status` | Statut de l'API et backend LLM |
| POST | `/api/upload` | Upload fichiers Python/ZIP |
| GET | `/api/analyze/{job_id}` | Analyse des fichiers |
| POST | `/api/process/{job_id}` | Traitement (PEP8 + docstrings) |
| GET | `/api/download/{job_id}` | Télécharger le ZIP résultat |
| GET | `/api/preview/{job_id}/{file}` | Prévisualiser un fichier |
| DELETE | `/api/job/{job_id}` | Supprimer un job |

## Utilisation

1. **Glissez-déposez** vos fichiers Python ou un ZIP
2. **Consultez l'analyse** — Score, fonctions, classes, erreurs
3. **Choisissez les options** — PEP8 (obligatoire) + Docstrings (optionnel)
4. **Lancez le traitement**
5. **Téléchargez** vos fichiers corrigés

## Configuration LLM

L'application détecte automatiquement la configuration :

- Si `LLM_API_URL` et `LLM_API_TOKEN` sont définis → utilise l'API
- Sinon → utilise Ollama en local

Le modèle par défaut est `llama3.2:3b`, modifiable via `LLM_MODEL`.

## Développement

```bash
# Mode développement avec rechargement automatique
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## License

MIT
