"""
Service LLM flexible : utilise l'API si configurée, sinon fallback sur Ollama local.
Supporte OpenRouter, OpenAI, et tout API compatible.
"""

import os
import subprocess
import httpx
from dotenv import load_dotenv
from pathlib import Path

# Charger .env depuis le dossier parent (racine du projet)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Configuration
LLM_API_URL = os.getenv("LLM_API_URL", "").strip()
LLM_API_TOKEN = os.getenv("LLM_API_TOKEN", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b").strip()


def is_api_configured() -> bool:
    """Vérifie si l'API externe est configurée."""
    return bool(LLM_API_URL and LLM_API_TOKEN)


def call_api(prompt: str) -> str:
    """Appelle l'API LLM externe (compatible OpenAI/OpenRouter)."""
    
    headers = {
        "Authorization": f"Bearer {LLM_API_TOKEN}",
        "Content-Type": "application/json",
    }
    
    if "openrouter" in LLM_API_URL.lower():
        headers["HTTP-Referer"] = "http://localhost:8000"
        headers["X-Title"] = "AgentIA Code Standardizer"
    
    # CORRECTION ICI : System Prompt neutre. 
    # C'est le 'prompt' utilisateur qui contient les instructions spécifiques (Code ou Doc).
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": "Tu es un assistant expert en programmation Python. Suis scrupuleusement les instructions de l'utilisateur."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2, # Faible pour être précis
        "max_tokens": 8192
    }
    
    try:
        print(f"[LLM] Appel API: {LLM_MODEL}")
        
        with httpx.Client(timeout=180.0) as client:
            response = client.post(LLM_API_URL, json=payload, headers=headers)
            
            if response.status_code != 200:
                print(f"[LLM] Erreur Status: {response.status_code}")
                # On évite de crash ici, on retourne l'erreur pour les logs
                return f"Erreur API ({response.status_code}): {response.text}"
            
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                return content
            else:
                return f"Erreur format réponse: {data}"
                
    except httpx.TimeoutException:
        return "Erreur: Timeout API (180s)"
    except Exception as e:
        return f"Erreur Exception API: {e}"


def call_ollama(prompt: str) -> str:
    """Appelle Ollama en local."""
    try:
        print(f"[LLM] Appel Ollama local: {LLM_MODEL}")
        
        # 1. Tentative API REST (Plus rapide/stable)
        try:
            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": LLM_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "system": "Tu es un assistant expert en Python." # System prompt neutre aussi
                },
                timeout=300.0
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception:
            pass # Fallback sur subprocess si l'API échoue
        
        # 2. Fallback Subprocess
        result = subprocess.run(
            ["ollama", "run", LLM_MODEL],
            input=prompt,
            text=True,
            encoding='utf-8',
            errors='replace',
            capture_output=True,
            timeout=300
        )
        if result.returncode != 0:
            return f"Erreur Ollama CLI: {result.stderr}"
            
        return result.stdout.strip()

    except Exception as e:
        return f"Erreur critique Ollama: {str(e)}"


def generate(prompt: str) -> str:
    """Point d'entrée principal."""
    if is_api_configured():
        return call_api(prompt)
    else:
        return call_ollama(prompt)


def get_backend_info() -> dict:
    """Retourne les infos sur le backend."""
    if is_api_configured():
        masked = LLM_API_TOKEN[:6] + "..." if len(LLM_API_TOKEN) > 6 else "***"
        return {"backend": "api", "model": LLM_MODEL, "token": masked}
    return {"backend": "ollama", "model": LLM_MODEL}