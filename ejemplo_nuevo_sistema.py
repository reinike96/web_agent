#!/usr/bin/env python3
"""
Ejemplo de uso del nuevo sistema de procesamiento de contenido
Demuestra el flujo completo: extracción → LLM → consolidación → archivo final
"""
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from safe_print_utils import safe_print_global as safe_print

def ejemplo_amazon_zapatillas():
    """
    Ejemplo: Extraer zapatillas >10€ de Amazon en 3 páginas → Excel
    """
    safe_print("=== EJEMPLO: AMAZON ZAPATILLAS → EXCEL ===")
    
    # PASO 1: Objetivo del usuario
    objetivo = "Extraer los nombres y precios de las zapatillas que cuestan más de 10 euros en las 3 primeras páginas de amazon.de"
    
    safe_print(f"[OBJETIVO] {objetivo}")
    safe_print("")
    
    # PASO 2: Plan de ejecución
    plan = [
        "1. Navigate to https://www.amazon.de",
        "2. Search for 'zapatillas'", 
        "3. Extract and process page 1 (extract_and_process_current_page)",
        "4. Go to page 2",
        "5. Extract and process page 2 (extract_and_process_current_page)",
        "6. Go to page 3", 
        "7. Extract and process page 3 (extract_and_process_current_page)",
        "8. Generate final Excel document (generate_final_document)"
    ]
    
    safe_print("[PLAN] Pasos a ejecutar:")
    for step in plan:
        safe_print(f"  {step}")
    safe_print("")
    
    # PASO 3: Flujo técnico detallado
    safe_print("[FLUJO TÉCNICO] Lo que sucede internamente:")
    safe_print("")
    
    safe_print("📄 POR CADA PÁGINA (1, 2, 3):")
    safe_print("  1. extract_page_content():")
    safe_print("     • Ejecuta extractText.js en la página actual")  
    safe_print("     • El JS extrae texto limpio y lo imprime en consola")
    safe_print("     • Python captura el texto de los logs del browser")
    safe_print("     • Guarda en memoria: {page_number, url, title, content}")
    safe_print("")
    
    safe_print("  2. process_page_with_llm():")
    safe_print("     • Envía contenido + objetivo original al LLM")
    safe_print("     • Prompt: 'Extrae zapatillas >10€ de este contenido'")
    safe_print("     • LLM devuelve JSON estructurado con productos")
    safe_print("     • Guarda resultado procesado en memoria")
    safe_print("")
    
    safe_print("🔄 DESPUÉS DE PROCESAR LAS 3 PÁGINAS:")
    safe_print("  3. generate_final_document():")
    safe_print("     • Consolida los 3 resultados del LLM")
    safe_print("     • Prompt: 'Combina estos resultados en informe final'")
    safe_print("     • Genera Excel con resumen + detalles por página")
    safe_print("     • Usuario elige destino del archivo")
    safe_print("     • Limpia memoria automáticamente")
    safe_print("")
    
    # PASO 4: Estructura de datos en memoria
    safe_print("[MEMORIA] Estructura de datos:")
    safe_print("")
    safe_print("extracted_pages = [")
    safe_print("  {page_number: 1, url: 'amazon.de/s?k=zapatillas&page=1',")
    safe_print("   title: 'Amazon.de: zapatillas', content: '...(texto extraído)...'},")
    safe_print("  {page_number: 2, url: 'amazon.de/s?k=zapatillas&page=2', ...},")
    safe_print("  {page_number: 3, url: 'amazon.de/s?k=zapatillas&page=3', ...}")
    safe_print("]")
    safe_print("")
    safe_print("processed_results = [")
    safe_print("  {page_number: 1, llm_response: '{productos: [...], resumen: \"...\"'},")
    safe_print("  {page_number: 2, llm_response: '{productos: [...], resumen: \"...\"'},") 
    safe_print("  {page_number: 3, llm_response: '{productos: [...], resumen: \"...\"'}")
    safe_print("]")
    safe_print("")
    
    # PASO 5: Archivo final
    safe_print("[RESULTADO] Archivo Excel generado:")
    safe_print("  📊 Hoja 'Resumen':")
    safe_print("     • Objetivo original")
    safe_print("     • Fecha de extracción") 
    safe_print("     • Total de páginas procesadas")
    safe_print("     • Resultados consolidados del LLM")
    safe_print("")
    safe_print("  📋 Hoja 'Detalles por Página':")
    safe_print("     • Tabla con página, título, URL, caracteres")
    safe_print("")
    safe_print("  💾 Usuario elige destino (ej: 'zapatillas_amazon_20250122.xlsx')")
    safe_print("")
    
    return True

