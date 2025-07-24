from browser_controller import BrowserController
import time

# Crear instancia del browser y navegar a X.com
browser = BrowserController()
browser.open_url('https://x.com/home')
time.sleep(5)

# Código exacto del log que supuestamente no devuelve nada
js_code = """
(function() {
    // Include simulatePaste function definition here first
    function simulatePaste(element, text) {
        element.focus();
        
        // STEP 1: Clear ALL existing content completely
        if (element.tagName === 'DIV' && element.contentEditable === 'true') {
            // For contenteditable elements - multiple clearing methods
            element.click();
            element.focus();
            
            // Method 1: Select all and delete
            const selection = window.getSelection();
            selection.selectAllChildren(element);
            selection.deleteFromDocument();
            
            // Method 2: Clear content directly
            element.textContent = '';
            element.innerHTML = '';
            
            // Method 3: Ensure it's really empty
            while (element.firstChild) {
                element.removeChild(element.firstChild);
            }
        } else {
            // For input/textarea elements
            element.select();
            element.value = '';
        }
        
        // STEP 2: Insert new text using paste event
        const pasteEvent = new ClipboardEvent("paste", {
            bubbles: true,
            cancelable: true,
            clipboardData: new DataTransfer()
        });
        
        pasteEvent.clipboardData.setData("text/plain", text);
        element.dispatchEvent(pasteEvent);
        
        // STEP 3: Fallback if paste event didn't work
        if (element.tagName === 'DIV' && element.contentEditable === 'true') {
            if (!element.textContent || element.textContent.trim() === '') {
                element.textContent = text;
            }
        } else {
            if (!element.value || element.value.trim() === '') {
                element.value = text;
            }
        }
        
        // STEP 4: Trigger events for framework detection
        element.dispatchEvent(new Event('input', {bubbles: true}));
        element.dispatchEvent(new Event('change', {bubbles: true}));
        element.dispatchEvent(new Event('blur', {bubbles: true}));
    }
    
    // Find the "Escribir nuevo mensaje" button which is the compose button
    const composeButton = document.querySelector('button[aria-label="Escribir nuevo mensaje"]');
    
    if (!composeButton) {
        return {
            success: false,
            message: "No se encontró el botón 'Escribir nuevo mensaje'",
            action_performed: "click_button",
            verification_details: {
                expected: "El botón 'Escribir nuevo mensaje' debería estar presente y ser clickeable",
                actual: "No se encontró el botón en el DOM",
                element_found: false,
                action_completed: false
            },
            debug_info: {
                selector_used: 'button[aria-label="Escribir nuevo mensaje"]',
                element_text: null
            }
        };
    }
    
    // Click the compose button
    composeButton.click();
    
    // Verify the click was successful by checking if the tweet textarea is now visible
    const tweetTextarea = document.querySelector('[data-testid="tweetTextarea_0"]');
    
    const success = tweetTextarea !== null && tweetTextarea.contentEditable === true;
    
    return {
        success: success,
        message: success ? "Botón 'Escribir nuevo mensaje' clickeado exitosamente" : "El botón fue clickeado pero no se detectó el área de texto",
        action_performed: "click_button",
        verification_details: {
            expected: "El área de texto para nuevos posts debería estar visible después del click",
            actual: success ? "El área de texto está disponible" : "No se encontró el área de texto",
            element_found: true,
            action_completed: success
        },
        debug_info: {
            selector_used: 'button[aria-label="Escribir nuevo mensaje"]',
            element_text: composeButton.textContent
        }
    };
})();
"""

# Prueba básica sin IIFE
basic_test = "return 'test string';"

print("=== PRUEBA BÁSICA: Return string ===")
result_basic = browser.execute_script(basic_test)
print(f"Resultado: {result_basic}")
print(f"Tipo: {type(result_basic)}")

# Prueba con objeto simple sin IIFE
object_test = "return {test: true, message: 'hello'};"

print("\n=== PRUEBA OBJETO: Return object ===")
result_object = browser.execute_script(object_test)
print(f"Resultado: {result_object}")
print(f"Tipo: {type(result_object)}")

# Prueba con IIFE muy simple
iife_test = "(function() { return 'iife test'; })();"

print("\n=== PRUEBA IIFE: IIFE simple ===")
result_iife = browser.execute_script(iife_test)
print(f"Resultado: {result_iife}")
print(f"Tipo: {type(result_iife)}")

# Prueba con console.log para ver si el código se ejecuta
console_test = "console.log('JavaScript ejecutándose'); return 'ejecutado';"

print("\n=== PRUEBA CONSOLE: Console log ===")
result_console = browser.execute_script(console_test)
print(f"Resultado: {result_console}")
print(f"Tipo: {type(result_console)}")

browser.close_browser()
