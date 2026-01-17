"""
Module de correction automatique PEP8.
"""

import autopep8
from utils import read_file, write_file


def correct_code(code: str) -> str:
    """
    Corrige le code Python selon les règles PEP8.
    
    Args:
        code: Code source Python
        
    Returns:
        Code corrigé
    """
    return autopep8.fix_code(code, options={
        'max_line_length': 120,
        'aggressive': 1
    })


def correct_file(filepath: str, output_path: str = None) -> str:
    """
    Corrige un fichier Python et l'enregistre.
    
    Args:
        filepath: Chemin du fichier source
        output_path: Chemin de sortie (optionnel)
        
    Returns:
        Code corrigé
    """
    original = read_file(filepath)
    corrected = correct_code(original)
    
    if output_path:
        write_file(output_path, corrected)
    
    return corrected