def ejemplo_wikipedia_articulo():
    """
    Ejemplo: Extraer artículo de Wikipedia → Word procesado por LLM
    """
    safe_print("=== EJEMPLO: WIKIPEDIA ARTÍCULO → WORD ===")
    
    objetivo = "Ir a Wikipedia, extraer toda la información del artículo sobre 'Machine Learning' y generar un resumen ejecutivo en Word"
    
    safe_print(f"[OBJETIVO] {objetivo}")
    safe_print("")
    
    plan = [
        "1. Navigate to https://es.wikipedia.org/wiki/Aprendizaje_automático",
        "2. Extract and process current page (extract_and_process_current_page)",
        "3. Generate final Word document (generate_final_document)"
    ]
    
    safe_print("[PLAN] Pasos para Wikipedia:")
    for step in plan:
        safe_print(f"  {step}")
    safe_print("")
    
    safe_print("[FLUJO TÉCNICO] Para artículo único:")
    safe_print("  1. extractText.js extrae todo el contenido del artículo")
    safe_print("  2. LLM procesa: 'Crea resumen ejecutivo de este artículo'")
    safe_print("  3. generate_final_document formato='word'")
    safe_print("  4. Usuario elige destino (ej: 'machine_learning_resumen.docx')")
    safe_print("")
    
    safe_print("[RESULTADO] Documento Word:")
    safe_print("  📄 Título: 'INFORME DE EXTRACCIÓN DE DATOS WEB'")
    safe_print("  📋 Información general (objetivo, fecha, páginas)")
    safe_print("  📖 Resumen ejecutivo procesado por LLM")
    safe_print("  📊 Tabla con detalles de la página")
    safe_print("")
    
    return True

def mostrar_ventajas_sistema():
    """
    Muestra las ventajas del nuevo sistema
    """
    safe_print("=== VENTAJAS DEL NUEVO SISTEMA ===")
    safe_print("")
    
    safe_print("🚀 MEJORAS IMPLEMENTADAS:")
    safe_print("  ✅ Sin archivos temporales - todo en memoria")
    safe_print("  ✅ JavaScript optimizado para extracción limpia") 
    safe_print("  ✅ LLM procesa cada página individualmente")
    safe_print("  ✅ Consolidación inteligente de resultados")
    safe_print("  ✅ Usuario elige formato y destino del archivo")
    safe_print("  ✅ Limpieza automática de memoria")
    safe_print("  ✅ Compatible con cualquier sitio web")
    safe_print("")
    
    safe_print("📋 FORMATOS SOPORTADOS:")
    safe_print("  📊 Excel (.xlsx) - Perfecto para datos estructurados")
    safe_print("  📄 Word (.docx) - Ideal para informes y artículos")
    safe_print("  🔧 Extensible a otros formatos")
    safe_print("")
    
    safe_print("🎯 CASOS DE USO:")
    safe_print("  🛒 E-commerce: Productos, precios, reviews")
    safe_print("  📚 Investigación: Artículos, papers, documentación") 
    safe_print("  📊 Análisis: Datos de mercado, competencia")
    safe_print("  📰 Contenido: Noticias, blogs, foros")
    safe_print("")
    
    return True

if __name__ == "__main__":
    safe_print("🎯 EJEMPLOS DEL NUEVO SISTEMA DE PROCESAMIENTO")
    safe_print("=" * 60)
    safe_print("")
    
    # Ejemplo 1: Amazon
    ejemplo_amazon_zapatillas()
    safe_print("")
    
    # Ejemplo 2: Wikipedia  
    ejemplo_wikipedia_articulo()
    safe_print("")
    
    # Ventajas del sistema
    mostrar_ventajas_sistema()
    
    safe_print("🎉 SISTEMA COMPLETAMENTE IMPLEMENTADO Y LISTO!")
    safe_print("")
    safe_print("Para usar el sistema:")
    safe_print("1. Configurar: set GROQ_API_KEY=tu_clave_aqui")
    safe_print("2. Ejecutar: python main.py") 
    safe_print("3. Usar las nuevas acciones en el plan del LLM:")
    safe_print("   • extract_and_process_current_page")
    safe_print("   • generate_final_document")
    safe_print("")
    safe_print("El LLM automáticamente elegirá estas acciones según el objetivo!")
