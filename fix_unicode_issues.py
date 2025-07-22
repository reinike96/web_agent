"""
Script para corregir problemas de codificaci?n Unicode en new_orchestrator.py
"""

import re

def fix_unicode_prints():
    """Corrige todos los prints con emojis problem?ticos"""
    
    file_path = "c:/Users/ALEXR/OneDrive/Desktop/Browser/web_agent/new_orchestrator.py"
    
    # Leer el archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Definir los reemplazos
    replacements = [
        # Prints b?sicos con emojis
        (r'print\(f?"[DATA]', r'self.safe_print(f"[DATA]'),
        (r'print\(f?"[PROCESSING]', r'self.safe_print(f"[RELOAD]'),  
        (r'print\(f?"[SUCCESS]', r'self.safe_print(f"[SUCCESS]'),
        (r'print\(f?"[ERROR]', r'self.safe_print(f"[ERROR]'),
        (r'print\(f?"[TARGET]', r'self.safe_print(f"[TARGET]'),
        (r'print\(f?"[WEB]', r'self.safe_print(f"[WEB]'),
        (r'print\(f?"[FILE]', r'self.safe_print(f"[FILE]'),
        (r'print\(f?"[DOCUMENT]', r'self.safe_print(f"[DOC]'),
        (r'print\(f?"[AI]', r'self.safe_print(f"[AI]'),
        (r'print\(f?"[WARNING]', r'self.safe_print(f"[WARNING]'),
        (r'print\(f?"📍', r'self.safe_print(f"[LOCATION]'),
        
        # Prints sin f-string tambi?n
        (r'print\("[DATA]', r'self.safe_print("[DATA]'),
        (r'print\("[PROCESSING]', r'self.safe_print("[RELOAD]'),  
        (r'print\("[SUCCESS]', r'self.safe_print("[SUCCESS]'),
        (r'print\("[ERROR]', r'self.safe_print("[ERROR]'),
        (r'print\("[TARGET]', r'self.safe_print("[TARGET]'),
        (r'print\("[WEB]', r'self.safe_print("[WEB]'),
        (r'print\("[FILE]', r'self.safe_print("[FILE]'),
        (r'print\("[DOCUMENT]', r'self.safe_print("[DOC]'),
        (r'print\("[AI]', r'self.safe_print("[AI]'),
        (r'print\("[WARNING]', r'self.safe_print("[WARNING]'),
        (r'print\("📍', r'self.safe_print("[LOCATION]'),
    ]
    
    # Aplicar reemplazos
    for old_pattern, new_pattern in replacements:
        content = re.sub(old_pattern, new_pattern, content)
    
    # Guardar archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("[SUCCESS] Unicode fixes applied to new_orchestrator.py")
    return True

if __name__ == "__main__":
    fix_unicode_prints()
