#!/usr/bin/env python3
"""
File Generator Agent
Genera archivos finales (Excel, Word) con los resultados consolidados
"""
import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from safe_print_utils import safe_print_global as safe_print

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    safe_print("[WARNING] openpyxl no disponible - instalando...")

try:
    from docx import Document
    from docx.shared import Inches
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False
    safe_print("[WARNING] python-docx no disponible - instalando...")

class FileGenerator:
    """
    Genera archivos finales con los resultados consolidados
    """
    
    def __init__(self):
        self.install_dependencies()
    
    def install_dependencies(self):
        """
        Instala las dependencias necesarias si no est?n disponibles
        """
        global EXCEL_AVAILABLE, WORD_AVAILABLE
        
        if not EXCEL_AVAILABLE:
            try:
                import subprocess
                subprocess.check_call(['pip', 'install', 'openpyxl'])
                import openpyxl
                from openpyxl.styles import Font, Alignment, PatternFill
                EXCEL_AVAILABLE = True
                safe_print("[SUCCESS] openpyxl instalado correctamente")
            except Exception as e:
                safe_print(f"[ERROR] No se pudo instalar openpyxl: {e}")
        
        if not WORD_AVAILABLE:
            try:
                import subprocess
                subprocess.check_call(['pip', 'install', 'python-docx'])
                from docx import Document
                WORD_AVAILABLE = True
                safe_print("[SUCCESS] python-docx instalado correctamente")
            except Exception as e:
                safe_print(f"[ERROR] No se pudo instalar python-docx: {e}")
    
    def choose_output_file(self, default_name: str = "resultado", file_type: str = "excel") -> Optional[str]:
        """
        Muestra di?logo para que el usuario elija el destino del archivo
        """
        try:
            # Create hidden root window
            root = tk.Tk()
            root.withdraw()  # Hide main window
            root.lift()
            root.attributes('-topmost', True)
            
            # Configure file types based on requested type
            if file_type.lower() == "excel":
                filetypes = [("Excel files", "*.xlsx"), ("All files", "*.*")]
                default_ext = ".xlsx"
            elif file_type.lower() == "word":
                filetypes = [("Word documents", "*.docx"), ("All files", "*.*")]
                default_ext = ".docx"
            else:
                filetypes = [("All files", "*.*")]
                default_ext = ".txt"
            
            # Generate default name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"{default_name}_{timestamp}{default_ext}"
            
            # Show save file dialog
            file_path = filedialog.asksaveasfilename(
                title=f"Save {file_type} file",
                defaultextension=default_ext,
                filetypes=filetypes,
                initialfile=default_filename
            )
            
            root.destroy()
            
            if file_path:
                safe_print(f"[USER] File selected: {file_path}")
                return file_path
            else:
                safe_print("[INFO] User cancelled file selection")
                return None
                
        except Exception as e:
            safe_print(f"[ERROR] Error showing file dialog: {e}")
            return None
    
    def parse_ascii_table(self, text: str) -> List[List[str]]:
        """
        Parse ASCII table from text and return rows and columns
        """
        lines = text.split('\n')
        table_data = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines and separator lines
            if not line or line.startswith('+-') or line.startswith('|-') or set(line) == {'-', '|', '+', ' '}:
                continue
                
            # Check if this looks like a table row
            if '|' in line:
                # Split by | and clean up
                columns = [col.strip() for col in line.split('|')]
                # Remove empty first/last columns (from leading/trailing |)
                if columns and columns[0] == '':
                    columns = columns[1:]
                if columns and columns[-1] == '':
                    columns = columns[:-1]
                
                if columns:  # Only add non-empty rows
                    table_data.append(columns)
        
        return table_data

    def generate_excel_file(self, consolidated_data: str, original_objective: str, 
                          summary_info: Dict[str, Any], output_path: str = None) -> Optional[str]:
        """
        Generate Excel file with pure table data (no metadata for table format)
        """
        if not EXCEL_AVAILABLE:
            safe_print("[ERROR] openpyxl not available to generate Excel")
            return None

        try:
            # Seleccionar archivo de salida si no se proporciona
            if not output_path:
                output_path = self.choose_output_file("extracted_results", "excel")
                if not output_path:
                    return None

            safe_print(f"[EXCEL] Generating Excel file with table data: {output_path}")
            
            # Crear workbook
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            
            wb = Workbook()
            wb.remove(wb.active)  # Remove default sheet
            
            # Parse all ASCII tables from consolidated data
            sections = consolidated_data.split('\n\n')
            sheet_number = 1
            
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for section in sections:
                if not section.strip():
                    continue
                    
                # Try to parse as ASCII table
                table_data = self.parse_ascii_table(section)
                
                if table_data and len(table_data) > 0:
                    # Create new sheet for this table
                    sheet_name = f"Table_{sheet_number}"
                    ws = wb.create_sheet(sheet_name)
                    
                    # Add table data
                    for row_idx, row_data in enumerate(table_data, 1):
                        for col_idx, cell_value in enumerate(row_data, 1):
                            cell = ws.cell(row=row_idx, column=col_idx, value=cell_value)
                            cell.border = border
                            
                            # Style header row
                            if row_idx == 1:
                                cell.font = header_font
                                cell.fill = header_fill
                                cell.alignment = Alignment(horizontal='center', vertical='center')
                            else:
                                cell.alignment = Alignment(vertical='center')
                    
                    # Auto-adjust column widths
                    for col_idx in range(1, len(table_data[0]) + 1 if table_data else 1):
                        max_length = 0
                        column_letter = ws.cell(row=1, column=col_idx).column_letter
                        
                        for row_idx in range(1, len(table_data) + 1):
                            cell_value = ws.cell(row=row_idx, column=col_idx).value
                            if cell_value:
                                max_length = max(max_length, len(str(cell_value)))
                        
                        adjusted_width = min(max_length + 3, 50)
                        ws.column_dimensions[column_letter].width = max(adjusted_width, 12)
                    
                    sheet_number += 1
                
                else:
                    # If not a table, check if it contains useful text data
                    text_lines = [line.strip() for line in section.split('\n') if line.strip()]
                    if text_lines:
                        # Create a simple sheet with the text content
                        sheet_name = f"Content_{sheet_number}"
                        ws = wb.create_sheet(sheet_name)
                        
                        for row_idx, line in enumerate(text_lines, 1):
                            ws.cell(row=row_idx, column=1, value=line)
                        
                        # Auto-adjust column width
                        max_length = max(len(line) for line in text_lines) if text_lines else 20
                        ws.column_dimensions['A'].width = min(max_length + 3, 100)
                        
                        sheet_number += 1
            
            # If no sheets were created, create a default one
            if len(wb.sheetnames) == 0:
                ws = wb.create_sheet("Data")
                ws.cell(row=1, column=1, value="No table data found in the processed content")
            
            # Guardar archivo
            wb.save(output_path)
            
            safe_print(f"[SUCCESS] Excel file generated with {len(wb.sheetnames)} sheet(s): {output_path}")
            return output_path
            
        except Exception as e:
            safe_print(f"[ERROR] Error generating Excel file: {e}")
            return None
    
    def generate_word_file(self, consolidated_data: str, original_objective: str,
                         summary_info: Dict[str, Any], output_path: str = None) -> Optional[str]:
        """
        Generate clean Word file with only LLM responses (no metadata)
        """
        if not WORD_AVAILABLE:
            safe_print("[ERROR] python-docx not available to generate Word")
            return None
        
        try:
            # Select output file if not provided
            if not output_path:
                output_path = self.choose_output_file("extracted_report", "word")
                if not output_path:
                    return None
            
            safe_print(f"[WORD] Generating Word file: {output_path}")
            
            # Create document
            from docx import Document
            from docx.shared import Inches
            
            doc = Document()
            
            # Extract only the LLM-generated content
            lines = consolidated_data.split('\n')
            content_started = False
            clean_content = []
            
            for line in lines:
                line = line.strip()
                
                # Skip metadata lines
                if any(metadata in line for metadata in [
                    'WEB DATA EXTRACTION REPORT',
                    'TASK RESULTS:',
                    'Processing completed:',
                    'Pages analyzed:',
                    'Original Objective:',
                    'Extraction Date:',
                    'Pages Processed:',
                    'Total Characters:',
                    'General Information',
                    'Consolidated Results'
                ]):
                    continue
                    
                # Look for actual content sections
                if line.startswith('CONSOLIDATED RESULT:') or line.startswith('COMPREHENSIVE SUMMARY:'):
                    content_started = True
                    continue
                elif line.startswith('INDIVIDUAL PAGE RESULTS:'):
                    content_started = True
                    continue
                
                # Add meaningful content
                if content_started and line:
                    # Skip page indicators like "Page 1:"
                    if not line.startswith('Page ') or ':' not in line:
                        clean_content.append(line)
                    elif ':' in line and not line.startswith('Page '):
                        # Keep lines that have colons but aren't page indicators
                        clean_content.append(line)
                elif line and not any(skip in line for skip in ['===', '---', 'PROCESSING SUMMARY']):
                    clean_content.append(line)
            
            # If no clean content found, use all non-metadata content
            if not clean_content:
                for line in lines:
                    line = line.strip()
                    if line and not any(metadata in line for metadata in [
                        'WEB DATA EXTRACTION REPORT',
                        'TASK RESULTS:',
                        'Processing completed:',
                        'Pages analyzed:',
                        'Original Objective:',
                        'Extraction Date:',
                        'Pages Processed:',
                        'Total Characters:',
                        '===', '---'
                    ]):
                        clean_content.append(line)
            
            # Add clean content to document
            for line in clean_content:
                if line.strip():
                    doc.add_paragraph(line.strip())
            
            # Save document
            doc.save(output_path)
            
            safe_print(f"[SUCCESS] Clean Word document generated: {output_path}")
            return output_path
            
        except Exception as e:
            safe_print(f"[ERROR] Error generating Word file: {e}")
            return None
    
    def open_file_location(self, file_path: str):
        """
        Abre la ubicaci?n del archivo generado
        """
        try:
            import subprocess
            import platform
            
            if platform.system() == 'Windows':
                subprocess.run(['explorer', '/select,', file_path])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', '-R', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', os.path.dirname(file_path)])
                
            safe_print(f"[INFO] File location opened: {file_path}")
            
        except Exception as e:
            safe_print(f"[ERROR] Could not open file location: {e}")
    
    def show_success_dialog(self, file_path: str):
        """
        Show success dialog with option to open the file
        """
        try:
            root = tk.Tk()
            root.withdraw()
            
            result = messagebox.askyesno(
                "File Generated Successfully",
                f"The file has been generated correctly:\n\n{file_path}\n\nDo you want to open the file location?",
                icon="info"
            )
            
            root.destroy()
            
            if result:
                self.open_file_location(file_path)
                
        except Exception as e:
            safe_print(f"[ERROR] Error showing success dialog: {e}")
