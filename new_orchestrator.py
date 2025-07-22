import time
import os
from typing import Dict, List
from browser_controller import BrowserController
from page_analyzer import PageAnalyzer
from llm_controller import LLMController
from memory import Memory
from manual_intervention import ManualInterventionDialog
from data_extraction_agent import DataExtractionAgent
from text_processor_agent import TextProcessorAgent
from enhanced_action_controller import EnhancedActionController
from content_processor import ContentProcessor
from file_generator import FileGenerator

class NewOrchestrator:
    """            elif action_name == "click_element":
                selector = params.get("selector", "")
                return self.browser.click_element(selector)
            
            elif action_name == "click_button":
                # General action to click relevant buttons using JSON data
                keywords = params.get("keywords", None)  # Optional: specific keywords to search for
                page_info = self.page_analyzer.get_comprehensive_page_info()
                return self.browser.click_button_from_json(page_info, keywords)  New orchestrator with improved architecture based on JavaScript extraction and robust validation.
    """
    
    def __init__(self, goal: str, message_callback: callable = None):
        self.goal = goal
        self.message_callback = message_callback
        self.browser = BrowserController()
        
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key or groq_api_key == "YOUR_API_KEY_HERE":
            raise ValueError("GROQ_API_KEY not found or not set.")
        
        self.llm = LLMController(api_key=groq_api_key)
        self.page_analyzer = PageAnalyzer(self.browser, self.llm)  # Pass LLM to PageAnalyzer
        self.memory = Memory()
        self.manual_intervention = ManualInterventionDialog()
        self.data_extraction_agent = DataExtractionAgent(self.llm.client)  # Initialize data extraction agent
        self.text_processor_agent = TextProcessorAgent(self.llm.client)  # Initialize text processor agent
        
        # Inicializar el controlador de acciones mejorado
        self.enhanced_action_controller = EnhancedActionController(self.browser, self.llm)
        
        # Inicializar procesadores de contenido y generador de archivos
        self.content_processor = ContentProcessor(self.browser, self.llm)
        self.file_generator = FileGenerator()
        
        self.plan = []
        self.completed_steps = []
        self.current_step_index = 0
        
        # Control de navegación mejorada
        self.extracted_urls = set()  # URLs ya procesadas para evitar loops
        self.current_page_number = 1  # Número de página actual
        self.pages_extracted = 0  # Páginas ya extraídas
    
    def safe_print(self, text: str):
        """Print text with Unicode character cleaning to avoid encoding issues."""
        try:
            # Clean emojis and Unicode characters that cause encoding issues
            cleaned_text = text
            
            # Replace common problematic emojis and Unicode characters
            emoji_replacements = {
                '🎯': '[TARGET]',
                '🔧': '[TOOL]',
                '📡': '[SIGNAL]',
                '🔍': '[SEARCH]',
                '❌': '[ERROR]',
                '✅': '[SUCCESS]', 
                '⚠️': '[WARNING]',
                '🌐': '[WEB]',
                '📊': '[DATA]',
                '📁': '[FILE]',
                '🔄': '[RELOAD]',
                '⏳': '[WAIT]',
                '📜': '[SCROLL]',
                '🚀': '[START]',
                '💡': '[IDEA]',
                '🎉': '[COMPLETE]'
            }
            
            for emoji, replacement in emoji_replacements.items():
                cleaned_text = cleaned_text.replace(emoji, replacement)
            
            # Remove any remaining problematic Unicode characters
            cleaned_text = cleaned_text.encode('ascii', 'replace').decode('ascii')
            print(cleaned_text)
            
        except Exception as e:
            # Ultimate fallback
            self.safe_print("[Message with encoding issues - unable to display]")
        
    def run(self):
        """Main execution loop with the new architecture."""
        if not self.browser.driver:
            self.safe_print("Browser initialization failed. Aborting.")
            return

        self.safe_print("Generating initial plan...")
        self.plan = self.llm.generate_plan(self.goal)
        if not self.plan:
            self.safe_print("Failed to generate a plan. Aborting.")
            return

        self.safe_print("Plan generated:")
        for i, task in enumerate(self.plan):
            self.safe_print(f"{i+1}. {task}")

        while self.current_step_index < len(self.plan):
            current_task = self.plan[self.current_step_index]
            
            self.safe_print(f"\n--- Executing Step {self.current_step_index + 1}: {current_task} ---")
            
            success = self.execute_step_with_retries(current_task)
            
            if success:
                self.safe_print(f"[OK] Step {self.current_step_index + 1} completed successfully!")
                self.completed_steps.append(current_task)
                self.current_step_index += 1
            else:
                self.safe_print(f"[ERROR] Step {self.current_step_index + 1} failed after all retries.")
                # Try alternative plan
                if self.try_alternative_approach():
                    continue
                else:
                    self.safe_print("Failed to find alternative approach. Aborting.")
                    break

        completion_message = "--- All Tasks Completed ---"
        print(completion_message)
        if self.message_callback:
            self.message_callback(completion_message)

    def is_verification_step(self, task: str) -> bool:
        """Check if a task is a verification step."""
        # Remove leading numbers and dots, then check for VERIFY
        clean_task = task.strip()
        # Remove pattern like "6. " from the beginning
        import re
        clean_task = re.sub(r'^\d+\.\s*', '', clean_task)
        return clean_task.upper().startswith("VERIFY:")

    def requires_post_action_verification(self, action: dict) -> bool:
        """
        Determine if an action requires post-execution verification.
        Text entry and button clicks are successful if they execute without errors.
        Only verify actions that navigate or significantly change page state.
        """
        action_type = action.get('action', '')
        
        # Actions that DON'T need verification (assume success if executed without error)
        simple_actions = {
            'enter_text_no_enter',  # Text entry is successful if no errors
            'enter_text',           # Text entry + enter is successful if no errors
            'click_element',        # Button clicks are successful if no errors
            'click_button',         # Button clicks are successful if no errors
            'wait',                 # Wait actions always work
            'scroll',               # Scroll actions always work
            'execute_script',       # Script execution is successful if no errors occur
            'extract_simple',       # Simple extraction is successful if temp file is created
            'finalize_extraction',  # Finalization is successful if files are processed
            'navigate_to_next_page' # Smart page navigation
        }
        
        # Actions that DO need verification (cause significant page changes)
        verification_needed_actions = {
            'navigate_to'           # Navigation should be verified
        }
        
        if action_type in simple_actions:
            return False
        elif action_type in verification_needed_actions:
            return True
        else:
            # Unknown action - err on the side of caution
            return True

    def execute_verification_step(self, task: str) -> bool:
        """Execute a verification step using LLM-generated JavaScript."""
        # Extract the verification requirement
        verification_text = task.replace("VERIFY:", "").strip()
        
        self.safe_print(f"Executing verification: {verification_text}")
        
        # Use PageAnalyzer to verify the condition
        verification_result = self.page_analyzer.verify_page_condition(
            verification_requirement=verification_text,
            context=f"Current goal: {self.goal}"
        )
        
        self.safe_print(f"Verification result: {verification_result}")
        
        if verification_result.get("verified", False):
            self.safe_print(f"[OK] Verification passed: {verification_text}")
            return True
        else:
            self.safe_print(f"[ERROR] Verification failed: {verification_result.get('reason', 'Unknown reason')}")
            return False

    def execute_step_with_retries(self, task: str) -> bool:
        """Execute a step with 3 progressive retry strategies."""
        
        # Check if this is a verification step
        if self.is_verification_step(task):
            return self.execute_verification_step(task)
        
        max_attempts = 2
        
        for attempt in range(1, max_attempts + 1):
            self.safe_print(f"Attempt {attempt}/{max_attempts} for current step...")
            
            # Extract current page information
            self.safe_print("Extracting page information...")
            page_info_before = self.page_analyzer.get_comprehensive_page_info()
            
            # Enhanced intervention check with detailed logging
            intervention_check = self.page_analyzer.detect_login_or_captcha(page_info_before)
            
            self.safe_print(f"Intervention check result: {intervention_check.get('message', 'No message')}")
            
            if intervention_check.get("requires_intervention", False):
                self.safe_print(f"Details: {intervention_check.get('details', 'No details')}")
                if not self.handle_manual_intervention(intervention_check):
                    return False
                # Re-extract page info after intervention
                self.safe_print("Re-extracting page information after manual intervention...")
                page_info_before = self.page_analyzer.get_comprehensive_page_info()
                
                # Double-check intervention after user action
                recheck = self.page_analyzer.detect_login_or_captcha(page_info_before)
                if recheck.get("requires_intervention", False):
                    self.safe_print("Still requires intervention after user action. User may need more time.")
                    # Give user another chance or abort
                    if not self.handle_manual_intervention(recheck):
                        return False
                    page_info_before = self.page_analyzer.get_comprehensive_page_info()
            
            # Generate action based on attempt strategy
            if attempt == 1:
                # Normal approach
                action = self.generate_normal_action(task, page_info_before)
            elif attempt == 2:
                # Alternative selector approach
                action = self.generate_alternative_action(task, page_info_before)
            else:
                # Creative approach - let LLM decide completely
                action = self.generate_creative_action(task, page_info_before)
            
            if not action:
                self.safe_print(f"Failed to generate action for attempt {attempt}")
                continue
            
            self.safe_print(f"Executing action: {action}")
            
            # Execute the action using enhanced controller
            execution_success = self.execute_action_enhanced(action)
            if not execution_success:
                self.safe_print(f"Action execution failed on attempt {attempt}")
                continue
            
            # Check if this action needs post-execution verification
            if self.requires_post_action_verification(action):
                self.safe_print("This action requires verification, waiting for page updates...")
                time.sleep(2)
                
                # Extract page info after action
                page_info_after = self.page_analyzer.get_comprehensive_page_info()
                
                # Verify step completion
                is_complete = self.llm.verify_step_completion_with_page_info(
                    task, page_info_before, page_info_after
                )
                
                if is_complete:
                    self.safe_print(f"Step verification successful on attempt {attempt}!")
                    return True
                else:
                    self.safe_print(f"Step verification failed on attempt {attempt}")
            else:
                self.safe_print(f"Action completed successfully on attempt {attempt} (no verification needed)")
                return True
            
            if is_complete:
                self.safe_print(f"Step verification successful on attempt {attempt}!")
                return True
            else:
                self.safe_print(f"Step verification failed on attempt {attempt}")
        
        return False

    def generate_normal_action(self, task: str, page_info: Dict) -> Dict:
        """Generate action using normal approach."""
        
        # Check if current task is a consolidation step
        task_lower = task.lower()
        if any(keyword in task_lower for keyword in [
            'system will automatically consolidate',
            'consolidate results',
            'generate excel',
            'create final',
            'save to excel',
            'process results'
        ]):
            self.safe_print("[CONSOLIDATION] Detected consolidation step, triggering file generation")
            
            # Determine output format from goal and task
            format_type = "excel"  # Default
            if "word" in self.goal.lower() or "doc" in self.goal.lower():
                format_type = "word"
            elif "txt" in self.goal.lower() or "text" in self.goal.lower():
                format_type = "txt"
            
            return {
                'action': 'process_temp_files_to_excel',
                'parameters': {
                    'format': format_type,
                    'goal': self.goal
                }
            }
        
        # Normal action generation
        remaining_steps = self.plan[self.current_step_index:]
        return self.llm.generate_action_from_page_info(
            self.goal, remaining_steps, self.completed_steps, page_info
        )

    def generate_alternative_action(self, task: str, page_info: Dict) -> Dict:
        """Generate action using alternative selectors."""
        # For now, this is the same as normal, but could be enhanced
        # to specifically request alternative approaches
        remaining_steps = self.plan[self.current_step_index:]
        return self.llm.generate_action_from_page_info(
            f"ALTERNATIVE APPROACH: {self.goal}", remaining_steps, self.completed_steps, page_info
        )

    def generate_creative_action(self, task: str, page_info: Dict) -> Dict:
        """Generate action using creative/desperate approach."""
        # Get additional context with page structure
        page_structure = self.page_analyzer.get_page_structure()
        
        # Combine both info types for maximum context
        enhanced_page_info = page_info.copy()
        enhanced_page_info["additional_structure"] = page_structure
        
        remaining_steps = self.plan[self.current_step_index:]
        return self.llm.generate_action_from_page_info(
            f"CREATIVE APPROACH - USE ANY MEANS: {self.goal}", 
            remaining_steps, self.completed_steps, enhanced_page_info
        )

    def try_alternative_approach(self) -> bool:
        """Try to generate an alternative plan when current approach fails."""
        self.safe_print("Attempting to generate alternative plan...")
        
        current_page_info = self.page_analyzer.get_comprehensive_page_info()
        failed_steps = self.plan[self.current_step_index:]
        
        alternative_plan = self.llm.generate_alternative_plan(
            self.goal, failed_steps, current_page_info
        )
        
        if alternative_plan:
            self.safe_print("Alternative plan generated:")
            for i, step in enumerate(alternative_plan):
                self.safe_print(f"{i+1}. {step}")
            
            # Replace remaining steps with alternative plan
            self.plan = self.completed_steps + alternative_plan
            self.current_step_index = len(self.completed_steps)
            return True
        
        return False

    def handle_manual_intervention(self, intervention_info: Dict) -> bool:
        """Handle manual intervention when needed."""
        intervention_type = intervention_info.get("type", "unknown")
        intervention_message = intervention_info.get("message", "Manual intervention required")
        
        self.safe_print(f"Manual intervention detected: {intervention_message}")
        
        user_wants_to_continue = self.manual_intervention.show_intervention_popup(
            intervention_message, intervention_type
        )
        
        if user_wants_to_continue:
            self.safe_print("User completed manual intervention. Continuing...")
            return True
        else:
            self.safe_print("User chose to abort. Stopping automation.")
            return False

    def execute_action_enhanced(self, action: Dict) -> bool:
        """Execute a given action using enhanced action controller with detailed feedback."""
        action_name = action.get("action")
        params = action.get("parameters", {})

        if not action_name:
            self.safe_print("No action specified.")
            return False

        # Obtener información actual de la página ANTES de ejecutar la acción
        page_info = self.page_analyzer.get_comprehensive_page_info()
        
        self.safe_print(f"\n🎯 Executing Enhanced Action: {action_name}")
        self.safe_print(f"Parameters: {params}")
        
        # Usar el controlador de acciones mejorado para acciones básicas
        enhanced_actions = ["click_element", "enter_text", "enter_text_no_enter", "click_button"]
        
        if action_name in enhanced_actions:
            self.safe_print(f"📡 Using Enhanced Action Controller for {action_name}")
            
            # Verificar si la acción es redundante en el contexto actual
            current_state = self.enhanced_action_controller._analyze_page_state(page_info)
            should_skip, skip_reason = self.enhanced_action_controller.should_skip_action_based_on_context(action, current_state)
            
            if should_skip:
                self.safe_print(f"⏭️  Skipping action: {skip_reason}")
                return True
            
            # Ejecutar con retroalimentación completa
            result = self.enhanced_action_controller.execute_action_with_feedback(action, page_info)
            
            # Mostrar retroalimentación detallada
            feedback = self.enhanced_action_controller.get_action_feedback_for_llm(action, result)
            self.safe_print(f"🔍 Action Feedback:\n{feedback}")
            
            # Si la acción falló, proporcionar contexto para el próximo intento
            if not result.get("success", False):
                self.safe_print(f"[ERROR] Action failed. Providing detailed context for next iteration...")
                
                # Re-analizar página después del fallo para obtener información actualizada
                updated_page_info = self.page_analyzer.get_comprehensive_page_info()
                
                # Extraer elementos interactivos actualizados para debug
                elements = updated_page_info.get('interactive_elements', {}).get('elements', [])
                self.safe_print(f"🔍 Current page has {len(elements)} interactive elements")
                
                # Mostrar algunos elementos disponibles para debug
                if elements:
                    self.safe_print("📋 Available elements for next attempt:")
                    for i, elem in enumerate(elements[:5]):  # Mostrar solo los primeros 5
                        self.safe_print(f"  {i+1}. {elem.get('tag', 'unknown')} - {elem.get('text', 'no text')[:50]}")
                        self.safe_print(f"     Selector: {elem.get('selector', 'no selector')}")
                
                # El LLM recibirá esta información actualizada en el próximo ciclo
                return False
            
            self.safe_print(f"[SUCCESS] Enhanced action completed successfully")
            return True

        # Usar la implementación original para acciones especiales
        return self.execute_action(action)

    def execute_action(self, action: Dict) -> bool:
        """Execute a given action and return success status."""
        action_name = action.get("action")
        params = action.get("parameters", {})

        if not action_name:
            self.safe_print("No action specified.")
            return False

        try:
            if action_name == "click_element":
                selector = params.get("selector", "")
                return self.browser.click_element(selector)
                
            elif action_name == "enter_text":
                selector = params.get("selector", "")
                text = params.get("text", "")
                return self.browser.enter_text(selector, text, press_enter=True)

            elif action_name == "enter_text_no_enter":
                selector = params.get("selector", "")
                text = params.get("text", "")
                success = self.browser.enter_text_without_enter(selector, text)
                
                # For contenteditable elements, verify the content was accepted
                if success:
                    self.safe_print("Verifying that the text input was detected properly...")
                    # Small delay to allow page to process the input
                    time.sleep(1)
                    # Note: Post-action verification will be handled by the verification system if needed
                
                return success
                
            elif action_name == "navigate_to":
                url = params.get("url", "")
                self.browser.navigate_to(url)
                return True
                
            elif action_name == "wait":
                seconds = params.get("seconds", 1)
                time.sleep(seconds)
                return True
                
            elif action_name == "scroll":
                direction = params.get("direction", "down")
                pixels = params.get("pixels", 300)
                if direction == "down":
                    script = f"window.scrollBy(0, {pixels});"
                else:
                    script = f"window.scrollBy(0, -{pixels});"
                self.browser.execute_script(script)
                return True
                
            elif action_name == "click_button":
                # General action to click relevant buttons using JSON data
                keywords = params.get("keywords", ["submit", "send", "next", "weiter", "continue"])
                page_info = self.page_analyzer.get_comprehensive_page_info()
                return self.browser.click_button_from_json(page_info, keywords)

            elif action_name == "extract_simple":
                # New simple extraction action with loop prevention
                format_type = params.get("format", "txt")
                goal = params.get("goal", "")
                
                self.safe_print(f"Executing simple extraction to {format_type} format...")
                
                # Check current URL to avoid loops
                current_url = self.browser.driver.current_url
                self.safe_print(f"Current URL: {current_url}")
                
                if current_url in self.extracted_urls:
                    self.safe_print(f"[WARNING]  URL already extracted, skipping to avoid loop: {current_url}")
                    return True  # Consider successful to move to next step
                
                # Use the data extraction agent for simple extraction
                result = self.data_extraction_agent.extract_page_content_simple(self.browser.driver)
                
                if result['success']:
                    self.safe_print(f"Page content extracted to temp file: {result['temp_file']}")
                    
                    # Store temp file for later processing
                    if not hasattr(self, 'temp_files'):
                        self.temp_files = []
                    self.temp_files.append(result['temp_file'])
                    
                    # Mark URL as extracted
                    self.extracted_urls.add(current_url)
                    self.pages_extracted += 1
                    
                    self.safe_print(f"[SUCCESS] Extracted {result.get('content_length', 0)} characters from '{result.get('title', 'Unknown')}'")
                    self.safe_print(f"[DATA] Total pages extracted: {self.pages_extracted}")
                    
                    # Auto-trigger Excel generation if goal involves Excel output
                    goal_lower = self.goal.lower()
                    if any(keyword in goal_lower for keyword in ['excel', 'archivo excel', 'spreadsheet']):
                        # Check if we've extracted enough pages or this is the final extraction
                        current_step = self.plan[self.current_step_index] if self.current_step_index < len(self.plan) else ""
                        next_step = self.plan[self.current_step_index + 1] if self.current_step_index + 1 < len(self.plan) else ""
                        
                        # If next step involves consolidation or this seems to be the last extraction
                        if ('consolidat' in next_step.lower() or 'system will automatically' in next_step.lower() or 
                            self.pages_extracted >= 2):  # Or if we've extracted multiple pages
                            
                            self.safe_print("[AUTO-TRIGGER] Goal involves Excel output, checking for auto-generation...")
                            
                            # Use the data extraction agent's auto-trigger method
                            excel_triggered = self.data_extraction_agent.auto_trigger_excel_generation()
                            if excel_triggered:
                                self.safe_print("[AUTO-EXCEL] Excel generation dialog triggered successfully")
                            else:
                                self.safe_print("[AUTO-EXCEL] Could not auto-trigger Excel generation")
                    
                    return True
                else:
                    self.safe_print(f"Simple extraction failed: {result.get('error', 'Unknown error')}")
                    return False
                    
            elif action_name == "navigate_to_next_page":
                # Smart navigation to next page with URL construction
                base_url = params.get("base_url", "")
                current_page = params.get("current_page", 1)
                next_page = current_page + 1
                
                self.safe_print(f"[RELOAD] Navigating to next page: {next_page}")
                
                # Construct next page URL
                if "amazon.de" in base_url:
                    # Amazon pagination format
                    if "page=" in base_url:
                        # Replace existing page parameter
                        import re
                        next_url = re.sub(r'page=\d+', f'page={next_page}', base_url)
                    else:
                        # Add page parameter
                        connector = "&" if "?" in base_url else "?"
                        next_url = f"{base_url}{connector}page={next_page}"
                else:
                    # Generic pagination - try common patterns
                    connector = "&" if "?" in base_url else "?"
                    next_url = f"{base_url}{connector}page={next_page}"
                
                self.safe_print(f"[LOCATION] Next page URL: {next_url}")
                
                try:
                    self.browser.driver.get(next_url)
                    time.sleep(2)  # Wait for page load
                    
                    # Update page tracking
                    self.current_page_number = next_page
                    self.safe_print(f"[SUCCESS] Successfully navigated to page {next_page}")
                    return True
                except Exception as e:
                    self.safe_print(f"[ERROR] Failed to navigate to next page: {str(e)}")
                    return False
                
            elif action_name == "finalize_extraction":
                # Process all collected temporary files using TextProcessorAgent
                output_format = params.get("format", "txt")
                goal = params.get("goal", "")
                
                if not hasattr(self, 'temp_files') or not self.temp_files:
                    self.safe_print("No temporary files found in memory...")
                    
                    # Intentar usar el nuevo sistema de procesamiento de archivos temporales
                    self.safe_print("[NEW SYSTEM] Intentando usar sistema de procesamiento mejorado...")
                    
                    try:
                        import subprocess
                        import os
                        
                        # Ejecutar el script de procesamiento de archivos temporales
                        script_path = os.path.join(os.path.dirname(__file__), "process_temp_files_to_excel.py")
                        if os.path.exists(script_path):
                            self.safe_print("[NEW SYSTEM] Ejecutando procesamiento de archivos temporales...")
                            result = subprocess.run([
                                'python', script_path
                            ], capture_output=False, text=True, cwd=os.path.dirname(__file__))
                            
                            if result.returncode == 0:
                                self.safe_print("[SUCCESS] Procesamiento completado exitosamente!")
                                return True
                            else:
                                self.safe_print(f"[ERROR] Error en procesamiento: código {result.returncode}")
                                return False
                        else:
                            self.safe_print("[ERROR] Script de procesamiento no encontrado")
                            return False
                            
                    except Exception as e:
                        self.safe_print(f"[ERROR] Error ejecutando nuevo sistema: {e}")
                        return False
                
                self.safe_print(f"Processing {len(self.temp_files)} temporary files for final {output_format} output...")
                
                # Use TextProcessorAgent to process multiple temp files
                result = self.text_processor_agent.process_temp_files_to_format(
                    self.temp_files, output_format, goal
                )
                
                if result['success']:
                    self.safe_print(f"[SUCCESS] Final extraction successful!")
                    self.safe_print(f"[DOC] File saved: {result['output_file']}")
                    self.safe_print(f"[DATA] Pages processed: {result.get('pages_processed', 0)}")
                    self.safe_print(f"[AI] Method: {result.get('processing_method', 'N/A')}")
                    
                    # Show processing summary
                    summary = self.text_processor_agent.get_processing_summary(result)
                    self.safe_print(f"\n{summary}")
                    
                    # Open the output folder
                    import os
                    import subprocess
                    if os.path.exists(result['output_file']):
                        folder_path = os.path.dirname(result['output_file'])
                        subprocess.run(['explorer', folder_path], shell=True)
                    
                    return True
                else:
                    self.safe_print(f"[ERROR] Final extraction failed: {result.get('error', 'Unknown error')}")
                    return False
            
            elif action_name == "extract_page_content":
                # Nueva acción: extraer contenido de página actual usando JavaScript
                page_number = params.get("page_number", self.current_page_number)
                
                page_data = self.content_processor.extract_page_content(page_number)
                if page_data:
                    self.safe_print(f"[SUCCESS] Contenido extraído de página {page_number}")
                    self.safe_print(f"[INFO] Caracteres extraídos: {page_data['content_length']}")
                    return True
                else:
                    self.safe_print(f"[ERROR] No se pudo extraer contenido de página {page_number}")
                    return False
            
            elif action_name == "process_page_with_llm":
                # Nueva acción: procesar página extraída con LLM
                page_number = params.get("page_number", self.current_page_number)
                original_objective = params.get("objective", self.goal)
                
                # Buscar la página en memoria
                page_data = None
                for page in self.content_processor.extracted_pages:
                    if page.get('page_number') == page_number:
                        page_data = page
                        break
                
                if not page_data:
                    self.safe_print(f"[ERROR] No se encontró datos de página {page_number} en memoria")
                    return False
                
                result = self.content_processor.process_page_with_llm(page_data, original_objective)
                if result:
                    self.safe_print(f"[SUCCESS] Página {page_number} procesada por LLM")
                    return True
                else:
                    self.safe_print(f"[ERROR] Error procesando página {page_number} con LLM")
                    return False
            
            elif action_name == "extract_and_process_current_page":
                # Acción combinada: extraer y procesar página actual
                page_number = params.get("page_number", self.current_page_number)
                original_objective = params.get("objective", self.goal)
                
                # Paso 1: Extraer contenido
                self.safe_print(f"[STEP 1] Extrayendo contenido de página {page_number}...")
                page_data = self.content_processor.extract_page_content(page_number)
                
                if not page_data:
                    self.safe_print(f"[ERROR] No se pudo extraer contenido")
                    return False
                
                # Paso 2: Procesar con LLM
                self.safe_print(f"[STEP 2] Procesando con LLM...")
                result = self.content_processor.process_page_with_llm(page_data, original_objective)
                
                if result:
                    self.safe_print(f"[SUCCESS] Página {page_number} extraída y procesada completamente")
                    self.current_page_number += 1  # Incrementar para la próxima página
                    return True
                else:
                    self.safe_print(f"[ERROR] Error en procesamiento con LLM")
                    return False
            
            elif action_name == "generate_final_document":
                # Nueva acción: generar documento final consolidado
                output_format = params.get("format", "excel").lower()
                
                # Verificar que hay datos procesados
                if not self.content_processor.processed_results:
                    self.safe_print("[ERROR] No hay datos procesados para generar documento")
                    return False
                
                # Consolidar resultados
                self.safe_print("[CONSOLIDATE] Consolidando resultados con LLM...")
                consolidated_data = self.content_processor.consolidate_results(self.goal, output_format)
                
                if not consolidated_data:
                    self.safe_print("[ERROR] Error consolidando resultados")
                    return False
                
                # Obtener resumen de memoria
                summary_info = self.content_processor.get_memory_summary()
                
                # Generar archivo
                self.safe_print(f"[GENERATE] Generando archivo {output_format.upper()}...")
                
                if output_format == "excel":
                    file_path = self.file_generator.generate_excel_file(
                        consolidated_data, self.goal, summary_info
                    )
                elif output_format == "word":
                    file_path = self.file_generator.generate_word_file(
                        consolidated_data, self.goal, summary_info
                    )
                else:
                    self.safe_print(f"[ERROR] Formato no soportado: {output_format}")
                    return False
                
                if file_path:
                    self.safe_print(f"[SUCCESS] Documento generado: {file_path}")
                    
                    # Mostrar diálogo de éxito
                    self.file_generator.show_success_dialog(file_path)
                    
                    # Limpiar memoria
                    self.safe_print("[CLEANUP] Limpiando memoria...")
                    self.content_processor.clear_memory()
                    
                    return True
                else:
                    self.safe_print("[ERROR] Error generando documento")
                    return False
            
            elif action_name == "show_memory_status":
                # Acción de debug: mostrar estado de la memoria
                summary = self.content_processor.get_memory_summary()
                
                self.safe_print("=== ESTADO DE LA MEMORIA ===")
                self.safe_print(f"Páginas extraídas: {summary['pages_extracted']}")
                self.safe_print(f"Páginas procesadas: {summary['pages_processed']}")
                self.safe_print(f"Total caracteres: {summary['total_content_chars']:,}")
                
                if summary['pages_info']:
                    self.safe_print("\nDetalle de páginas:")
                    for page_info in summary['pages_info']:
                        self.safe_print(f"  Página {page_info['page_number']}: {page_info['title']} ({page_info['content_length']} chars)")
                
                return True
            
            elif action_name == "process_temp_files_to_excel":
                # Nueva acción: procesar archivos temporales existentes a Excel
                self.safe_print("[EXCEL] Procesando archivos temporales a Excel...")
                
                try:
                    import subprocess
                    import os
                    
                    # Ejecutar el script de procesamiento
                    script_path = os.path.join(os.path.dirname(__file__), "process_temp_files_to_excel.py")
                    if os.path.exists(script_path):
                        self.safe_print("[PROCESS] Ejecutando procesamiento de archivos temporales...")
                        
                        # Ejecutar sin capturar salida para que el usuario vea el progreso
                        result = subprocess.run([
                            'python', script_path
                        ], cwd=os.path.dirname(__file__))
                        
                        if result.returncode == 0:
                            self.safe_print("[SUCCESS] Excel generado exitosamente!")
                            return True
                        else:
                            self.safe_print(f"[ERROR] Error generando Excel: código {result.returncode}")
                            return False
                    else:
                        self.safe_print("[ERROR] Script de procesamiento no encontrado")
                        return False
                        
                except Exception as e:
                    self.safe_print(f"[ERROR] Error procesando a Excel: {e}")
                    return False
                
            else:
                self.safe_print(f"Unknown action: {action_name}")
                return False
                
        except Exception as e:
            self.safe_print(f"Error executing action {action_name}: {e}")
            return False
