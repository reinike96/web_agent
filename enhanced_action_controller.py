"""
Enhanced Action Controller with intelligent feedback and error recovery
Controlador de acciones mejorado con retroalimentación inteligente y recuperación de errores
"""

import json
import time
import logging
from typing import Dict, List, Tuple, Optional
from safe_print_utils import safe_print_global

class EnhancedActionController:
    """
    Sistema mejorado de control de acciones con:
    1. Retroalimentación inteligente de scripts JS
    2. Análisis de estado de página
    3. Reintentos con estrategias diferentes
    4. Detección de éxito contextual
    """
    
    def __init__(self, browser_controller, llm_controller):
        self.browser = browser_controller
        self.llm = llm_controller
        self.logger = logging.getLogger(__name__)
        
        # Historial de acciones para evitar loops
        self.action_history = []
        self.failed_actions = {}  # selector -> count
        self.page_state_cache = {}
        
    def execute_action_with_feedback(self, action: dict, page_info: dict) -> dict:
        """
        Ejecuta una acción con retroalimentación completa del resultado
        """
        action_type = action.get("action", "")
        action_id = f"{action_type}_{int(time.time())}"
        
        self.logger.info(f"[{action_id}] Executing action: {action}")
        
        # 1. Analizar estado actual de la página
        current_state = self._analyze_page_state(page_info)
        
        # 2. Verificar si la acción es realmente necesaria
        if self._is_action_redundant(action, current_state):
            return {
                "success": True,
                "message": "Action not needed - already in target state",
                "details": current_state,
                "skip_reason": "redundant"
            }
        
        # 3. Ejecutar la acción con script JS mejorado
        result = self._execute_with_enhanced_js(action, page_info)
        
        # 4. Analizar el resultado y proporcionar retroalimentación
        feedback = self._analyze_action_result(result, action, page_info)
        
        # 5. Si falló, intentar estrategias alternativas
        if not feedback.get("success", False):
            feedback = self._try_alternative_strategies(action, page_info, result)
        
        # 6. Actualizar historial
        self._update_action_history(action, feedback)
        
        return feedback
    
    def _analyze_page_state(self, page_info: dict) -> dict:
        """
        Analiza el estado actual de la página para detectar contexto
        """
        interactive_elements = page_info.get("interactive_elements", {})
        url = interactive_elements.get("url", "")
        title = interactive_elements.get("title", "")
        elements = interactive_elements.get("elements", [])
        
        state = {
            "url": url,
            "title": title,
            "has_search_box": False,
            "has_results": False,
            "has_login_form": False,
            "current_page_type": "unknown",
            "interactive_count": len(elements),
            "key_elements": []
        }
        
        # Detectar elementos clave
        for element in elements:
            text = element.get("text", "").lower()
            tag = element.get("tag", "").lower()
            element_type = element.get("type", "").lower()
            
            # Cajas de búsqueda
            if element_type in ["search", "text"] or "search" in text:
                state["has_search_box"] = True
                state["key_elements"].append({
                    "type": "search_box",
                    "selector": element.get("selector"),
                    "text": text
                })
            
            # Resultados de búsqueda
            if "result" in text or tag in ["article", "li"] and len(text) > 50:
                state["has_results"] = True
                state["key_elements"].append({
                    "type": "search_result",
                    "selector": element.get("selector"),
                    "text": text[:100]
                })
            
            # Formularios de login
            if element_type in ["email", "password"] or "login" in text:
                state["has_login_form"] = True
        
        # Determinar tipo de página
        if "amazon" in url and "s?" in url:
            state["current_page_type"] = "amazon_search_results"
        elif "wikipedia" in url:
            state["current_page_type"] = "wikipedia"
        elif state["has_search_box"] and not state["has_results"]:
            state["current_page_type"] = "search_page"
        elif state["has_results"]:
            state["current_page_type"] = "results_page"
        
        return state
    
    def _is_action_redundant(self, action: dict, current_state: dict) -> bool:
        """
        Verifica si una acción es redundante dado el estado actual
        """
        action_type = action.get("action", "")
        
        # Si estamos tratando de buscar pero ya estamos en resultados
        if action_type in ["click_element", "enter_text"] and current_state.get("current_page_type") == "results_page":
            # Verificar si la acción es para buscar
            params = action.get("parameters", {})
            selector = params.get("selector", "")
            text = params.get("text", "").lower()
            
            if "search" in selector or any(keyword in text for keyword in ["buscar", "search", "zapatillas"]):
                self.logger.info("Action redundant: already in search results page")
                return True
        
        return False
    
    def _execute_with_enhanced_js(self, action: dict, page_info: dict) -> dict:
        """
        Ejecuta la acción usando scripts JS mejorados con retroalimentación detallada
        """
        action_type = action.get("action", "")
        parameters = action.get("parameters", {})
        
        if action_type == "click_element":
            return self._enhanced_click_element(parameters.get("selector"), page_info)
        elif action_type == "enter_text":
            return self._enhanced_enter_text(parameters.get("selector"), parameters.get("text"), page_info)
        elif action_type == "enter_text_no_enter":
            return self._enhanced_enter_text(parameters.get("selector"), parameters.get("text"), page_info, press_enter=False)
        elif action_type == "click_button":
            return self._enhanced_click_button(parameters.get("keywords", []), page_info)
        else:
            # Fallback al método original del browser_controller
            return {"success": False, "message": f"Action type {action_type} not implemented in enhanced controller"}
    
    def _enhanced_click_element(self, selector: str, page_info: dict) -> dict:
        """
        Click mejorado con retroalimentación detallada
        """
        js_script = f"""
        (function() {{
            console.log('[ENHANCED_CLICK] Starting click attempt for selector: {selector}');
            
            try {{
                // Paso 1: Buscar el elemento
                let element = document.querySelector('{selector}');
                console.log('[ENHANCED_CLICK] Element found:', !!element);
                
                if (!element) {{
                    // Intentar selectores alternativos
                    const alternativeSelectors = [
                        '{selector}',
                        '{selector.replace("'", "")}',
                        '{selector.lower()}',
                        // Más selectores alternativos basados en el selector original
                    ];
                    
                    for (let altSelector of alternativeSelectors) {{
                        element = document.querySelector(altSelector);
                        if (element) {{
                            console.log('[ENHANCED_CLICK] Found with alternative selector:', altSelector);
                            break;
                        }}
                    }}
                }}
                
                if (!element) {{
                    return {{
                        success: false,
                        error: 'element_not_found',
                        message: 'Element not found with selector: {selector}',
                        available_elements: Array.from(document.querySelectorAll('button, input, a, [role="button"]')).slice(0, 10).map(el => ({{
                            tag: el.tagName,
                            text: el.textContent.trim().substring(0, 50),
                            selector: el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase())
                        }}))
                    }};
                }}
                
                // Paso 2: Verificar si el elemento es clickeable
                const rect = element.getBoundingClientRect();
                const isVisible = rect.width > 0 && rect.height > 0 && 
                                element.offsetParent !== null &&
                                window.getComputedStyle(element).visibility !== 'hidden';
                
                console.log('[ENHANCED_CLICK] Element visible:', isVisible);
                console.log('[ENHANCED_CLICK] Element rect:', rect);
                
                if (!isVisible) {{
                    // Intentar hacer scroll al elemento
                    element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    // Esperar sin usar await
                    setTimeout(function() {{
                        console.log('[ENHANCED_CLICK] Scrolled to element');
                    }}, 1000);
                }}
                
                // Paso 3: Ejecutar el click
                const clickMethods = [
                    function() {{ element.click(); }},
                    function() {{ element.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true }})); }},
                    function() {{ element.dispatchEvent(new Event('click', {{ bubbles: true }})); }}
                ];
                
                let clickSuccess = false;
                let clickMethod = '';
                
                for (let i = 0; i < clickMethods.length; i++) {{
                    try {{
                        clickMethods[i]();
                        clickSuccess = true;
                        clickMethod = 'method_' + (i + 1);
                        console.log('[ENHANCED_CLICK] Click successful with method:', clickMethod);
                        break;
                    }} catch (e) {{
                        console.log('[ENHANCED_CLICK] Click method', (i + 1), 'failed:', e.message);
                    }}
                }}
                
                // Paso 4: Verificar el resultado después de un tiempo (sin await)
                setTimeout(function() {{
                    console.log('[ENHANCED_CLICK] Post-click verification completed');
                }}, 1500);
                
                const afterClick = {{
                    url_changed: window.location.href !== '{page_info.get("interactive_elements", {}).get("url", "")}',
                    new_elements: document.querySelectorAll('*[data-testid], button, input, a').length,
                    page_title: document.title
                }};
                
                console.log('[ENHANCED_CLICK] After click state:', afterClick);
                
                return {{
                    success: clickSuccess,
                    message: clickSuccess ? 'Click executed successfully' : 'Click failed with all methods',
                    details: {{
                        element_found: true,
                        was_visible: isVisible,
                        click_method: clickMethod,
                        url_before: '{page_info.get("interactive_elements", {}).get("url", "")}',
                        url_after: window.location.href,
                        url_changed: afterClick.url_changed,
                        element_text: element.textContent.trim(),
                        element_tag: element.tagName
                    }}
                }};
                
            }} catch (error) {{
                console.error('[ENHANCED_CLICK] Unexpected error:', error);
                return {{
                    success: false,
                    error: 'unexpected_error',
                    message: 'Unexpected error during click: ' + error.message,
                    stack: error.stack
                }};
            }}
        }})();
        """
        
        try:
            result = self.browser.driver.execute_script(js_script)
            self.logger.info(f"Click result: {result}")
            return result if isinstance(result, dict) else {"success": False, "message": "Invalid response from JS"}
        except Exception as e:
            return {
                "success": False, 
                "error": "script_execution_failed",
                "message": f"Failed to execute click script: {str(e)}"
            }
    
    def _enhanced_enter_text(self, selector: str, text: str, page_info: dict, press_enter: bool = True) -> dict:
        """
        Entrada de texto mejorada con retroalimentación detallada
        """
        enter_key = "element.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));" if press_enter else ""
        
        js_script = f"""
        (function() {{
            console.log('[ENHANCED_TEXT] Starting text entry for selector: {selector}');
            console.log('[ENHANCED_TEXT] Text to enter: {text}');
            console.log('[ENHANCED_TEXT] Press enter: {press_enter}');
            
            try {{
                let element = document.querySelector('{selector}');
                console.log('[ENHANCED_TEXT] Element found:', !!element);
                
                if (!element) {{
                    // Buscar elementos de entrada alternativos
                    const alternativeSelectors = [
                        'input[type="text"]',
                        'input[type="search"]', 
                        'textarea',
                        '[contenteditable="true"]',
                        'input:not([type="hidden"])',
                        '[role="textbox"]'
                    ];
                    
                    for (let altSelector of alternativeSelectors) {{
                        const elements = document.querySelectorAll(altSelector);
                        if (elements.length > 0) {{
                            element = elements[0]; // Tomar el primero
                            console.log('[ENHANCED_TEXT] Found alternative element:', altSelector);
                            break;
                        }}
                    }}
                }}
                
                if (!element) {{
                    return {{
                        success: false,
                        error: 'input_element_not_found',
                        message: 'No input element found with selector: {selector}',
                        available_inputs: Array.from(document.querySelectorAll('input, textarea, [contenteditable]')).slice(0, 5).map(el => ({{
                            tag: el.tagName,
                            type: el.type || 'none',
                            placeholder: el.placeholder || '',
                            selector: el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase())
                        }}))
                    }};
                }}
                
                // Verificar si el elemento puede recibir texto
                const isInput = element.tagName === 'INPUT' || element.tagName === 'TEXTAREA';
                const isContentEditable = element.contentEditable === 'true';
                
                console.log('[ENHANCED_TEXT] Element type check:', {{ isInput, isContentEditable }});
                
                if (!isInput && !isContentEditable) {{
                    return {{
                        success: false,
                        error: 'element_not_editable',
                        message: 'Element is not editable',
                        element_info: {{
                            tag: element.tagName,
                            contentEditable: element.contentEditable,
                            type: element.type
                        }}
                    }};
                }}
                
                // Enfocar el elemento
                element.focus();
                setTimeout(function() {{
                    console.log('[ENHANCED_TEXT] Element focused');
                }}, 500);
                
                // Limpiar contenido existente
                if (isInput) {{
                    element.value = '';
                }} else if (isContentEditable) {{
                    element.textContent = '';
                }}
                
                // Introducir el texto
                let textEntered = false;
                const textMethods = [
                    function() {{
                        if (isInput) {{
                            element.value = '{text}';
                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }} else {{
                            element.textContent = '{text}';
                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }},
                    function() {{
                        // Método alternativo: simular tipeo
                        element.dispatchEvent(new Event('focus'));
                        if (isInput) {{
                            element.value = '{text}';
                        }} else {{
                            element.innerHTML = '{text}';
                        }}
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                ];
                
                for (let method of textMethods) {{
                    try {{
                        method();
                        textEntered = true;
                        console.log('[ENHANCED_TEXT] Text entered successfully');
                        break;
                    }} catch (e) {{
                        console.log('[ENHANCED_TEXT] Text method failed:', e.message);
                    }}
                }}
                
                // Presionar Enter si es necesario (sin async/await)
                if ({str(press_enter).lower()} && textEntered) {{
                    setTimeout(function() {{
                        try {{
                            {enter_key}
                            console.log('[ENHANCED_TEXT] Enter key pressed');
                        }} catch (e) {{
                            console.log('[ENHANCED_TEXT] Enter key failed:', e.message);
                        }}
                    }}, 500);
                }}
                
                // Verificar que el texto se haya introducido (sin async/await)
                setTimeout(function() {{
                    const currentValue = isInput ? element.value : element.textContent;
                    const textWasEntered = currentValue.includes('{text}');
                    console.log('[ENHANCED_TEXT] Verification - text was entered:', textWasEntered);
                }}, 1000);
                
                const currentValue = isInput ? element.value : element.textContent;
                const textWasEntered = currentValue.includes('{text}') || textEntered;
                
                return {{
                    success: textEntered && textWasEntered,
                    message: textEntered ? 'Text entered successfully' : 'Failed to enter text',
                    details: {{
                        element_found: true,
                        element_type: element.tagName,
                        is_editable: isInput || isContentEditable,
                        text_requested: '{text}',
                        text_entered: currentValue,
                        text_matches: textWasEntered,
                        enter_pressed: {str(press_enter).lower()}
                    }}
                }};
                
            }} catch (error) {{
                console.error('[ENHANCED_TEXT] Unexpected error:', error);
                return {{
                    success: false,
                    error: 'unexpected_error',
                    message: 'Unexpected error during text entry: ' + error.message
                }};
            }}
        }})();
        """
        
        try:
            result = self.browser.driver.execute_script(js_script)
            self.logger.info(f"Text entry result: {result}")
            return result if isinstance(result, dict) else {"success": False, "message": "Invalid response from JS"}
        except Exception as e:
            return {
                "success": False,
                "error": "script_execution_failed", 
                "message": f"Failed to execute text entry script: {str(e)}"
            }
    
    def _enhanced_click_button(self, keywords: List[str], page_info: dict) -> dict:
        """
        Click de botón mejorado buscando por palabras clave
        """
        keywords_js = json.dumps(keywords) if keywords else '[]'
        
        js_script = f"""
        (function() {{
            console.log('[ENHANCED_BUTTON] Looking for button with keywords:', {keywords_js});
            
            const keywords = {keywords_js};
            const buttons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], [role="button"], a[href]'));
            
            console.log('[ENHANCED_BUTTON] Found', buttons.length, 'potential buttons');
            
            let targetButton = null;
            let matchReason = '';
            
            // Buscar botón que coincida con las palabras clave
            for (let button of buttons) {{
                const buttonText = button.textContent.toLowerCase().trim();
                const buttonValue = (button.value || '').toLowerCase();
                const buttonTitle = (button.title || '').toLowerCase();
                const buttonAriaLabel = (button.getAttribute('aria-label') || '').toLowerCase();
                
                // Si no hay palabras clave, buscar botones comunes
                if (keywords.length === 0) {{
                    const commonButtons = ['search', 'buscar', 'submit', 'send', 'enviar', 'go', 'enter'];
                    if (commonButtons.some(common => 
                        buttonText.includes(common) || 
                        buttonValue.includes(common) || 
                        buttonTitle.includes(common) ||
                        buttonAriaLabel.includes(common)
                    )) {{
                        targetButton = button;
                        matchReason = 'common_button_pattern';
                        break;
                    }}
                }} else {{
                    // Buscar coincidencias con palabras clave
                    if (keywords.some(keyword => 
                        buttonText.includes(keyword.toLowerCase()) || 
                        buttonValue.includes(keyword.toLowerCase()) ||
                        buttonTitle.includes(keyword.toLowerCase()) ||
                        buttonAriaLabel.includes(keyword.toLowerCase())
                    )) {{
                        targetButton = button;
                        matchReason = 'keyword_match';
                        break;
                    }}
                }}
            }}
            
            if (!targetButton && buttons.length > 0) {{
                // Fallback: tomar el primer botón visible
                targetButton = buttons.find(btn => {{
                    const rect = btn.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                }});
                matchReason = 'first_visible_button';
            }}
            
            if (!targetButton) {{
                return {{
                    success: false,
                    error: 'no_button_found',
                    message: 'No suitable button found',
                    available_buttons: buttons.slice(0, 10).map(btn => ({{
                        text: btn.textContent.trim().substring(0, 50),
                        value: btn.value || '',
                        tag: btn.tagName,
                        type: btn.type || ''
                    }}))
                }};
            }}
            
            console.log('[ENHANCED_BUTTON] Target button found:', targetButton.textContent.trim());
            console.log('[ENHANCED_BUTTON] Match reason:', matchReason);
            
            // Ejecutar el click
            try {{
                const rect = targetButton.getBoundingClientRect();
                const isVisible = rect.width > 0 && rect.height > 0;
                
                if (!isVisible) {{
                    targetButton.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    setTimeout(function() {{
                        console.log('[ENHANCED_BUTTON] Scrolled to button');
                    }}, 1000);
                }}
                
                targetButton.click();
                console.log('[ENHANCED_BUTTON] Button clicked successfully');
                
                // Esperar y verificar cambios (sin async/await)
                setTimeout(function() {{
                    console.log('[ENHANCED_BUTTON] Post-click verification completed');
                }}, 2000);
                
                return {{
                    success: true,
                    message: 'Button clicked successfully',
                    details: {{
                        button_text: targetButton.textContent.trim(),
                        button_type: targetButton.type || targetButton.tagName,
                        match_reason: matchReason,
                        url_before: '{page_info.get("interactive_elements", {}).get("url", "")}',
                        url_after: window.location.href,
                        url_changed: window.location.href !== '{page_info.get("interactive_elements", {}).get("url", "")}'
                    }}
                }};
                
            }} catch (error) {{
                return {{
                    success: false,
                    error: 'click_failed',
                    message: 'Failed to click button: ' + error.message
                }};
            }}
        }})();
        """
        
        try:
            result = self.browser.driver.execute_script(js_script)
            self.logger.info(f"Button click result: {result}")
            return result if isinstance(result, dict) else {"success": False, "message": "Invalid response from JS"}
        except Exception as e:
            return {
                "success": False,
                "error": "script_execution_failed",
                "message": f"Failed to execute button click script: {str(e)}"
            }
    
    def _analyze_action_result(self, result: dict, action: dict, page_info: dict) -> dict:
        """
        Analiza el resultado de una acción y proporciona retroalimentación detallada
        """
        if result.get("success", False):
            return {
                "success": True,
                "message": "Action completed successfully",
                "action": action,
                "result": result,
                "feedback": "Action executed without errors and achieved expected outcome"
            }
        
        # Analizar el tipo de error para proporcionar retroalimentación específica
        error_type = result.get("error", "unknown")
        
        feedback = {
            "success": False,
            "action": action,
            "result": result,
            "error_analysis": {},
            "suggestions": []
        }
        
        if error_type == "element_not_found":
            feedback["error_analysis"] = {
                "type": "selector_issue",
                "description": "The specified element selector could not find the target element",
                "available_alternatives": result.get("available_elements", [])
            }
            feedback["suggestions"] = [
                "Try alternative selectors",
                "Check if page has loaded completely",
                "Verify if element is dynamically created"
            ]
            
        elif error_type == "input_element_not_found":
            feedback["error_analysis"] = {
                "type": "input_selector_issue", 
                "description": "No suitable input element found for text entry",
                "available_inputs": result.get("available_inputs", [])
            }
            feedback["suggestions"] = [
                "Use generic input selectors",
                "Check for contenteditable elements",
                "Look for alternative text input methods"
            ]
            
        elif error_type == "no_button_found":
            feedback["error_analysis"] = {
                "type": "button_matching_issue",
                "description": "No button matched the specified criteria",
                "available_buttons": result.get("available_buttons", [])
            }
            feedback["suggestions"] = [
                "Use broader keyword matching",
                "Try clicking generic button selectors",
                "Check if buttons are dynamically loaded"
            ]
        
        return feedback
    
    def _try_alternative_strategies(self, original_action: dict, page_info: dict, previous_result: dict) -> dict:
        """
        Intenta estrategias alternativas cuando una acción falla
        """
        action_type = original_action.get("action", "")
        
        self.logger.info(f"Trying alternative strategies for failed action: {action_type}")
        
        if action_type == "click_element":
            return self._alternative_click_strategies(original_action, page_info, previous_result)
        elif action_type in ["enter_text", "enter_text_no_enter"]:
            return self._alternative_text_entry_strategies(original_action, page_info, previous_result)
        elif action_type == "click_button":
            return self._alternative_button_strategies(original_action, page_info, previous_result)
        
        return previous_result
    
    def _alternative_click_strategies(self, action: dict, page_info: dict, previous_result: dict) -> dict:
        """
        Estrategias alternativas para click
        """
        # Estrategia 1: Intentar con selectores genéricos
        generic_selectors = [
            "button:first-of-type",
            "input[type='submit']",
            "[role='button']:first-of-type",
            "a[href]:first-of-type"
        ]
        
        for selector in generic_selectors:
            alternative_action = {
                "action": "click_element",
                "parameters": {"selector": selector}
            }
            result = self._enhanced_click_element(selector, page_info)
            if result.get("success", False):
                result["strategy"] = f"generic_selector: {selector}"
                return result
        
        # Estrategia 2: Click por coordenadas (si tenemos información del elemento)
        available_elements = previous_result.get("available_elements", [])
        if available_elements:
            first_element = available_elements[0]
            if first_element.get("selector"):
                result = self._enhanced_click_element(first_element["selector"], page_info)
                if result.get("success", False):
                    result["strategy"] = "first_available_element"
                    return result
        
        return previous_result
    
    def _alternative_text_entry_strategies(self, action: dict, page_info: dict, previous_result: dict) -> dict:
        """
        Estrategias alternativas para entrada de texto
        """
        text = action.get("parameters", {}).get("text", "")
        press_enter = action.get("action") == "enter_text"
        
        # Estrategia 1: Probar selectores genéricos de entrada
        generic_selectors = [
            "input:first-of-type",
            "textarea:first-of-type", 
            "[contenteditable='true']:first-of-type",
            "input[type='text']:first-of-type",
            "input[type='search']:first-of-type"
        ]
        
        for selector in generic_selectors:
            result = self._enhanced_enter_text(selector, text, page_info, press_enter)
            if result.get("success", False):
                result["strategy"] = f"generic_input_selector: {selector}"
                return result
        
        # Estrategia 2: Usar el primer input disponible
        available_inputs = previous_result.get("available_inputs", [])
        if available_inputs:
            first_input = available_inputs[0]
            if first_input.get("selector"):
                result = self._enhanced_enter_text(first_input["selector"], text, page_info, press_enter)
                if result.get("success", False):
                    result["strategy"] = "first_available_input"
                    return result
        
        return previous_result
    
    def _alternative_button_strategies(self, action: dict, page_info: dict, previous_result: dict) -> dict:
        """
        Estrategias alternativas para click de botón
        """
        # Estrategia 1: Probar con keywords más genéricas
        generic_keywords = ["search", "submit", "go", "enter", "send"]
        
        result = self._enhanced_click_button(generic_keywords, page_info)
        if result.get("success", False):
            result["strategy"] = "generic_keywords"
            return result
        
        # Estrategia 2: Click en cualquier botón disponible
        available_buttons = previous_result.get("available_buttons", [])
        if available_buttons:
            # Intentar hacer click en el primer botón disponible
            result = self._enhanced_click_button([], page_info)  # Sin keywords específicas
            if result.get("success", False):
                result["strategy"] = "any_available_button"
                return result
        
        return previous_result
    
    def _update_action_history(self, action: dict, result: dict):
        """
        Actualiza el historial de acciones para evitar loops
        """
        action_signature = f"{action.get('action', '')}_{action.get('parameters', {})}"
        
        self.action_history.append({
            "timestamp": time.time(),
            "action": action,
            "result": result,
            "signature": action_signature
        })
        
        # Mantener solo las últimas 20 acciones
        if len(self.action_history) > 20:
            self.action_history = self.action_history[-20:]
        
        # Actualizar contadores de fallos
        if not result.get("success", False):
            selector = action.get("parameters", {}).get("selector", "unknown")
            self.failed_actions[selector] = self.failed_actions.get(selector, 0) + 1
    
    def get_action_feedback_for_llm(self, action: dict, result: dict) -> str:
        """
        Genera retroalimentación formateada para enviar al LLM
        """
        if result.get("success", False):
            details = result.get("details", {})
            feedback = f"""
ACTION SUCCESS: {action.get('action', '')} completed successfully.

Action Details:
- Action Type: {action.get('action', '')}
- Parameters: {action.get('parameters', {})}

Result Details:
- Success: True
- Message: {result.get('message', '')}
- Strategy Used: {result.get('strategy', 'original')}
"""
            
            if details:
                feedback += f"\nExecution Details:\n"
                for key, value in details.items():
                    feedback += f"- {key}: {value}\n"
            
            return feedback
        
        else:
            error_analysis = result.get("error_analysis", {})
            suggestions = result.get("suggestions", [])
            
            feedback = f"""
ACTION FAILED: {action.get('action', '')} was not successful.

Action Details:
- Action Type: {action.get('action', '')}
- Parameters: {action.get('parameters', {})}

Error Analysis:
- Error Type: {result.get('error', 'unknown')}
- Error Message: {result.get('message', '')}
- Description: {error_analysis.get('description', 'No detailed analysis available')}

Available Alternatives:
"""
            
            # Agregar información sobre elementos/inputs/botones disponibles
            for key in ['available_elements', 'available_inputs', 'available_buttons']:
                if key in result and result[key]:
                    feedback += f"\n{key.replace('_', ' ').title()}:\n"
                    for item in result[key][:5]:  # Limitar a 5 elementos
                        feedback += f"  - {item}\n"
            
            if suggestions:
                feedback += f"\nSuggestions for next attempt:\n"
                for suggestion in suggestions:
                    feedback += f"- {suggestion}\n"
            
            return feedback
    
    def should_skip_action_based_on_context(self, action: dict, current_state: dict) -> Tuple[bool, str]:
        """
        Determina si una acción debe omitirse basándose en el contexto actual
        """
        action_type = action.get("action", "")
        parameters = action.get("parameters", {})
        
        # Omitir búsquedas si ya estamos en resultados relevantes
        if action_type in ["enter_text", "click_element"] and current_state.get("current_page_type") == "results_page":
            if "search" in parameters.get("selector", "").lower() or "search" in parameters.get("text", "").lower():
                return True, "Already in search results page, no need to search again"
        
        # Omitir navegación si ya estamos en la página correcta
        if action_type == "navigate_to":
            target_url = parameters.get("url", "")
            current_url = current_state.get("url", "")
            if target_url in current_url or current_url in target_url:
                return True, f"Already at target page: {current_url}"
        
        return False, ""
