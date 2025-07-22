"""
Text Processor Agent - Procesa m?ltiples archivos temporales
Sistema para consolidar contenido extra?do y convertir a formatos espec?ficos
"""

import os
import tempfile
import logging
from typing import List, Dict, Any, Optional
from groq import Groq


class TextProcessorAgent:
    """
    Agente que procesa m?ltiples archivos temporales de p?ginas web
    y los convierte al formato solicitado por el usuario
    """
    
    def __init__(self, groq_client: Groq):
        self.client = groq_client
        self.model = "moonshotai/kimi-k2-instruct"
        self.logger = logging.getLogger(__name__)
    
    def process_temp_files_to_format(self, temp_files: List[str], format_type: str, goal: str) -> Dict[str, Any]:
        """
        Procesa m?ltiples archivos temporales seg?n el formato solicitado
        
        Args:
            temp_files: Lista de rutas de archivos temporales
            format_type: 'txt', 'word', 'csv', 'excel'
            goal: Objetivo original del usuario
        """
        try:
            if not temp_files:
                return {
                    "success": False,
                    "error": "No hay archivos temporales para procesar"
                }
            
            # Leer contenido de todos los archivos temporales
            all_content = []
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        with open(temp_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            all_content.append({
                                'file': temp_file,
                                'content': content
                            })
                    except Exception as e:
                        self.logger.warning(f"No se pudo leer {temp_file}: {str(e)}")
            
            if not all_content:
                return {
                    "success": False,
                    "error": "No se pudo leer ning?n archivo temporal"
                }
            
            # Procesar seg?n el formato
            if format_type.lower() in ['txt', 'word']:
                result = self._consolidate_to_text(all_content, format_type, goal)
            elif format_type.lower() in ['csv', 'excel']:
                result = self._process_to_structured(all_content, format_type, goal)
            else:
                result = self._consolidate_to_text(all_content, 'txt', goal)
            
            # Cleanup archivos temporales
            self._cleanup_temp_files(temp_files)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error procesando archivos temporales: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _consolidate_to_text(self, content_list: List[Dict], format_type: str, goal: str) -> Dict[str, Any]:
        """Consolida m?ltiples p?ginas en un archivo de texto o Word"""
        try:
            # Crear contenido consolidado
            consolidated_content = f"EXTRACCI?N WEB - {goal}\n"
            consolidated_content += "=" * 50 + "\n"
            consolidated_content += f"Fecha: {self._get_current_datetime()}\n"
            consolidated_content += f"P?ginas procesadas: {len(content_list)}\n\n"
            
            for i, page in enumerate(content_list, 1):
                consolidated_content += f"P?GINA {i}\n"
                consolidated_content += "-" * 20 + "\n"
                consolidated_content += page['content'] + "\n\n"
                consolidated_content += "=" * 50 + "\n\n"
            
            # Determinar extensi?n
            extension = ".txt" if format_type.lower() == 'txt' else ".txt"  # Word tambi?n como .txt por simplicidad
            
            # Guardar archivo final
            final_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix=extension,
                prefix='web_extraction_consolidated_',
                delete=False,
                encoding='utf-8'
            )
            
            final_file.write(consolidated_content)
            final_file.close()
            
            return {
                "success": True,
                "format": format_type,
                "output_file": final_file.name,
                "pages_processed": len(content_list),
                "processing_method": "text_consolidation",
                "content_preview": consolidated_content[:500] + "..." if len(consolidated_content) > 500 else consolidated_content
            }
            
        except Exception as e:
            self.logger.error(f"Error consolidando a texto: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _process_to_structured(self, content_list: List[Dict], format_type: str, goal: str) -> Dict[str, Any]:
        """Procesa contenido usando LLM para crear formato CSV/Excel estructurado"""
        try:
            # Preparar contenido para LLM
            combined_content = ""
            for i, page in enumerate(content_list, 1):
                combined_content += f"--- P?GINA {i} ---\n"
                # Limitar contenido para no sobrecargar el LLM
                content_preview = page['content'][:3000] + "..." if len(page['content']) > 3000 else page['content']
                combined_content += content_preview + "\n\n"
            
            # Crear prompt para LLM
            llm_prompt = f"""
Analiza el siguiente contenido extra?do de {len(content_list)} p?ginas web y convierte la informaci?n relevante a formato CSV.

OBJETIVO: {goal}

CONTENIDO EXTRA?DO:
{combined_content}

INSTRUCCIONES:
1. Identifica y extrae la informaci?n m?s relevante relacionada con el objetivo
2. Si hay productos: incluye nombres, precios, caracter?sticas, enlaces si los hay
3. Si hay art?culos: incluye t?tulos, autores, fechas, res?menes
4. Si hay datos generales: organiza en categor?as l?gicas
5. Crea encabezados de columnas apropiados en espa?ol
6. Usa formato CSV con comas como separadores
7. Encierra entre comillas los campos que contengan comas
8. No inventes informaci?n que no est? en el contenido original
9. Si no hay informaci?n estructurable, crea un resumen organizado

FORMATO DE SALIDA:
Responde ?NICAMENTE con el contenido CSV, comenzando directamente con los encabezados.
"""
            
            # Llamar al LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user", 
                        "content": llm_prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            csv_content = response.choices[0].message.content.strip()
            
            # Guardar archivo CSV
            final_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.csv',
                prefix='web_extraction_structured_',
                delete=False,
                encoding='utf-8'
            )
            
            final_file.write(csv_content)
            final_file.close()
            
            return {
                "success": True,
                "format": format_type,
                "output_file": final_file.name,
                "pages_processed": len(content_list),
                "processing_method": "llm_structured",
                "llm_used": True,
                "content_preview": csv_content[:500] + "..." if len(csv_content) > 500 else csv_content
            }
            
        except Exception as e:
            self.logger.error(f"Error procesando con LLM: {str(e)}")
            # Fallback sin LLM
            return self._create_simple_csv(content_list, format_type, goal)
    
    def _create_simple_csv(self, content_list: List[Dict], format_type: str, goal: str) -> Dict[str, Any]:
        """Fallback: crear CSV simple sin LLM"""
        try:
            csv_content = "P?gina,Contenido\n"
            
            for i, page in enumerate(content_list, 1):
                # Limpiar contenido para CSV
                content_clean = page['content'].replace('"', '""').replace('\n', ' ').replace('\r', '')[:500]
                csv_content += f'"{i}","{content_clean}"\n'
            
            # Guardar archivo
            final_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.csv',
                prefix='web_extraction_simple_',
                delete=False,
                encoding='utf-8'
            )
            
            final_file.write(csv_content)
            final_file.close()
            
            return {
                "success": True,
                "format": format_type,
                "output_file": final_file.name,
                "pages_processed": len(content_list),
                "processing_method": "simple_csv_fallback",
                "llm_used": False,
                "content_preview": csv_content
            }
            
        except Exception as e:
            self.logger.error(f"Error creando CSV simple: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _cleanup_temp_files(self, temp_files: List[str]):
        """Limpia archivos temporales"""
        cleaned = 0
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    cleaned += 1
            except Exception as e:
                self.logger.warning(f"No se pudo limpiar {temp_file}: {str(e)}")
        
        if cleaned > 0:
            self.logger.info(f"Limpiados {cleaned} archivos temporales")
    
    def _get_current_datetime(self) -> str:
        """Retorna fecha y hora actual formateada"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_processing_summary(self, result: Dict[str, Any]) -> str:
        """Retorna resumen del procesamiento para mostrar al usuario"""
        if not result.get("success"):
            return f"[ERROR] Error: {result.get('error', 'Error desconocido')}"
        
        summary = f"[SUCCESS] Procesamiento exitoso\n"
        summary += f"   [DOCUMENT] Formato: {result.get('format', 'N/A').upper()}\n"
        summary += f"   [DATA] P?ginas procesadas: {result.get('pages_processed', 0)}\n"
        summary += f"   [AI] M?todo: {result.get('processing_method', 'N/A')}\n"
        summary += f"   [FILE] Archivo generado: {os.path.basename(result.get('output_file', 'N/A'))}\n"
        
        if result.get('llm_used'):
            summary += f"   [AI] LLM utilizado para estructuraci?n inteligente\n"
        
        return summary
