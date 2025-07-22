#!/usr/bin/env python3
"""Script para eliminar todos los emojis de los archivos Python"""

import os
import re
from pathlib import Path

# Diccionario de reemplazos de emojis
EMOJI_REPLACEMENTS = {
    '🔧': '[TOOLS]',
    '🔍': '[SEARCH]',
    '✅': '[SUCCESS]',
    '⚠️': '[WARNING]',
    '❌': '[ERROR]',
    '📄': '[DOCUMENT]',
    '📊': '[DATA]',
    '📁': '[FILE]',
    '🤖': '[AI]',
    '📚': '[BOOKS]',
    '🧠': '[BRAIN]',
    '📋': '[LIST]',
    '🚀': '[LAUNCH]',
    '💾': '[SAVE]',
    '🎯': '[TARGET]',
    '🔄': '[PROCESSING]',
    '💡': '[IDEA]',
    '🎉': '[CELEBRATE]',
    '⏭️': '[SKIP]',
    '🌐': '[WEB]',
    '🔗': '[LINK]',
    '📱': '[MOBILE]',
    '💻': '[DESKTOP]',
    '⭐': '[STAR]',
    '🛑': '[STOP]',
    '▶️': '[PLAY]',
    '⏸️': '[PAUSE]',
    '⏹️': '[STOP]',
    '🔊': '[AUDIO]',
    '🔇': '[MUTE]',
    '🗃️': '[ARCHIVE]',
    '📈': '[CHART]',
    '📉': '[GRAPH]',
    '🏆': '[TROPHY]',
    '🎖️': '[MEDAL]',
    '🥇': '[GOLD]',
    '🥈': '[SILVER]',
    '🥉': '[BRONZE]',
    '🔑': '[KEY]',
    '🎪': '[EVENT]',
    '🎭': '[THEATER]',
    '🎨': '[ART]',
    '🎵': '[MUSIC]',
    '🎶': '[MELODY]',
    '🖱️': '[CLICK]'
}

def clean_emojis_in_file(file_path):
    """Limpia emojis en un archivo específico"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Reemplazar emojis conocidos
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            content = content.replace(emoji, replacement)
        
        # Remover cualquier otro carácter Unicode alto que pueda causar problemas
        content = re.sub(r'[\u0080-\uffff]', '?', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[SUCCESS] Limpiado: {file_path}")
            return True
        else:
            print(f"[INFO] Sin cambios: {file_path}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error procesando {file_path}: {e}")
        return False

def main():
    """Función principal"""
    print("[LAUNCH] Iniciando limpieza de emojis...")
    
    # Obtener todos los archivos Python
    python_files = list(Path('.').glob('*.py'))
    
    cleaned_count = 0
    
    for file_path in python_files:
        if file_path.name == 'clean_all_emojis.py':  # Saltar este script
            continue
            
        if clean_emojis_in_file(file_path):
            cleaned_count += 1
    
    print(f"\n[SUCCESS] Proceso completado. {cleaned_count} archivos modificados.")

if __name__ == "__main__":
    main()
