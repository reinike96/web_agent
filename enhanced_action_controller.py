"""
Enhanced Action Controller with intelligent feedback and error recovery
Controlador de acciones mejorado con retroalimentaci?n inteligente y recuperaci?n de errores
"""

import json
import time
import logging
import re
from typing import Dict, List, Tuple, Optional
from safe_print_utils import safe_print_global

def safe_print(text: str):
    """Safe print that handles Unicode characters that might cause encoding issues on Windows"""
    try:
        # Clean emojis and Unicode characters that cause encoding issues
        cleaned_text = str(text)
        
        # Replace common problematic emojis and Unicode characters
        emoji_replacements = {
            '[AI]': '[AI]',
            '[SUCCESS]': '[SUCCESS]',
            '[ERROR]': '[ERROR]',
            '[WARNING]': '[WARNING]',
            '[PROCESSING]': '[RELOAD]',
            '[DOCUMENT]': '[CODE]',
            '[LIST]': '[LIST]'
        }
        
        # Replace known emojis
        for emoji, replacement in emoji_replacements.items():
            cleaned_text = cleaned_text.replace(emoji, replacement)
        
        # Remove any remaining problematic Unicode characters
        cleaned_text = re.sub(r'[\U00010000-\U0010ffff]', '[EMOJI]', cleaned_text)
        
        # Final cleanup
        cleaned_text = cleaned_text.encode('utf-8', errors='replace').decode('utf-8')
        
        print(cleaned_text)
        
    except Exception as e:
        try:
            print(f"[Message with encoding issues - {str(e)}]")
        except:
            print("[Message with severe encoding issues - unable to display]")

