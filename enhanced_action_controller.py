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
        Genera retroalimentaci?n formateada para enviar al LLM
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
            
            # Agregar informaci?n sobre elementos/inputs/botones disponibles
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

    def _llm_fallback_action(self, action: dict, page_info: dict, previous_result: dict) -> dict:
        """
        Fallback usando LLM: env?a el JSON completo de la p?gina para que el LLM genere c?digo JS espec?fico
        """
        action_type = action.get("action", "")
        parameters = action.get("parameters", {})
        
        safe_print(f"[AI] [LLM_FALLBACK] Iniciando fallback con LLM para acci?n: {action_type}")
        
        # Preparar el contexto completo para el LLM
        llm_context = {
            "action_requested": action,
            "page_elements": page_info.get("interactive_elements", {}).get("elements", []),
            "page_url": page_info.get("url", ""),
            "page_title": page_info.get("title", ""),
            "previous_failure": previous_result,
            "objective": f"Generate JavaScript code to {action_type} with parameters {parameters}"
        }
        
        # Crear prompt para el LLM
        llm_prompt = f"""
TASK: Generate JavaScript code to perform the following action on a web page.

ACTION REQUESTED: {action_type}
PARAMETERS: {json.dumps(parameters, indent=2)}

AVAILABLE PAGE ELEMENTS:
{json.dumps(page_info.get("interactive_elements", {}).get("elements", [])[:20], indent=2)}

PAGE CONTEXT:
- URL: {page_info.get("url", "")}
- Title: {page_info.get("title", "")}

PREVIOUS FAILURE:
{json.dumps(previous_result, indent=2)}

CRITICAL REQUIREMENTS:
1. Return ONLY executable JavaScript code wrapped in (function() {{ ... }})();
2. The code should be robust and handle edge cases
3. Use console.log for debugging information
4. Return a result object with success status: return {{success: true/false, message: "...", details: {{...}}}}
5. For button clicks: find the most appropriate button based on the action context
6. For text input: NEVER use simple value assignment (element.value = text)
7. For text input: ALWAYS simulate real typing with proper events to trigger SPA validation
8. Handle both contenteditable and regular input elements

ENHANCED TEXT INPUT SIMULATION REQUIREMENTS:
- Clear the field first with proper selection
- Simulate realistic typing with individual keystrokes
- Fire proper events: focus, input, keydown, keyup, change, blur
- For React/Vue/Angular SPAs: dispatch input events with proper event properties
- Verify the text was actually entered and detected by the page

ENHANCED TEXT INPUT CODE TEMPLATE:
function simulateRealTyping(element, text) {{
    // Focus the element first
    element.focus();
    element.click();
    
    // Clear existing content
    element.select();
    element.setSelectionRange(0, element.value.length);
    
    // Simulate backspace to clear
    element.dispatchEvent(new KeyboardEvent('keydown', {{key: 'Backspace', bubbles: true}}));
    element.value = '';
    element.dispatchEvent(new Event('input', {{bubbles: true}}));
    
    // Type each character with proper events
    for (let i = 0; i < text.length; i++) {{
        const char = text[i];
        
        // Simulate keydown
        element.dispatchEvent(new KeyboardEvent('keydown', {{
            key: char,
            keyCode: char.charCodeAt(0),
            which: char.charCodeAt(0),
            bubbles: true
        }}));
        
        // Add the character
        element.value += char;
        
        // Simulate input event (crucial for React/Vue)
        element.dispatchEvent(new Event('input', {{
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: char
        }}));
        
        // Simulate keyup
        element.dispatchEvent(new KeyboardEvent('keyup', {{
            key: char,
            keyCode: char.charCodeAt(0),
            which: char.charCodeAt(0),
            bubbles: true
        }}));
    }}
    
    // Final events to ensure SPA detects the input
    element.dispatchEvent(new Event('change', {{bubbles: true}}));
    element.blur();
}}

EXAMPLE OUTPUT FORMAT:
(function() {{
    // ALWAYS INCLUDE THIS ENHANCED TYPING FUNCTION
    function simulateRealTyping(element, text) {{
        console.log('[ENHANCED_TYPING] Starting enhanced typing simulation for:', text.substring(0, 50));
        
        // Focus the element first
        element.focus();
        element.click();
        
        // Clear existing content with proper selection
        if (element.tagName === 'DIV' && element.contentEditable === 'true') {{
            // For contenteditable div (like X.com)
            element.selectAll && element.selectAll();
            const selection = window.getSelection();
            selection.selectAllChildren(element);
            selection.deleteFromDocument();
        }} else {{
            // For regular input/textarea
            element.select();
            element.setSelectionRange(0, element.value.length);
            element.dispatchEvent(new KeyboardEvent('keydown', {{key: 'Backspace', bubbles: true}}));
            element.value = '';
        }}
        
        // Initial input event to clear
        element.dispatchEvent(new Event('input', {{bubbles: true}}));
        
        // Type each character with realistic timing
        let currentText = '';
        for (let i = 0; i < text.length; i++) {{
            const char = text[i];
            currentText += char;
            
            // Simulate keydown
            element.dispatchEvent(new KeyboardEvent('keydown', {{
                key: char,
                keyCode: char.charCodeAt(0),
                which: char.charCodeAt(0),
                bubbles: true,
                cancelable: true
            }}));
            
            // Update content based on element type
            if (element.tagName === 'DIV' && element.contentEditable === 'true') {{
                element.textContent = currentText;
            }} else {{
                element.value = currentText;
            }}
            
            // Simulate input event (crucial for React/Vue/SPA frameworks)
            const inputEvent = new Event('input', {{
                bubbles: true,
                cancelable: true
            }});
            inputEvent.inputType = 'insertText';
            inputEvent.data = char;
            element.dispatchEvent(inputEvent);
            
            // Simulate keyup
            element.dispatchEvent(new KeyboardEvent('keyup', {{
                key: char,
                keyCode: char.charCodeAt(0),
                which: char.charCodeAt(0),
                bubbles: true
            }}));
        }}
        
        // Final events to ensure SPA frameworks detect the change
        element.dispatchEvent(new Event('change', {{bubbles: true}}));
        element.dispatchEvent(new Event('blur', {{bubbles: true}}));
        
        console.log('[ENHANCED_TYPING] Enhanced typing simulation completed');
        return true;
    }}
    
    try {{
        console.log('[LLM_ACTION] Starting {action_type}...');
        
        if ('{action_type}' === 'type_text') {{
            // Use enhanced typing simulation
            const text = {json.dumps(parameters.get('text', ''))};
            
            // Common selectors for popular sites
            const inputSelectors = [
                // X.com (Twitter) composer
                'div[data-testid="tweetTextarea_0"]',
                'div[role="textbox"][data-testid="tweetTextarea_0"]',
                'div[contenteditable="true"][data-testid="tweetTextarea_0"]',
                // Generic social media
                'div[role="textbox"][contenteditable="true"]',
                'div[contenteditable="true"][aria-multiline="true"]',
                // Regular inputs  
                'input[type="text"]', 'textarea', 
                // Fallback
                '[contenteditable="true"]', 'input', 'textarea'
            ];
            
            let element = null;
            for (const selector of inputSelectors) {{
                element = document.querySelector(selector);
                if (element && element.offsetParent !== null) break; // visible element
            }}
            
            if (element) {{
                simulateRealTyping(element, text);
                console.log('[LLM_ACTION] Enhanced typing completed on element:', element.tagName, element.getAttribute('data-testid'));
                
                // Additional verification for X.com
                if (window.location.href.includes('x.com') || window.location.href.includes('twitter.com')) {{
                    // Wait a bit for React to process
                    setTimeout(() => {{
                        const postButton = document.querySelector('[data-testid="tweetButtonInline"]') || 
                                         document.querySelector('[data-testid="tweetButton"]') ||
                                         document.querySelector('div[role="button"]:has-text("Post")');
                        if (postButton && !postButton.disabled) {{
                            console.log('[LLM_ACTION] Post button is now enabled after typing');
                        }}
                    }}, 500);
                }}
            }} else {{
                console.error('[LLM_ACTION] No suitable text input element found');
            }}
        }} else if ('{action_type}' === 'click_button') {{
            // Enhanced button clicking with better detection
            const keywords = {json.dumps(parameters.get('keywords', []))};
            const buttonSelectors = [
                // X.com specific
                '[data-testid="tweetButtonInline"]',
                '[data-testid="tweetButton"]', 
                'div[role="button"]:has-text("Post")',
                'div[role="button"]:has-text("Tweet")',
                // Generic patterns
                'button', 'input[type="submit"]', 'div[role="button"]',
                'a[role="button"]', '.btn', '.button'
            ];
            
            let targetButton = null;
            
            // Try specific selectors first
            for (const selector of buttonSelectors) {{
                const button = document.querySelector(selector);
                if (button && button.offsetParent !== null && !button.disabled) {{
                    targetButton = button;
                    break;
                }}
            }}
            
            // Fallback: search by text content
            if (!targetButton) {{
                const allButtons = document.querySelectorAll('button, div[role="button"], input[type="submit"]');
                for (const button of allButtons) {{
                    const text = button.textContent.toLowerCase().trim();
                    if (keywords.some(keyword => text.includes(keyword.toLowerCase()))) {{
                        targetButton = button;
                        break;
                    }}
                }}
            }}
            
            if (targetButton) {{
                targetButton.focus();
                targetButton.click();
                console.log('[LLM_ACTION] Successfully clicked button:', targetButton.textContent.trim());
            }}
        }}
        
        // Find and interact with elements using enhanced methods
        // Add any additional logic here based on the specific action
        
        return {{
            success: true,
            message: "Action completed successfully with enhanced simulation",
            details: {{
                element_found: true,
                action_performed: true,
                enhanced_simulation_used: true,
                action_type: '{action_type}'
            }}
        }};
    }} catch (error) {{
        console.error('[LLM_ACTION] Error:', error);
        return {{
            success: false,
            message: "Error: " + error.message,
            details: {{
                error_type: error.name,
                stack: error.stack,
                action_type: '{action_type}'
            }}
        }};
    }}
}})();

Generate the JavaScript code now:
"""
        
        try:
            # Solicitar código JavaScript al LLM
            safe_print("[AI] [LLM_FALLBACK] Solicitando código JavaScript al LLM...")
            llm_response = self.llm.ask_llm_with_context(
                llm_prompt, 
                page_context=llm_context,
                max_tokens=1500
            )
            
            if not llm_response or not llm_response.strip():
                return {
                    "success": False,
                    "message": "LLM fallback failed - empty response",
                    "fallback_used": True
                }
            
            # Limpiar la respuesta del LLM para extraer solo el c?digo JavaScript
            js_code = self._extract_js_code_from_llm_response(llm_response)
            
            if not js_code:
                return {
                    "success": False,
                    "message": "LLM fallback failed - no valid JavaScript code generated",
                    "llm_response": llm_response[:200],
                    "fallback_used": True
                }
            
            safe_print(f"[AI] [LLM_FALLBACK] Ejecutando c?digo JavaScript generado por LLM...")
            safe_print(f"[DOCUMENT] [LLM_CODE] {js_code[:200]}...")
            
            # Ejecutar el c?digo JavaScript generado por el LLM
            result = self.browser.driver.execute_script(js_code)
            
            if isinstance(result, dict):
                result["fallback_used"] = True
                result["llm_generated"] = True
                
                if result.get("success", False):
                    safe_print("[SUCCESS] [LLM_FALLBACK] C?digo LLM ejecutado exitosamente!")
                else:
                    safe_print(f"[ERROR] [LLM_FALLBACK] C?digo LLM fall?: {result.get('message', 'Unknown error')}")
                    
                return result
            else:
                return {
                    "success": False,
                    "message": f"LLM fallback returned unexpected result type: {type(result)}",
                    "result": str(result)[:100],
                    "fallback_used": True
                }
                
        except Exception as e:
            safe_print(f"[ERROR] [LLM_FALLBACK] Error en fallback con LLM: {str(e)}")
            return {
                "success": False,
                "message": f"LLM fallback exception: {str(e)}",
                "fallback_used": True,
                "error_type": type(e).__name__
            }
    
    def _extract_js_code_from_llm_response(self, llm_response: str) -> str:
        """
        Extrae el c?digo JavaScript de la respuesta del LLM
        """
        # Buscar patrones comunes de c?digo JavaScript en la respuesta
        
        # Patr?n 1: C?digo envuelto en ```javascript
        js_pattern1 = r'```(?:javascript|js)?\s*(.*?)```'
        match1 = re.search(js_pattern1, llm_response, re.DOTALL | re.IGNORECASE)
        if match1:
            return match1.group(1).strip()
        
        # Patr?n 2: Funci?n auto-ejecutable (function() { ... })();
        js_pattern2 = r'\(function\(\)\s*\{.*?\}\)\(\);'
        match2 = re.search(js_pattern2, llm_response, re.DOTALL)
        if match2:
            return match2.group(0)
        
        # Patr?n 3: Cualquier l?nea que comience con (function()
        lines = llm_response.split('\n')
        js_lines = []
        in_js_block = False
        
        for line in lines:
            if line.strip().startswith('(function()') or line.strip().startswith('function()'):
                in_js_block = True
                js_lines.append(line)
            elif in_js_block:
                js_lines.append(line)
                if '})();' in line:
                    break
        
        if js_lines:
            return '\n'.join(js_lines)
        
        # Fallback: usar toda la respuesta si contiene palabras clave JavaScript
        js_keywords = ['function', 'document.', 'console.log', 'return {', 'success:', 'try {']
        if any(keyword in llm_response for keyword in js_keywords):
            return llm_response.strip()
        
        return ""

    def execute_action_with_llm_fallback(self, action: dict, page_info: dict) -> dict:
        """
        Ejecuta una acci?n con fallback autom?tico a LLM cuando falla el m?todo program?tico
        """
        action_type = action.get("action", "")
        
        # Intentar m?todo program?tico primero
        print(f"[HYBRID] Intentando m?todo program?tico para: {action_type}")
        
        if action_type == "click_button":
            keywords = action.get("parameters", {}).get("keywords", [])
            programmatic_result = self._enhanced_click_button(keywords, page_info)
        elif action_type in ["enter_text", "enter_text_no_enter"]:
            selector = action.get("parameters", {}).get("selector", "")
            text = action.get("parameters", {}).get("text", "")
            press_enter = action_type == "enter_text"
            programmatic_result = self._enhanced_enter_text(selector, text, page_info, press_enter)
        else:
            programmatic_result = {"success": False, "message": f"Unsupported action type: {action_type}"}
        
        # Si el m?todo program?tico fue exitoso, retornar ese resultado
        if programmatic_result.get("success", False):
            safe_print(f"[SUCCESS] [HYBRID] M?todo program?tico exitoso para: {action_type}")
            programmatic_result["method_used"] = "programmatic"
            return programmatic_result
        
        # Si fall?, usar fallback con LLM
        safe_print(f"[AI] [HYBRID] M?todo program?tico fall?, usando fallback con LLM para: {action_type}")
        llm_result = self._llm_fallback_action(action, page_info, programmatic_result)
        llm_result["method_used"] = "llm_fallback"
        llm_result["programmatic_failure"] = programmatic_result
        
        return llm_result
