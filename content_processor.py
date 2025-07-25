#!/usr/bin/env python3
"""
Content Processing Agent
Maneja la extracci?n, procesamiento y consolidaci?n de contenido de m?ltiples p?ginas
"""
import os
import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from safe_print_utils import safe_print_global as safe_print

class ContentProcessor:
    """
    Procesa contenido extra?do de m?ltiples p?ginas web
    """
    
    def __init__(self, browser_controller, llm_controller):
        self.browser = browser_controller
        self.llm = llm_controller
        self.extracted_pages = []  # Lista de p?ginas extra?das
        self.processed_results = []  # Resultados procesados por LLM
        
        # Cargar JavaScript extractor
        self.js_extractor_path = Path(__file__).parent / "extractText.js"
        if self.js_extractor_path.exists():
            with open(self.js_extractor_path, 'r', encoding='utf-8') as f:
                self.js_extractor_code = f.read()
        else:
            safe_print("[ERROR] extractText.js not found")
            self.js_extractor_code = None
    
    def extract_page_content(self, page_number: int = None) -> Optional[Dict[str, Any]]:
        """
        Extrae el contenido de la p?gina actual usando JavaScript
        """
        if not self.js_extractor_code:
            safe_print("[ERROR] JavaScript extractor not available")
            return None
            
        try:
            safe_print(f"[EXTRACT] Extrayendo contenido de la p?gina {page_number or 'actual'}...")
            
            # Obtener informaci?n b?sica de la p?gina
            current_url = self.browser.driver.current_url
            page_title = self.browser.driver.title
            
            # Ejecutar JavaScript para extraer contenido
            safe_print("[JS] Ejecutando extractText.js...")
            extracted_content = self.browser.driver.execute_script(self.js_extractor_code)
            
            # Obtener logs de la consola (donde se imprime el contenido)
            logs = self.browser.driver.get_log('browser')
            
            # Extraer el contenido de los logs de consola
            content_text = ""
            for log in logs:
                if "EXTRACTED CONTENT FROM:" in log.get('message', ''):
                    # Parsear el contenido del log
                    message = log.get('message', '')
                    if '--- EXTRACTED CONTENT FROM:' in message and '--- END OF CONTENT ---' in message:
                        start_marker = '--- EXTRACTED CONTENT FROM:'
                        end_marker = '--- END OF CONTENT ---'
                        start_idx = message.find(start_marker)
                        end_idx = message.find(end_marker)
                        if start_idx != -1 and end_idx != -1:
                            content_text = message[start_idx + len(start_marker):end_idx].strip()
                            break
            
            # Si no se obtuvo contenido de los logs, usar m?todo alternativo
            if not content_text:
                safe_print("[INFO] Usando m?todo alternativo de extracci?n...")
                # Ejecutar JS que retorne el contenido directamente
                js_return_content = """
                function extractContent() {
                    const bodyClone = document.body.cloneNode(true);
                    const selectorsToRemove = [
                        'header', 'footer', 'nav', 'aside', 'script', 'style', 
                        'noscript', 'iframe', 'form', '[role="navigation"]',
                        '[role="banner"]', '[role="complementary"]', '[role="contentinfo"]',
                        '.header', '.footer', '#header', '#footer'
                    ];
                    bodyClone.querySelectorAll(selectorsToRemove.join(',')).forEach(el => el.remove());
                    
                    const mainSelectors = ['article', 'main', '.post', '#content', '#main', '.main'];
                    let mainContent = null;
                    for (const selector of mainSelectors) {
                        mainContent = bodyClone.querySelector(selector);
                        if (mainContent) break;
                    }
                    const contentElement = mainContent || bodyClone;
                    let textContent = contentElement.innerText || '';
                    return textContent.replace(/^\\s*[\\r\\n]/gm, '').trim();
                }
                return extractContent();
                """
                content_text = self.browser.driver.execute_script(js_return_content)
            
            if not content_text:
                safe_print("[WARNING] No se pudo extraer contenido de la p?gina")
                return None
            
            # Crear estructura de datos para la p?gina extra?da
            page_data = {
                'page_number': page_number,
                'url': current_url,
                'title': page_title,
                'content': content_text,
                'extracted_at': datetime.now().isoformat(),
                'content_length': len(content_text)
            }
            
            # Guardar en memoria
            self.extracted_pages.append(page_data)
            
            safe_print(f"[SUCCESS] Contenido extra?do: {len(content_text)} caracteres")
            safe_print(f"[INFO] T?tulo: {page_title}")
            safe_print(f"[INFO] URL: {current_url}")
            
            return page_data
            
        except Exception as e:
            safe_print(f"[ERROR] Error extrayendo contenido: {e}")
            return None
    
    def process_page_with_llm(self, page_data: Dict[str, Any], original_objective: str) -> Optional[Dict[str, Any]]:
        """
        Procesa el contenido de una p?gina con el LLM seg?n el objetivo original
        """
        if not page_data or not page_data.get('content'):
            safe_print("[ERROR] No hay contenido para procesar")
            return None
            
        try:
            safe_print(f"[LLM] Procesando p?gina {page_data.get('page_number', 'N/A')} con LLM...")
            
            # Crear prompt espec?fico para el procesamiento
            prompt = f"""
Objetivo original del usuario: {original_objective}

Contenido extra?do de la p?gina:
URL: {page_data.get('url', 'N/A')}
T?tulo: {page_data.get('title', 'N/A')}

Contenido:
{page_data['content']}

Instrucciones:
1. Analiza el contenido extra?do seg?n el objetivo original del usuario
2. Extrae SOLO la informaci?n relevante que cumple con el objetivo
3. Estructura la informaci?n de manera clara y organizada
4. Si el objetivo menciona filtros (como precios, categor?as, etc.), apl?calos
5. Devuelve la informaci?n en formato JSON estructurado

Ejemplo de respuesta esperada:
{{
    "productos_encontrados": [
        {{"nombre": "Nombre del producto", "precio": "?XX.XX", "descripcion": "..."}}
    ],
    "resumen": "X productos encontrados que cumplen los criterios",
    "pagina_info": "P?gina X de Amazon.de"
}}

Responde ?nicamente con el JSON estructurado:
"""
            
            # Enviar al LLM
            response = self.llm.generate_response(
                prompt, 
                context="Procesamiento de contenido extra?do para objetivo espec?fico"
            )
            
            if response:
                # Crear resultado estructurado
                processed_result = {
                    'page_number': page_data.get('page_number'),
                    'url': page_data.get('url'),
                    'title': page_data.get('title'),
                    'original_objective': original_objective,
                    'llm_response': response,
                    'processed_at': datetime.now().isoformat()
                }
                
                # Guardar en memoria
                self.processed_results.append(processed_result)
                
                safe_print(f"[SUCCESS] P?gina procesada por LLM")
                safe_print(f"[INFO] Respuesta LLM: {response[:200]}...")
                
                return processed_result
            else:
                safe_print("[ERROR] LLM no devolvi? respuesta")
                return None
                
        except Exception as e:
            safe_print(f"[ERROR] Error procesando con LLM: {e}")
            return None
    
    def consolidate_results(self, original_objective: str, output_format: str = "excel") -> Optional[str]:
        """
        Consolida todas las respuestas del LLM en un archivo final
        """
        if not self.processed_results:
            safe_print("[ERROR] No hay resultados procesados para consolidar")
            return None
            
        try:
            safe_print(f"[CONSOLIDATE] Consolidando {len(self.processed_results)} resultados...")
            
            # Crear prompt de consolidaci?n
            consolidation_prompt = f"""
Objetivo original: {original_objective}

Resultados procesados de {len(self.processed_results)} p?ginas:

"""
            
            for i, result in enumerate(self.processed_results, 1):
                consolidation_prompt += f"""
--- P?GINA {i} ---
URL: {result.get('url', 'N/A')}
T?tulo: {result.get('title', 'N/A')}
Resultado procesado: {result.get('llm_response', 'N/A')}

"""
            
            consolidation_prompt += f"""
Instrucciones para consolidaci?n:
1. Combina todos los resultados de las p?ginas en un informe final coherente
2. Elimina duplicados si existen
3. Organiza la informaci?n de manera l?gica
4. Crea un resumen ejecutivo al inicio
5. Incluye estad?sticas totales si es relevante
6. El formato debe ser apropiado para {output_format}

Genera un informe consolidado completo:
"""
            
            # Enviar al LLM para consolidaci?n
            consolidated_response = self.llm.generate_response(
                consolidation_prompt,
                context="Consolidaci?n final de resultados multi-p?gina"
            )
            
            if consolidated_response:
                safe_print("[SUCCESS] Resultados consolidados por LLM")
                return consolidated_response
            else:
                safe_print("[ERROR] Error en consolidaci?n LLM")
                return None
                
        except Exception as e:
            safe_print(f"[ERROR] Error consolidando resultados: {e}")
            return None
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen del contenido en memoria
        """
        return {
            'pages_extracted': len(self.extracted_pages),
            'pages_processed': len(self.processed_results),
            'total_content_chars': sum(page.get('content_length', 0) for page in self.extracted_pages),
            'pages_info': [
                {
                    'page_number': page.get('page_number'),
                    'title': page.get('title', '')[:50],
                    'url': page.get('url', '')[:50],
                    'content_length': page.get('content_length', 0)
                }
                for page in self.extracted_pages
            ]
        }
    
    def clear_memory(self):
        """
        Limpia la memoria despu?s de generar el documento final
        """
        pages_count = len(self.extracted_pages)
        results_count = len(self.processed_results)
        
        self.extracted_pages.clear()
        self.processed_results.clear()
        
        safe_print(f"[CLEANUP] Memoria limpiada: {pages_count} p?ginas y {results_count} resultados eliminados")