class EnhancedActionController:
    """
    Sistema mejorado de control de acciones con:
    1. Retroalimentaci?n inteligente de scripts JS
    2. An?lisis de estado de p?gina
    3. Reintentos con estrategias diferentes
    4. Detecci?n de ?xito contextual
    """
    
    def __init__(self, browser_controller, memory, logger, llm_controller=None):
        self.browser = browser_controller
        self.memory = memory
        self.llm = llm_controller
        self.logger = logger
        
        # Historial de acciones para evitar loops
        self.action_history = []
        self.failed_actions = {}  # selector -> count
        self.page_state_cache = {}
        
    def execute_action_with_feedback(self, action: dict, page_info: dict) -> dict:
        """
        Ejecuta una acci?n con retroalimentaci?n completa del resultado
        """
        action_type = action.get("action", "")
        action_id = f"{action_type}_{int(time.time())}"
        
        self.logger.info(f"[{action_id}] Executing action: {action}")
        
        # 1. Analizar estado actual de la p?gina
        current_state = self._analyze_page_state(page_info)
        
        # 2. Verificar si la acci?n es realmente necesaria
        if self._is_action_redundant(action, current_state):
            return {
                "success": True,
                "message": "Action not needed - already in target state",
                "details": current_state,
                "skip_reason": "redundant"
            }
        
        # 3. Ejecutar la acci?n con script JS mejorado
        result = self._execute_with_enhanced_js(action, page_info)
        
        # 4. Analizar el resultado y proporcionar retroalimentaci?n
        feedback = self._analyze_action_result(result, action, page_info)
        
        # 5. Si fall?, intentar estrategias alternativas
        if not feedback.get("success", False):
            feedback = self._try_alternative_strategies(action, page_info, result)
        
        # 6. Actualizar historial
        self._update_action_history(action, feedback)
        
        return feedback
    
    def _analyze_page_state(self, page_info: dict) -> dict:
        """
        Analiza el estado actual de la p?gina para detectar contexto
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
            
            # Cajas de b?squeda
            if element_type in ["search", "text"] or "search" in text:
                state["has_search_box"] = True
                state["key_elements"].append({
                    "type": "search_box",
                    "selector": element.get("selector"),
                    "text": text
                })
            
            # Resultados de b?squeda
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
        
        # Determinar tipo de p?gina
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
        Verifica si una acci?n es redundante dado el estado actual
        """
        action_type = action.get("action", "")
        
        # Si estamos tratando de buscar pero ya estamos en resultados
        if action_type in ["click_element", "enter_text"] and current_state.get("current_page_type") == "results_page":
            # Verificar si la acci?n es para buscar
            params = action.get("parameters", {})
            selector = params.get("selector", "")
            text = params.get("text", "").lower()
            
            if "search" in selector or any(keyword in text for keyword in ["buscar", "search", "zapatillas"]):
                self.logger.info("Action redundant: already in search results page")
                return True
        
        return False
    
    def _execute_with_enhanced_js(self, action: dict, page_info: dict) -> dict:
        """
        Ejecuta la acci?n usando scripts JS mejorados con retroalimentaci?n detallada
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
            # Fallback al m?todo original del browser_controller
            return {"success": False, "message": f"Action type {action_type} not implemented in enhanced controller"}
    
    def _enhanced_click_element(self, selector: str, page_info: dict) -> dict:
        """
        Click mejorado con retroalimentaci?n detallada
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
                        // M?s selectores alternativos basados en el selector original
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
                
                // Paso 4: Verificar el resultado despu?s de un tiempo (sin await)
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
        Enhanced text entry with improved typing simulation and verification
        """
        print(f"[ENHANCED_TEXT] Starting enhanced text entry for selector: {selector}")
        print(f"[ENHANCED_TEXT] Text to enter: '{text}'")
        print(f"[ENHANCED_TEXT] Press enter: {press_enter}")
        
        try:
            # Use the improved browser controller method
            success = self.browser.enter_text_without_enter(selector, text) if not press_enter else self.browser.enter_text(selector, text, press_enter=True)
            
            if success:
                print("[ENHANCED_TEXT] Text entry completed, verifying input detection...")
                
                # Use enhanced verification
                input_detected = self.browser.verify_text_input_detected(selector, text, timeout=5)
                
                # Provide detailed feedback
                feedback = {
                    "success": True,
                    "action_type": "enter_text",
                    "selector_used": selector,
                    "text_entered": text,
                    "input_detected": input_detected,
                    "message": f"Successfully entered text '{text}' using enhanced typing simulation",
                    "verification": "[SUCCESS] Input verified by page" if input_detected else "[WARNING] Input verification inconclusive"
                }
                
                if input_detected:
                    safe_print("[SUCCESS] Enhanced text entry successful - page detected the input")
                else:
                    safe_print("[WARNING] Text entered but page detection uncertain - continuing")
                    
            else:
                feedback = {
                    "success": False,
                    "action_type": "enter_text",
                    "selector_used": selector,
                    "error": "Failed to enter text using enhanced method",
                    "message": f"Could not enter text '{text}' in element with selector '{selector}'"
                }
                safe_print("[ERROR] Enhanced text entry failed")
            
            return feedback
            
        except Exception as e:
            error_feedback = {
                "success": False,
                "action_type": "enter_text", 
                "selector_used": selector,
                "error": str(e),
                "message": f"Exception during enhanced text entry: {str(e)}"
            }
            safe_print(f"[ERROR] Exception during enhanced text entry: {e}")
            return error_feedback
    
    def _enhanced_click_button(self, keywords: List[str], page_info: dict) -> dict:
        """
        Click de bot?n mejorado buscando por palabras clave
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
            
            // Buscar bot?n que coincida con las palabras clave
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
                // Fallback: tomar el primer bot?n visible
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
        Analiza el resultado de una acci?n y proporciona retroalimentaci?n detallada
        """
        if result.get("success", False):
            return {
                "success": True,
                "message": "Action completed successfully",
                "action": action,
                "result": result,
                "feedback": "Action executed without errors and achieved expected outcome"
            }
        
        # Analizar el tipo de error para proporcionar retroalimentaci?n espec?fica
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
        Intenta estrategias alternativas cuando una acci?n falla
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
        # Estrategia 1: Intentar con selectores gen?ricos
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
        
        # Estrategia 2: Click por coordenadas (si tenemos informaci?n del elemento)
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
        
        # Estrategia 1: Probar selectores gen?ricos de entrada
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
        Estrategias alternativas para click de bot?n
        """
        # Estrategia 1: Probar con keywords m?s gen?ricas
        generic_keywords = ["search", "submit", "go", "enter", "send"]
        
        result = self._enhanced_click_button(generic_keywords, page_info)
        if result.get("success", False):
            result["strategy"] = "generic_keywords"
            return result
        
        # Estrategia 2: Click en cualquier bot?n disponible
        available_buttons = previous_result.get("available_buttons", [])
        if available_buttons:
            # Intentar hacer click en el primer bot?n disponible
            result = self._enhanced_click_button([], page_info)  # Sin keywords espec?ficas
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
        
        # Mantener solo las ?ltimas 20 acciones
        if len(self.action_history) > 20:
            self.action_history = self.action_history[-20:]
        
        # Actualizar contadores de fallos
        if not result.get("success", False):
            selector = action.get("parameters", {}).get("selector", "unknown")
            self.failed_actions[selector] = self.failed_actions.get(selector, 0) + 1
    
    def get_action_feedback_for_llm(self, action: dict, result: dict) -> str:
        """
        Genera retroalimentación formateada limitada para enviar al LLM
        Limita la cantidad de información para evitar sobrecargar tokens
        """
        def truncate_text(text: str, max_length: int = 200) -> str:
            """Trunca texto preservando información clave"""
            if len(text) <= max_length:
                return text
            return text[:max_length] + "..."
        
        if result.get("success", False):
            feedback = f"""
ACTION SUCCESS: {action.get('action', '')} completed successfully.
- Strategy: {result.get('strategy', 'original')}
- Message: {truncate_text(result.get('message', ''), 150)}
"""
            return feedback
        
        else:
            error_analysis = result.get("error_analysis", {})
            suggestions = result.get("suggestions", [])
            
            feedback = f"""
ACTION FAILED: {action.get('action', '')} unsuccessful.
- Error: {result.get('error', 'unknown')}
- Message: {truncate_text(result.get('message', ''), 150)}
- Analysis: {truncate_text(error_analysis.get('description', 'No analysis'), 150)}
"""
            
            # Limitar elementos disponibles a máximo 3 por categoría
            for key in ['available_elements', 'available_inputs', 'available_buttons']:
                if key in result and result[key]:
                    items = result[key][:3]  # Solo 3 elementos
                    feedback += f"\n{key.replace('_', ' ').title()} ({len(result[key])} total):\n"
                    for item in items:
                        item_text = truncate_text(str(item), 80)
                        feedback += f"  - {item_text}\n"
            
            # Limitar sugerencias
            if suggestions:
                feedback += f"\nSuggestions ({len(suggestions)} total):\n"
                for suggestion in suggestions[:3]:  # Solo 3 sugerencias
                    feedback += f"- {truncate_text(suggestion, 100)}\n"
            
            return feedback
    
    def should_skip_action_based_on_context(self, action: dict, current_state: dict) -> Tuple[bool, str]:
        """
        Determina si una acci?n debe omitirse bas?ndose en el contexto actual
        """
        action_type = action.get("action", "")
        parameters = action.get("parameters", {})
        
        # Omitir b?squedas si ya estamos en resultados relevantes
        if action_type in ["enter_text", "click_element"] and current_state.get("current_page_type") == "results_page":
            if "search" in parameters.get("selector", "").lower() or "search" in parameters.get("text", "").lower():
                return True, "Already in search results page, no need to search again"
        
        # Omitir navegaci?n si ya estamos en la p?gina correcta
        if action_type == "navigate_to":
            target_url = parameters.get("url", "")
            current_url = current_state.get("url", "")
            if target_url in current_url or current_url in target_url:
                return True, f"Already at target page: {current_url}"
        
        return False, ""

    def _enhanced_click_button_with_extracted_elements(self, keywords: List[str], elements: List[dict], page_context: dict) -> dict:
        """
        Click de botón mejorado usando elementos extraídos dinámicamente
        """
        safe_print(f"[PROGRAMMATIC] Buscando botón con keywords {keywords} en {len(elements)} elementos")
        
        try:
            # Buscar botones que coincidan con las palabras clave
            matching_buttons = []
            
            for element in elements:
                if element.get("tag") not in ["button", "input"]:
                    continue
                    
                # Obtener texto del elemento
                text = element.get("text", "").lower() if element.get("text") else ""
                aria_label = element.get("aria-label", "").lower() if element.get("aria-label") else ""
                data_testid = element.get("data-testid", "").lower() if element.get("data-testid") else ""
                placeholder = element.get("placeholder", "").lower() if element.get("placeholder") else ""
                
                search_text = f"{text} {aria_label} {data_testid} {placeholder}".strip()
                
                # Verificar si coincide con alguna keyword (más flexible)
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if (keyword_lower in search_text or 
                        # Búsquedas específicas para X.com
                        (keyword_lower == "post" and ("publicar" in search_text or "tweet" in search_text)) or
                        (keyword_lower == "tweet" and ("post" in search_text or "publicar" in search_text)) or
                        # Búsquedas por funcionalidad
                        (keyword_lower in ["post", "tweet"] and "compose" in data_testid)):
                        matching_buttons.append({
                            "element": element,
                            "keyword": keyword,
                            "match_text": search_text
                        })
                        break
            
            # Si no se encontraron keywords específicas, buscar botones genéricos de acción
            if not matching_buttons and not keywords:
                safe_print("[PROGRAMMATIC] No keywords específicas, buscando cualquier botón de acción...")
                for element in elements:
                    if element.get("tag") in ["button", "input"]:
                        text = element.get("text", "").lower() if element.get("text") else ""
                        aria_label = element.get("aria-label", "").lower() if element.get("aria-label") else ""
                        
                        # Buscar botones con texto que sugiera acción
                        action_words = ["submit", "send", "post", "publicar", "tweet", "enviar", "confirmar", "siguiente", "next"]
                        if any(word in f"{text} {aria_label}" for word in action_words):
                            matching_buttons.append({
                                "element": element,
                                "keyword": "generic_action",
                                "match_text": f"{text} {aria_label}".strip()
                            })
            
            if not matching_buttons:
                return {
                    "success": False,
                    "message": f"No button found matching keywords: {keywords}",
                    "available_buttons": [{"text": e.get("text"), "selector": e.get("selector"), "aria-label": e.get("aria-label")} for e in elements if e.get("tag") in ["button", "input"]][:5]
                }
            
            # Usar el primer botón que coincida
            target_button = matching_buttons[0]
            selector = target_button["element"]["selector"]
            
            safe_print(f"[PROGRAMMATIC] Haciendo clic en botón: {target_button['element']['text']} -> {selector}")
            
            # Ejecutar el clic usando el selector extraído
            js_script = f"""
            (function() {{
                const element = document.querySelector('{selector}');
                if (element) {{
                    element.click();
                    return {{success: true, message: "Button clicked successfully", selector: '{selector}'}};
                }} else {{
                    return {{success: false, message: "Element not found with selector: {selector}"}};
                }}
            }})();
            """
            
            result = self.browser.driver.execute_script(js_script)
            
            # Log the programmatic code used
            success = result.get("success", False) if isinstance(result, dict) else False
            self.llm.log_action_code("click_button", "PROGRAMMATIC", js_script, success)
            
            return result if isinstance(result, dict) else {"success": False, "message": "Invalid response from click script"}
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Exception in programmatic button click: {str(e)}"
            }

    def _enhanced_click_element_with_extracted_elements(self, selector: str, elements: List[dict], page_context: dict) -> dict:
        """
        Click de elemento usando selector y elementos extraídos para validación
        """
        safe_print(f"[PROGRAMMATIC] Haciendo clic en elemento con selector: {selector}")
        
        try:
            # Verificar si el selector existe en los elementos extraídos
            element_found = any(e.get("selector") == selector for e in elements)
            
            if not element_found:
                return {
                    "success": False,
                    "message": f"Selector not found in extracted elements: {selector}",
                    "available_selectors": [e.get("selector") for e in elements[:5]]
                }
            
            # Ejecutar el clic
            js_script = f"""
            (function() {{
                const element = document.querySelector('{selector}');
                if (element) {{
                    element.click();
                    return {{success: true, message: "Element clicked successfully", selector: '{selector}'}};
                }} else {{
                    return {{success: false, message: "Element not found with selector: {selector}"}};
                }}
            }})();
            """
            
            result = self.browser.driver.execute_script(js_script)
            
            # Log the programmatic code used
            success = result.get("success", False) if isinstance(result, dict) else False
            self.llm.log_action_code("click_element", "PROGRAMMATIC", js_script, success)
            
            return result if isinstance(result, dict) else {"success": False, "message": "Invalid response from click script"}
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Exception in programmatic element click: {str(e)}"
            }

    def _enhanced_enter_text_with_extracted_elements(self, selector: str, text: str, elements: List[dict], page_context: dict, press_enter: bool = True) -> dict:
        """
        Entrada de texto usando elementos extraídos para encontrar campos editables
        """
        safe_print(f"[PROGRAMMATIC] Ingresando texto en selector: {selector}")
        
        try:
            # Buscar elemento editable que coincida
            target_element = None
            
            # Si no se especifica selector, buscar campo editable
            if not selector:
                for element in elements:
                    if element.get("contenteditable") or element.get("tag") in ["input", "textarea"]:
                        target_element = element
                        selector = element.get("selector")
                        break
            else:
                # PRIMERA OPCIÓN: Verificar que el selector exacto existe en elementos extraídos
                target_element = next((e for e in elements if e.get("selector") == selector), None)
                
                # SEGUNDA OPCIÓN: Si no hay coincidencia exacta, buscar por data-testid
                if not target_element and "data-testid" in selector:
                    # Extraer data-testid del selector (ej: div[data-testid="tweetTextarea_0"] -> tweetTextarea_0)
                    testid_match = re.search(r'data-testid[=\'\"]*([^\'\"\]]+)', selector)
                    if testid_match:
                        target_testid = testid_match.group(1)
                        target_element = next((e for e in elements if e.get("data-testid") == target_testid), None)
                        if target_element:
                            selector = target_element.get("selector")  # Usar el selector extraído
                            safe_print(f"[PROGRAMMATIC] Encontrado elemento por data-testid: {target_testid} -> {selector}")
                
                # TERCERA OPCIÓN: Si sigue sin encontrar y es contenteditable, buscar cualquier contenteditable
                if not target_element and "contenteditable" in selector.lower():
                    target_element = next((e for e in elements if e.get("contenteditable")), None)
                    if target_element:
                        selector = target_element.get("selector")  # Usar el selector extraído
                        safe_print(f"[PROGRAMMATIC] Encontrado elemento contenteditable: {selector}")
            
            if not target_element:
                return {
                    "success": False,
                    "message": f"No editable element found with selector: {selector}",
                    "editable_elements": [{"text": e.get("text"), "selector": e.get("selector")} for e in elements if e.get("contenteditable") or e.get("tag") in ["input", "textarea"]][:3]
                }
            
            # Determinar el tipo de elemento para usar la estrategia correcta
            is_contenteditable = target_element.get("contenteditable")
            
            if is_contenteditable:
                # Usar método especial para contenteditable con paste simulation
                js_script = f"""
                (function() {{
                    const element = document.querySelector('{selector}');
                    if (!element) {{
                        return {{success: false, message: "Element not found"}};
                    }}
                    
                    function simulatePaste(el, text) {{
                        // Focus and select all existing content
                        el.focus();
                        el.click();
                        
                        const selection = window.getSelection();
                        selection.selectAllChildren(el);
                        selection.deleteFromDocument();
                        
                        // Create paste event
                        const pasteEvent = new ClipboardEvent("paste", {{
                            bubbles: true,
                            cancelable: true,
                            clipboardData: new DataTransfer()
                        }});
                        
                        pasteEvent.clipboardData.setData("text/plain", text);
                        
                        // Dispatch paste event
                        el.dispatchEvent(pasteEvent);
                        
                        // Fallback: set text directly if paste event didn't work
                        if (!el.textContent || el.textContent.trim() === '') {{
                            el.textContent = text;
                        }}
                        
                        // Dispara eventos para que frameworks lo detecten
                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                        el.dispatchEvent(new Event('blur', {{bubbles: true}}));
                    }}
                    
                    simulatePaste(element, '{text}');
                    
                    return {{success: true, message: "Text pasted successfully in contenteditable", selector: '{selector}'}};
                }})();
                """
            else:
                # Usar método mejorado con paste simulation para input/textarea
                enter_key = "element.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));" if press_enter else ""
                js_script = f"""
                (function() {{
                    const element = document.querySelector('{selector}');
                    if (!element) {{
                        return {{success: false, message: "Element not found"}};
                    }}
                    
                    function simulatePaste(el, text) {{
                        el.focus();
                        
                        // Select all existing content
                        el.select();
                        
                        // Create paste event
                        const pasteEvent = new ClipboardEvent("paste", {{
                            bubbles: true,
                            cancelable: true,
                            clipboardData: new DataTransfer()
                        }});
                        
                        pasteEvent.clipboardData.setData("text/plain", text);
                        
                        // Dispatch paste event
                        el.dispatchEvent(pasteEvent);
                        
                        // Fallback: set value directly if paste event didn't work
                        if (!el.value || el.value.trim() === '') {{
                            el.value = text;
                        }}
                        
                        // Dispara eventos para que frameworks lo detecten (importante para React/Vue/Angular)
                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                        el.dispatchEvent(new Event('blur', {{bubbles: true}}));
                    }}
                    
                    simulatePaste(element, '{text}');
                    
                    {enter_key}
                    
                    return {{success: true, message: "Text pasted successfully", selector: '{selector}'}};
                }})();
                """
            
            result = self.browser.driver.execute_script(js_script)
            
            # Log the programmatic code used
            success = result.get("success", False) if isinstance(result, dict) else False
            action_name = "enter_text" if press_enter else "enter_text_no_enter"
            self.llm.log_action_code(action_name, "PROGRAMMATIC", js_script, success)
            
            return result if isinstance(result, dict) else {"success": False, "message": "Invalid response from text entry script"}
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Exception in programmatic text entry: {str(e)}"
            }

    def _llm_action_with_verification(self, action: dict, current_elements: dict, original_goal: str = "") -> dict:
        """
        Ejecuta acción con LLM y verificación automática de éxito.
        El LLM debe generar código que incluya verificación de éxito.
        """
        action_type = action.get("action", "")
        parameters = action.get("parameters", {})
        elements = current_elements.get("elements", [])
        
        safe_print(f"[AI] [LLM] Iniciando ejecución LLM con verificación para: {action_type}")
        safe_print(f"[DEBUG] [LLM] Elementos disponibles: {len(elements)}")
        
        try:
            # PASO 1: Crear prompt con enfoque en verificación de éxito
            current_action_description = f"Perform {action_type} with parameters: {parameters}"
            
            llm_prompt = f"""
OVERALL GOAL: {original_goal if original_goal else "Web automation task"}

TASK: Generate JavaScript code that performs an action AND verifies its success.

ACTION TO PERFORM: {action_type}
ACTION PARAMETERS: {json.dumps(parameters, indent=2)}

AVAILABLE PAGE ELEMENTS (live from current page):
{json.dumps(elements, indent=2)}

PAGE CONTEXT:
- URL: {current_elements.get("url", "")}
- Title: {current_elements.get("title", "")}

CRITICAL REQUIREMENTS:
1. Your JavaScript code must include BOTH action execution AND success verification
2. Use ONLY selectors from the AVAILABLE PAGE ELEMENTS above
3. For text input: Use the simulatePaste() function provided below (copy the entire function)
4. For clicks: Use element.click() on the exact selectors provided
5. MUST return object with success:true/false and verification details
6. Code must verify the action actually worked (text was entered, button was clicked, etc.)
7. INCLUDE the simulatePaste function definition in your code - do not just call it

COMPLETE SIMULATEPASTE FUNCTION (copy this entire function into your code):
function simulatePaste(element, text) {{
    element.focus();
    
    // STEP 1: Clear ALL existing content completely
    if (element.tagName === 'DIV' && element.contentEditable === 'true') {{
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
        while (element.firstChild) {{
            element.removeChild(element.firstChild);
        }}
    }} else {{
        // For input/textarea elements
        element.select();
        element.value = '';
    }}
    
    // STEP 2: Insert new text using paste event
    const pasteEvent = new ClipboardEvent("paste", {{
        bubbles: true,
        cancelable: true,
        clipboardData: new DataTransfer()
    }});
    
    pasteEvent.clipboardData.setData("text/plain", text);
    element.dispatchEvent(pasteEvent);
    
    // STEP 3: Fallback if paste event didn't work
    if (element.tagName === 'DIV' && element.contentEditable === 'true') {{
        if (!element.textContent || element.textContent.trim() === '') {{
            element.textContent = text;
        }}
    }} else {{
        if (!element.value || element.value.trim() === '') {{
            element.value = text;
        }}
    }}
    
    // STEP 4: Trigger events for framework detection
    element.dispatchEvent(new Event('input', {{bubbles: true}}));
    element.dispatchEvent(new Event('change', {{bubbles: true}}));
    element.dispatchEvent(new Event('blur', {{bubbles: true}}));
}}

VERIFICATION EXAMPLES:
- For text input: Check if element.textContent or element.value contains the entered text
- For button clicks: Check if page changed, new elements appeared, or button state changed
- For navigation: Check if URL changed

RESPONSE FORMAT (MANDATORY - your code MUST return this exact structure):
// Include simulatePaste function definition first
function simulatePaste(element, text) {{ /* full function above */ }}

// Your action code here (NO IIFE wrapper needed)

// MANDATORY: Always return this object structure at the end
return {{
    success: true/false,
    message: "Description of what happened",
    action_performed: "{action_type}",
    verification_details: {{
        expected: "what was expected to happen",
        actual: "what actually happened",  
        element_found: true/false,
        action_completed: true/false
    }},
    debug_info: {{
        selector_used: "actual selector used",
        element_text: "element text content if applicable"
    }}
}};

IMPORTANT: 
- Do NOT wrap your code in (function() {{}})(); - use direct execution
- Your JavaScript code must ALWAYS end with a return statement
- Do NOT use setTimeout or async operations - execute everything synchronously
"""
            
            # PASO 2: Solicitar código JavaScript al LLM
            safe_print("[AI] [LLM] Solicitando código JavaScript con verificación al LLM...")
            llm_response = self.llm.ask_llm_with_context(
                llm_prompt,
                page_context={
                    "overall_goal": original_goal,
                    "current_action": action,
                    "available_elements": elements,
                    "page_url": current_elements.get("url", ""),
                    "page_title": current_elements.get("title", "")
                }
            )
            
            if not llm_response or not llm_response.strip():
                return {
                    "success": False,
                    "message": "LLM failed to generate code - empty response",
                    "method_used": "llm_only"
                }
            
            # PASO 3: Extraer y ejecutar el código JavaScript
            js_code = self._extract_js_code_from_llm_response(llm_response)
            
            if not js_code:
                return {
                    "success": False,
                    "message": "LLM failed to generate valid JavaScript code",
                    "llm_response": llm_response[:200],
                    "method_used": "llm_only"
                }
            
            safe_print(f"[AI] [LLM] Ejecutando código JavaScript con verificación...")
            safe_print(f"[CODE] {js_code[:200]}...")
            
            # PASO 4: Ejecutar el código generado
            result = self.browser.driver.execute_script(js_code)
            
            # PASO 5: Procesar resultado con verificación
            if result is None:
                safe_print("[WARNING] [LLM] JavaScript code returned None - assuming success")
                result = {
                    "success": True,
                    "message": "JavaScript executed but returned no verification data",
                    "verification_details": {"note": "No verification data returned"}
                }
            
            if isinstance(result, dict):
                result["method_used"] = "llm_only"
                result["elements_used"] = len(elements)
                result["original_goal"] = original_goal
                
                success = result.get("success", False)
                verification = result.get("verification_details", {})
                
                # Log the LLM code used for this action
                self.llm.log_action_code(action_type, "LLM_ONLY", js_code, success)
                
                if success:
                    safe_print("[SUCCESS] [LLM] Código LLM ejecutado exitosamente con verificación!")
                    safe_print(f"[SUCCESS] Verificación: {verification.get('expected', 'N/A')} -> {verification.get('actual', 'N/A')}")
                else:
                    safe_print(f"[ERROR] [LLM] Código LLM falló verificación: {result.get('message', 'Unknown error')}")
                    safe_print(f"[ERROR] Detalles: {verification}")
                    
                return result
            else:
                # Log failed LLM attempt
                self.llm.log_action_code(action_type, "LLM_ONLY", js_code, False)
                return {
                    "success": False,
                    "message": f"LLM returned unexpected result type: {type(result)}",
                    "result": str(result)[:100],
                    "method_used": "llm_only",
                    "js_code": js_code[:200]
                }
                
        except Exception as e:
            safe_print(f"[ERROR] [LLM] Error en ejecución LLM: {str(e)}")
            return {
                "success": False,
                "message": f"LLM execution exception: {str(e)}",
                "method_used": "llm_only"
            }
    def _llm_fallback_action_backup(self, action: dict, current_elements: dict, previous_result: dict, original_goal: str = "") -> dict:
        action_type = action.get("action", "")
        parameters = action.get("parameters", {})
        elements = current_elements.get("elements", [])
        
        safe_print(f"[AI] [LLM_FALLBACK] Iniciando fallback universal para acción: {action_type}")
        safe_print(f"[DEBUG] [LLM_FALLBACK] Elementos disponibles: {len(elements)}")
        
        try:
            # PASO 1: Crear prompt enriquecido con goal original y contexto completo
            current_action_description = f"Perform {action_type} with parameters: {parameters}"
            
            llm_prompt = f"""
OVERALL GOAL: {original_goal if original_goal else "Not specified"}

CURRENT TASK: Generate JavaScript code to perform a single action on a web page.

CURRENT ACTION: {action_type}
PARAMETERS: {json.dumps(parameters, indent=2)}

AVAILABLE PAGE ELEMENTS (extracted live from current page):
{json.dumps(elements, indent=2)}

PAGE CONTEXT:
- URL: {current_elements.get("url", "")}
- Title: {current_elements.get("title", "")}

PREVIOUS PROGRAMMATIC ATTEMPT FAILED:
{previous_result.get("message", "Unknown error")}

REQUIREMENTS:
1. You have COMPLETE FREEDOM to generate any JavaScript code needed
2. NO keyword matching required - analyze the goal and elements intelligently
3. Use ONLY the selectors provided in AVAILABLE PAGE ELEMENTS above
4. Return ONLY executable JavaScript code wrapped in (function() {{ ... }})();
5. For text input: Use proper event simulation with bubbles:true for framework compatibility
6. For clicks: Use the exact selectors from the available elements
7. Consider the OVERALL GOAL when deciding which elements to interact with
8. Return result object: return {{success: true/false, message: "...", details: {{...}}}}

ENHANCED TYPING FUNCTION (use for ALL text input - handles React/Vue/Angular frameworks):
function simulatePaste(element, text) {{
    element.focus();
    
    if (element.tagName === 'DIV' && element.contentEditable === 'true') {{
        // For contenteditable elements
        element.click();
        const selection = window.getSelection();
        selection.selectAllChildren(element);
        selection.deleteFromDocument();
    }} else {{
        // For input/textarea elements
        element.select();
    }}
    
    // Create paste event with clipboard data
    const pasteEvent = new ClipboardEvent("paste", {{
        bubbles: true,
        cancelable: true,
        clipboardData: new DataTransfer()
    }});
    
    pasteEvent.clipboardData.setData("text/plain", text);
    
    // Dispatch the paste event
    element.dispatchEvent(pasteEvent);
    
    // Fallback: set content directly if paste event didn't work
    if (element.tagName === 'DIV' && element.contentEditable === 'true') {{
        if (!element.textContent || element.textContent.trim() === '') {{
            element.textContent = text;
        }}
    }} else {{
        if (!element.value || element.value.trim() === '') {{
            element.value = text;
        }}
    }}
    
    // CRITICAL: Dispara eventos para que frameworks lo detecten
    element.dispatchEvent(new Event('input', {{bubbles: true}}));
    element.dispatchEvent(new Event('change', {{bubbles: true}}));
    element.dispatchEvent(new Event('blur', {{bubbles: true}}));
}}

CONTEXT FOR INTELLIGENT DECISION MAKING:
- Overall Goal: {original_goal}
- Current Action: {current_action_description}
- Available Elements Count: {len(elements)}
- Page: {current_elements.get("title", "")}

Generate the most appropriate JavaScript code to accomplish this action within the context of the overall goal.
IMPORTANT: Always use simulatePaste() for text input to ensure maximum framework compatibility.
"""
            
            # PASO 2: Solicitar código JavaScript al LLM
            safe_print("[AI] [LLM_FALLBACK] Solicitando código JavaScript específico al LLM...")
            llm_response = self.llm.ask_llm_with_context(
                llm_prompt,
                page_context={
                    "overall_goal": original_goal,
                    "current_action": action,
                    "available_elements": elements,
                    "page_url": current_elements.get("url", ""),
                    "page_title": current_elements.get("title", ""),
                    "programmatic_failure": previous_result
                }
            )
            
            if not llm_response or not llm_response.strip():
                return {
                    "success": False,
                    "message": "LLM fallback failed - empty response",
                    "fallback_used": True
                }
            
            # PASO 3: Extraer y ejecutar el código JavaScript
            js_code = self._extract_js_code_from_llm_response(llm_response)
            
            if not js_code:
                return {
                    "success": False,
                    "message": "LLM fallback failed - no valid JavaScript code generated",
                    "llm_response": llm_response[:200],
                    "fallback_used": True
                }
            
            safe_print(f"[AI] [LLM_FALLBACK] Ejecutando código JavaScript generado...")
            safe_print(f"[CODE] {js_code[:200]}...")
            
            # PASO 4: Ejecutar el código generado
            result = self.browser.driver.execute_script(js_code)
            
            # Manejar caso donde el resultado es None
            if result is None:
                safe_print("[WARNING] [LLM_FALLBACK] JavaScript code returned None - assuming success")
                result = {
                    "success": True,
                    "message": "JavaScript executed but returned no value (assuming success)",
                    "result_type": "None"
                }
            
            if isinstance(result, dict):
                result["fallback_used"] = True
                result["llm_generated"] = True
                result["elements_used"] = len(elements)
                result["original_goal"] = original_goal
                
                success = result.get("success", False)
                
                # Log the LLM code used for this action
                self.llm.log_action_code(action_type, "LLM_FALLBACK", js_code, success)
                
                if success:
                    safe_print("[SUCCESS] [LLM_FALLBACK] Código LLM ejecutado exitosamente!")
                else:
                    safe_print(f"[ERROR] [LLM_FALLBACK] Código LLM falló: {result.get('message', 'Unknown error')}")
                    
                return result
            else:
                # Log failed LLM attempt
                self.llm.log_action_code(action_type, "LLM_FALLBACK", js_code, False)
                return {
                    "success": False,
                    "message": f"LLM fallback returned unexpected result type: {type(result)}",
                    "result": str(result)[:100],
                    "fallback_used": True,
                    "js_code": js_code[:200]  # Include some JS code for debugging
                }
                
        except Exception as e:
            safe_print(f"[ERROR] [LLM_FALLBACK] Error en fallback universal: {str(e)}")
            return {
                "success": False,
                "message": f"LLM fallback exception: {str(e)}",
                "fallback_used": True
            }
    def _extract_js_code_from_llm_response(self, llm_response: str) -> str:
        """
        Extrae el código JavaScript de la respuesta del LLM (sin IIFE)
        """
        # Buscar patrones comunes de código JavaScript en la respuesta
        
        # Patrón 1: Código envuelto en ```javascript
        js_pattern1 = r'```(?:javascript|js)?\s*(.*?)```'
        match1 = re.search(js_pattern1, llm_response, re.DOTALL | re.IGNORECASE)
        if match1:
            return match1.group(1).strip()
        
        # Patrón 2: Función auto-ejecutable (function() { ... })(); - convertir a código directo
        js_pattern2 = r'\(function\(\)\s*\{(.*?)\}\)\(\);'
        match2 = re.search(js_pattern2, llm_response, re.DOTALL)
        if match2:
            # Extraer solo el contenido de la función, sin el wrapper IIFE
            return match2.group(1).strip()
        
        # Patrón 3: Buscar código que empiece con function definition y termine con return
        lines = llm_response.split('\n')
        js_lines = []
        collecting = False
        
        for line in lines:
            line_stripped = line.strip()
            # Empezar a recoger cuando vemos function definition o código directo
            if (line_stripped.startswith('function simulatePaste') or 
                line_stripped.startswith('const ') or 
                line_stripped.startswith('let ') or
                line_stripped.startswith('var ') or
                line_stripped.startswith('//')):
                collecting = True
                js_lines.append(line)
            elif collecting:
                js_lines.append(line)
                # Parar cuando encontremos el return final
                if line_stripped.startswith('return {') and '};' in line:
                    break
        
        if js_lines:
            return '\n'.join(js_lines)
        
        # Fallback: buscar cualquier código que contenga return y función simulatePaste
        if 'function simulatePaste' in llm_response and 'return {' in llm_response:
            # Encontrar desde function hasta el último return
            start_idx = llm_response.find('function simulatePaste')
            end_idx = llm_response.rfind('};')
            if start_idx != -1 and end_idx != -1:
                return llm_response[start_idx:end_idx + 2]
        
        # Último recurso: usar toda la respuesta si contiene palabras clave
        js_keywords = ['function', 'document.', 'console.log', 'return {', 'success:', 'querySelector']
        if any(keyword in llm_response for keyword in js_keywords):
            return llm_response.strip()
        
        return ""

    def execute_action_with_llm_fallback(self, action: dict, page_info: dict, original_goal: str = "") -> dict:
        """
        Ejecuta una acción usando SOLO el método LLM con elementos extraídos dinámicamente.
        Se eliminó el método programático ya que no funcionaba correctamente.
        """
        action_type = action.get("action", "")
        
        safe_print(f"[LLM] Iniciando ejecución con LLM para: {action_type}")
        
        # PASO 1: Extraer elementos actuales de la página
        try:
            safe_print("[LLM] Extrayendo elementos actuales de la página...")
            js_file_path = r"c:\Users\ALEXR\OneDrive\Desktop\Browser\web_agent\extractJsonInteractive_simple.js"
            
            with open(js_file_path, 'r', encoding='utf-8') as file:
                extraction_js = file.read()
            
            # Add "return" to ensure the IIFE returns the value to Selenium
            extraction_js_with_return = "return " + extraction_js
            current_elements = self.browser.driver.execute_script(extraction_js_with_return)
            
            if not current_elements or not current_elements.get("elements"):
                safe_print("[WARNING] [LLM] No se pudieron extraer elementos de la página")
                return {
                    "success": False,
                    "message": "Failed to extract page elements for action execution",
                    "method_used": "llm_only"
                }
            
            elements = current_elements.get("elements", [])
            safe_print(f"[DEBUG] [LLM] Elementos extraídos: {len(elements)}")
            
        except Exception as e:
            safe_print(f"[ERROR] [LLM] Error extrayendo elementos: {e}")
            return {
                "success": False,
                "message": f"Element extraction failed: {str(e)}",
                "method_used": "llm_only"
            }
        
        # PASO 2: Ejecutar directamente con LLM usando elementos extraídos
        safe_print(f"[LLM] Ejecutando acción con LLM: {action_type}")
        llm_result = self._llm_action_with_verification(action, current_elements, original_goal)
        llm_result["method_used"] = "llm_only"
        llm_result["elements_used"] = len(elements)
        
        return llm_result
