"""
Script para corregir problemas de codificación Unicode en new_orchestrator.py
"""

import re

def fix_unicode_prints():
    """Corrige todos los prints con emojis problemáticos"""
    
    file_path = "c:/Users/ALEXR/OneDrive/Desktop/Browser/web_agent/new_orchestrator.py"
    
    # Leer el archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Definir los reemplazos
    replacements = [
        # Prints básicos con emojis
        (r'print\(f?"📊', r'self.safe_print(f"[DATA]'),
        (r'print\(f?"🔄', r'self.safe_print(f"[RELOAD]'),  
        (r'print\(f?"✅', r'self.safe_print(f"[SUCCESS]'),
        (r'print\(f?"❌', r'self.safe_print(f"[ERROR]'),
        (r'print\(f?"🎯', r'self.safe_print(f"[TARGET]'),
        (r'print\(f?"🌐', r'self.safe_print(f"[WEB]'),
        (r'print\(f?"📁', r'self.safe_print(f"[FILE]'),
        (r'print\(f?"📄', r'self.safe_print(f"[DOC]'),
        (r'print\(f?"🤖', r'self.safe_print(f"[AI]'),
        (r'print\(f?"⚠️', r'self.safe_print(f"[WARNING]'),
        (r'print\(f?"📍', r'self.safe_print(f"[LOCATION]'),
        
        # Prints sin f-string también
        (r'print\("📊', r'self.safe_print("[DATA]'),
        (r'print\("🔄', r'self.safe_print("[RELOAD]'),  
        (r'print\("✅', r'self.safe_print("[SUCCESS]'),
        (r'print\("❌', r'self.safe_print("[ERROR]'),
        (r'print\("🎯', r'self.safe_print("[TARGET]'),
        (r'print\("🌐', r'self.safe_print("[WEB]'),
        (r'print\("📁', r'self.safe_print("[FILE]'),
        (r'print\("📄', r'self.safe_print("[DOC]'),
        (r'print\("🤖', r'self.safe_print("[AI]'),
        (r'print\("⚠️', r'self.safe_print("[WARNING]'),
        (r'print\("📍', r'self.safe_print("[LOCATION]'),
    ]
    
    # Aplicar reemplazos
    for old_pattern, new_pattern in replacements:
        content = re.sub(old_pattern, new_pattern, content)
    
    # Guardar archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Unicode fixes applied to new_orchestrator.py")
    return True

if __name__ == "__main__":
    fix_unicode_prints()
