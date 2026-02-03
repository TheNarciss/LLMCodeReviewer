"""
Service LLM flexible : utilise l'API si configurée, sinon fallback sur Ollama local.
Supporte OpenRouter, OpenAI, et tout API compatible.
"""

import os
import subprocess
import httpx
from dotenv import load_dotenv

# Charger .env depuis le dossier parent (racine du projet)
from pathlib import Path
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
    
    # Headers de base
    headers = {
        "Authorization": f"Bearer {LLM_API_TOKEN}",
        "Content-Type": "application/json",
    }
    
    # Headers spécifiques pour OpenRouter
    if "openrouter" in LLM_API_URL.lower():
        headers["HTTP-Referer"] = "http://localhost:8000"
        headers["X-Title"] = "AgentIA Code Standardizer"
    
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": "Tu es un expert Python. Tu ajoutes des docstrings Google-style claires et concises. Tu retournes UNIQUEMENT le code Python, sans texte avant ou après."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 8192
    }
    
    try:
        print(f"[LLM] Appel API: {LLM_API_URL}")
        print(f"[LLM] Modèle: {LLM_MODEL}")
        
        with httpx.Client(timeout=180.0) as client:
            response = client.post(LLM_API_URL, json=payload, headers=headers)
            
            # Debug
            print(f"[LLM] Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[LLM] Erreur: {response.text}")
                raise RuntimeError(f"API Error {response.status_code}: {response.text}")
            
            data = response.json()
            
            # Extraire la réponse
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                print(f"[LLM] Réponse reçue ({len(content)} chars)")
                return content
            else:
                raise RuntimeError(f"Format de réponse inattendu: {data}")
                
    except httpx.TimeoutException:
        raise RuntimeError("Timeout: l'API n'a pas répondu dans les 180 secondes")
    except Exception as e:
        raise RuntimeError(f"Erreur API LLM: {e}")


def call_ollama(prompt: str) -> str:
    """Appelle Ollama en local."""
    try:
        print(f"[LLM] Appel Ollama local: {LLM_MODEL}")
        
        # Essayer d'abord l'API REST d'Ollama (recommandé)
        try:
            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=300.0
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("response", "").strip()
            print(f"[LLM] Réponse reçue ({len(content)} chars)")
            return content
        except (httpx.RequestError, httpx.HTTPStatusError, httpx.ConnectError):
            print("[LLM] API REST non disponible, tentative avec subprocess...")
        
        # Fallback: utiliser subprocess avec encodage explicite
        result = subprocess.run(
            ["ollama", "run", LLM_MODEL],
            input=prompt,
            text=True,
            encoding='utf-8',  # Spécifier explicitement UTF-8
            errors='replace',  # Gérer les erreurs d'encodage
            capture_output=True,
            check=True,
            timeout=300
        )
        content = result.stdout.strip()
        print(f"[LLM] Réponse reçue ({len(content)} chars)")
        return content
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        raise RuntimeError(f"Erreur Ollama: {error_msg}")
    except FileNotFoundError:
        raise RuntimeError("Ollama n'est pas installé. Installez-le depuis https://ollama.com/")
    except UnicodeDecodeError as e:
        raise RuntimeError(f"Erreur d'encodage avec Ollama: {e}. Essayez de redémarrer Ollama.")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout: Ollama n'a pas répondu dans les 5 minutes")
    except Exception as e:
        raise RuntimeError(f"Erreur inattendue avec Ollama: {e}")


def generate(prompt: str) -> str:
    """
    Point d'entrée principal : utilise l'API si configurée, sinon Ollama.
    
    Args:
        prompt: Le prompt à envoyer au LLM
        
    Returns:
        La réponse du LLM
    """
    if is_api_configured():
        print("[LLM] Mode: API externe")
        return call_api(prompt)
    else:
        print("[LLM] Mode: Ollama local")
        return call_ollama(prompt)


def get_backend_info() -> dict:
    """Retourne les infos sur le backend LLM utilisé."""
    if is_api_configured():
        # Masquer le token
        masked_token = LLM_API_TOKEN[:10] + "..." if len(LLM_API_TOKEN) > 10 else "***"
        return {
            "backend": "api",
            "url": LLM_API_URL,
            "model": LLM_MODEL,
            "token": masked_token
        }
    return {
        "backend": "ollama",
        "model": LLM_MODEL
    }