"""
Utilidad para finalizar extracción cuando ya se tienen archivos temporales
Procesa los archivos temporales existentes sin necesidad de más navegación
"""

import os
import sys
import tempfile
from typing import List

# Añadir directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from text_processor_agent import TextProcessorAgent
    from groq import Groq
    import os
    
    def finalizar_extraccion_forzada():
        """Finaliza la extracción procesando archivos temporales existentes"""
        
        print("🔧 FINALIZANDO EXTRACCIÓN CON ARCHIVOS TEMPORALES EXISTENTES")
        print("=" * 60)
        
        # Buscar archivos temporales de extracción web en el directorio temp
        temp_dir = tempfile.gettempdir()
        temp_files = []
        
        print(f"🔍 Buscando archivos temporales en: {temp_dir}")
        
        # Buscar archivos que coincidan con el patrón de nuestros archivos temporales
        for filename in os.listdir(temp_dir):
            if filename.startswith('tmp') and filename.endswith('.txt'):
                file_path = os.path.join(temp_dir, filename)
                # Verificar que el archivo fue creado recientemente (última hora)
                if os.path.getmtime(file_path) > (os.path.getmtime(__file__) - 3600):  # Última hora
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Verificar que contenga datos de Amazon (indicativo de extracción web)
                            if 'amazon' in content.lower() or 'zapatillas' in content.lower():
                                temp_files.append(file_path)
                                print(f"  ✅ Encontrado: {filename} ({len(content)} chars)")
                    except Exception as e:
                        print(f"  ⚠️ Error leyendo {filename}: {e}")
        
        if not temp_files:
            print("❌ No se encontraron archivos temporales recientes")
            return False
        
        print(f"\n📁 Total archivos temporales encontrados: {len(temp_files)}")
        
        # Configurar Groq client
        from dotenv import load_dotenv
        load_dotenv()  # Cargar variables de entorno
        
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            print("❌ Error: GROQ_API_KEY no encontrada")
            return False
        
        try:
            client = Groq(api_key=groq_api_key)
            processor = TextProcessorAgent(client)
            
            # Procesar archivos a formato Excel/CSV
            goal = "Extraer nombres y precios de productos de Amazon para zapatillas"
            result = processor.process_temp_files_to_format(temp_files, "excel", goal)
            
            if result['success']:
                print(f"\n✅ ¡EXTRACCIÓN FINALIZADA EXITOSAMENTE!")
                print(f"📄 Archivo generado: {result['output_file']}")
                print(f"📊 Páginas procesadas: {result.get('pages_processed', 0)}")
                print(f"🤖 Método: {result.get('processing_method', 'N/A')}")
                
                # Mostrar preview del contenido
                if 'content_preview' in result:
                    print(f"\n📋 PREVIEW DEL CONTENIDO:")
                    print("-" * 40)
                    print(result['content_preview'][:500])
                    print("-" * 40)
                
                # Abrir carpeta con resultado
                if os.path.exists(result['output_file']):
                    import subprocess
                    folder_path = os.path.dirname(result['output_file'])
                    print(f"\n📂 Abriendo carpeta: {folder_path}")
                    subprocess.run(['explorer', folder_path], shell=True)
                
                return True
            else:
                print(f"❌ Error procesando archivos: {result.get('error', 'Error desconocido')}")
                return False
                
        except Exception as e:
            print(f"❌ Error configurando procesador: {e}")
            return False

    def mostrar_archivos_temporales():
        """Muestra información sobre archivos temporales disponibles"""
        
        temp_dir = tempfile.gettempdir()
        print(f"📁 Directorio temporal: {temp_dir}")
        
        temp_files = []
        for filename in os.listdir(temp_dir):
            if filename.startswith('tmp') and filename.endswith('.txt'):
                file_path = os.path.join(temp_dir, filename)
                if os.path.getmtime(file_path) > (os.path.getmtime(__file__) - 3600):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'amazon' in content.lower():
                                temp_files.append({
                                    'name': filename,
                                    'path': file_path,
                                    'size': len(content),
                                    'preview': content[:200]
                                })
                    except:
                        pass
        
        print(f"\n📋 ARCHIVOS TEMPORALES DE EXTRACCIÓN ENCONTRADOS: {len(temp_files)}")
        for i, file_info in enumerate(temp_files, 1):
            print(f"\n{i}. {file_info['name']}")
            print(f"   📏 Tamaño: {file_info['size']} caracteres")
            print(f"   📄 Preview: {file_info['preview']}...")

    if __name__ == "__main__":
        print("🚀 UTILIDAD DE FINALIZACIÓN DE EXTRACCIÓN")
        print("Esta herramienta procesa archivos temporales existentes")
        
        mostrar_archivos_temporales()
        
        print("\n" + "="*50)
        respuesta = input("¿Procesar archivos temporales encontrados? (s/n): ")
        
        if respuesta.lower() in ['s', 'si', 'y', 'yes']:
            finalizar_extraccion_forzada()
        else:
            print("👋 Operación cancelada")

except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("Asegúrate de tener todos los módulos necesarios")
    
except Exception as e:
    print(f"❌ Error general: {e}")
    