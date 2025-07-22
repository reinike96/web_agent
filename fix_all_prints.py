"""
Script mejorado para corregir TODOS los prints problem?ticos
"""

def fix_all_prints():
    file_path = "c:/Users/ALEXR/OneDrive/Desktop/Browser/web_agent/new_orchestrator.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Procesar l?nea por l?nea
    fixed_lines = []
    for line in lines:
        # Si la l?nea contiene print( y no es ya safe_print, convertirla
        if 'print(' in line and 'self.safe_print(' not in line and 'print(f"' not in line.strip():
            # Para prints sin f-string
            if 'print("' in line:
                fixed_line = line.replace('print("', 'self.safe_print("')
            elif "print('" in line:
                fixed_line = line.replace("print('", "self.safe_print('")
            else:
                fixed_line = line
        elif 'print(f"' in line and 'self.safe_print(' not in line:
            # Para prints con f-string
            fixed_line = line.replace('print(f"', 'self.safe_print(f"')
        elif "print(f'" in line and 'self.safe_print(' not in line:
            fixed_line = line.replace("print(f'", "self.safe_print(f'")
        else:
            fixed_line = line
        
        fixed_lines.append(fixed_line)
    
    # Guardar archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("[SUCCESS] All print statements converted to safe_print")

if __name__ == "__main__":
    fix_all_prints()
