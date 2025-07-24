from browser_controller import BrowserController
import time

# Crear instancia del browser
browser = BrowserController()

# Ir a X.com home
browser.open_url('https://x.com/home')
time.sleep(5)

# Cargar y ejecutar el script de extracción
with open('extractJsonInteractive_simple.js', 'r', encoding='utf-8') as f:
    js_script = f.read()

# Agregar return para que funcione con Selenium
js_with_return = 'return ' + js_script
result = browser.execute_script(js_with_return)

print('ELEMENTOS EXTRAÍDOS:')
if result and result.get('elements'):
    for i, element in enumerate(result['elements'][:15]):
        print(f'{i+1}. {element.get("tag", "N/A")} - {element.get("selector", "N/A")}')
        print(f'   Text: {element.get("text", "N/A")}')
        print(f'   Contenteditable: {element.get("contenteditable", "N/A")}')
        print(f'   Data-testid: {element.get("data-testid", "N/A")}')
        print()
else:
    print('No se pudieron extraer elementos')

browser.close_browser()
