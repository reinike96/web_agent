"""
Data Extraction Agent for intelligent web data extraction with JavaScript generation.
Handles multiple output formats (TXT, Excel, Word) with automatic format detection.
"""

import re
import json
import tempfile
import os
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List
from groq import Groq


class DataExtractionAgent:
    """
    Agent that detects data extraction intents and generates JavaScript code
    for extracting and exporting data in various formats (TXT, Excel, Word).
    """
    
    def __init__(self, groq_client: Groq):
        """Initialize with Groq client for LLM interactions."""
        self.client = groq_client
        self.model = "moonshotai/kimi-k2-instruct"
    
    def detect_extraction_intent(self, task_description: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Detect if a task description mentions data extraction patterns, indicating extraction is needed.
        
        Args:
            task_description: The task description from the plan (not the original goal)
        
        Returns:
            tuple: (is_extraction, extraction_details)
        """
        # Look for extraction patterns in the task description
        task_lower = task_description.lower()
        
        # Check for various extraction patterns (including corrupted text)
        extraction_patterns = [
            'data_extraction_agent',
            'data extraction agent',
            'extraction agent',
            'data ex',  # Handle corrupted text like "Data Ex Extraction Agent"
            'extract product',
            'extract.*data',
            'extract.*names',
            'extract.*prices'
        ]
        
        # Check if any extraction pattern is mentioned
        has_extraction = any(
            re.search(pattern, task_lower) for pattern in extraction_patterns
        )
        
        if not has_extraction:
            return False, {}
        
        print(f"[DEBUG] Detected extraction pattern in task: {task_description}")
        
        # Determine output format from context
        detected_format = 'txt'  # Default format
        
        # Check for format keywords in the task description
        format_keywords = {
            'excel': ['excel', 'xlsx', 'xls', 'spreadsheet', 'hoja de c?lculo', 'csv'],
            'word': ['word', 'docx', 'doc', 'document', 'documento'],
            'txt': ['txt', 'text', 'texto', 'plain text']
        }
        
        for format_type, keywords in format_keywords.items():
            if any(keyword in task_lower for keyword in keywords):
                detected_format = format_type
                break
        
        # Extract target content hints from task description
        target_hints = []
        content_patterns = [
            r'product[s]?', r'producto[s]?', r'result[s]?', r'resultado[s]?', 
            r'data', r'datos?', r'information', r'informaci?n', r'content', r'contenido',
            r'title[s]?', r't?tulo[s]?', r'price[s]?', r'precio[s]?', 
            r'rating[s]?', r'calificaci[o?]n[es]?', r'link[s]?', r'enlace[s]?'
        ]
        
        for pattern in content_patterns:
            if re.search(pattern, task_lower):
                target_hints.append(pattern)
        
        # Detect if scrolling or multiple pages are needed
        needs_scrolling = any(word in task_lower for word in [
            'slow', 'lento', 'complete', 'completo', 'all', 'todo', 'todas',
            'm?ltiples', 'multiple', 'p?ginas', 'pages', 'primeras', 'first',
            'scroll', 'load all', 'cargar todo'
        ])
        
        extraction_details = {
            'format': detected_format,
            'target_hints': target_hints,
            'goal': task_description,  # Use the task description as the goal
            'needs_scrolling': needs_scrolling
        }
        
        return True, extraction_details
    
    def generate_extraction_javascript(self, extraction_details: Dict[str, Any]) -> str:
        """
        Generate JavaScript code for data extraction based on the extraction details.
        """
        format_type = extraction_details.get('format', 'txt')
        goal = extraction_details.get('goal', '')
        needs_scrolling = extraction_details.get('needs_scrolling', False)
        
        try:
            # Generate extraction code using LLM
            extraction_prompt = f"""
            Generate JavaScript code that:
            
            1. EXTRACTS data from the current webpage based on this goal: "{goal}"
            2. FORMATS the data for {format_type.upper()} output
            3. CREATES and DOWNLOADS the file automatically
            
            Requirements:
            - Use DOM manipulation to find and extract relevant data
            - Handle tables, lists, and text content intelligently
            - Generate proper {format_type.upper()} format
            - Create downloadable file with proper filename
            - Include error handling
            
            Output format: {format_type.upper()}
            
            Return ONLY the JavaScript code, no explanations.
            """
            
            if needs_scrolling:
                extraction_prompt += """
                
                IMPORTANT: Include slow scrolling functionality:
                - Scroll page slowly to load all content
                - Wait for content to load between scrolls
                - Extract data after full page is loaded
                """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a JavaScript expert specializing in web data extraction and file generation."},
                    {"role": "user", "content": extraction_prompt}
                ],
                # Removed max_tokens to allow complete response
                temperature=0.1
            )
            
            js_code = response.choices[0].message.content.strip()
            
            # Clean and validate the JavaScript code
            js_code = self._clean_javascript_code(js_code)
            
            # Check if cleaning resulted in fallback placeholder
            if js_code.startswith("//"):
                print("[DEBUG] Malformed code detected, switching to fallback generation")
                return self._generate_fallback_extraction_code(format_type, goal, needs_scrolling)
            
            return js_code
            
        except Exception as e:
            # Fallback to template-based generation
            return self._generate_fallback_extraction_code(format_type, goal, needs_scrolling)
    
    def _clean_javascript_code(self, js_code: str) -> str:
        """Clean and validate JavaScript code."""
        # Remove markdown code blocks if present
        js_code = re.sub(r'^```(?:javascript|js)?\n?', '', js_code, flags=re.MULTILINE)
        js_code = re.sub(r'\n?```$', '', js_code, flags=re.MULTILINE)
        
        # Check for severely malformed code patterns
        # Pattern 1: Repeated opening braces
        if re.search(r'\{\s*\{\s*\{\s*\{', js_code):
            print("[DEBUG] Detected malformed JavaScript with repeated braces, using fallback")
            return "// Malformed code detected, using fallback"
        
        # Pattern 2: Unmatched braces or syntax errors
        open_braces = js_code.count('{')
        close_braces = js_code.count('}')
        if abs(open_braces - close_braces) > 2:  # Allow small mismatches
            print(f"[DEBUG] Unmatched braces detected (open:{open_braces}, close:{close_braces}), using fallback")
            return "// Unmatched braces detected, using fallback"
        
        # Pattern 3: Check for basic JavaScript validity
        if 'return {' in js_code and js_code.count('{') > js_code.count('}') + 5:
            print("[DEBUG] Invalid syntax structure detected, using fallback")
            return "// Invalid syntax detected, using fallback"
        
        # Pattern 4: Detect infinite repetition patterns (new)
        if re.search(r'(LoadedLoaded|LoadedLoadedLoaded)', js_code):
            print("[DEBUG] Detected infinite repetition pattern, using fallback")
            return "// Infinite repetition detected, using fallback"
        
        # Pattern 5: Detect invalid function calls (new)
        if re.search(r'querySelector\d+\(', js_code):
            print("[DEBUG] Detected invalid querySelector calls, using fallback")
            return "// Invalid function calls detected, using fallback"
        
        # Pattern 6: Detect repeated variable declarations (new)
        const_declarations = re.findall(r'const\s+(\w+)', js_code)
        if len(const_declarations) != len(set(const_declarations)):
            print("[DEBUG] Detected duplicate variable declarations, using fallback")
            return "// Duplicate declarations detected, using fallback"
        
        # Pattern 7: Detect extremely long lines that indicate corruption (new)
        lines = js_code.split('\n')
        for line in lines:
            if len(line) > 2000:  # Line too long, likely corrupted
                print("[DEBUG] Detected extremely long line, using fallback")
                return "// Extremely long line detected, using fallback"
        
        # Pattern 8: Check for basic syntax issues (new)
        if js_code.count('"') % 2 != 0:  # Unmatched quotes
            print("[DEBUG] Detected unmatched quotes, using fallback")
            return "// Unmatched quotes detected, using fallback"
        
        # Fix common JavaScript selector issues
        # Replace invalid child selector '> *' with just '*'
        js_code = js_code.replace("querySelectorAll('> *')", "querySelectorAll('*')")
        js_code = js_code.replace('querySelectorAll("> *")', 'querySelectorAll("*")')
        
        # Fix other common selector issues
        js_code = js_code.replace("querySelector('> ", "querySelector('")
        js_code = js_code.replace('querySelector("> ', 'querySelector("')
        
        # Ensure the code has basic structure
        if 'function' not in js_code and '=>' not in js_code:
            js_code = f"(function() {{\n{js_code}\n}})();"
        
        return js_code.strip()
    
    def _generate_fallback_extraction_code(self, format_type: str, goal: str, needs_scrolling: bool) -> str:
        """Generate fallback extraction code when LLM fails."""
        scrolling_code = ""
        if needs_scrolling:
            scrolling_code = """
            // Slow scroll to load all content
            await new Promise(resolve => {
                let scrollCount = 0;
                const maxScrolls = 20;
                const scrollInterval = setInterval(() => {
                    window.scrollBy(0, window.innerHeight / 3);
                    scrollCount++;
                    
                    if (scrollCount >= maxScrolls || 
                        (window.innerHeight + window.scrollY) >= document.body.offsetHeight) {
                        clearInterval(scrollInterval);
                        setTimeout(resolve, 1000); // Wait for final content load
                    }
                }, 800); // Slow scroll speed
            });
            """
        
        if format_type == 'excel':
            return f"""
            (async function extractToExcel() {{
                try {{
                    {scrolling_code}
                    
                    const data = [];
                    let productCount = 0;
                    
                    // Add headers
                    data.push(['Title', 'Price', 'Rating', 'Link', 'Source Page']);
                    
                    // Check if this is Amazon and use specific selectors
                    const isAmazon = window.location.hostname.includes('amazon');
                    const currentPage = window.location.href;
                    
                    if (isAmazon) {{
                        console.log('Detected Amazon site, using specialized extraction...');
                        
                        // Amazon product selectors (multiple variations)
                        const productSelectors = [
                            '[data-component-type="s-search-result"]',
                            '.s-result-item[data-component-type]',
                            '.s-search-result',
                            '.s-result-item',
                            '[data-asin]:not([data-asin=""])'
                        ];
                        
                        let products = [];
                        for (const selector of productSelectors) {{
                            products = document.querySelectorAll(selector);
                            if (products.length > 0) {{
                                console.log(`Found ${{products.length}} products with selector: ${{selector}}`);
                                break;
                            }}
                        }}
                        
                        products.forEach((product, index) => {{
                            try {{
                                // Extract title
                                const titleEl = product.querySelector('h2 a span') || 
                                              product.querySelector('h2 a') ||
                                              product.querySelector('[data-cy="title-recipe-title"]') ||
                                              product.querySelector('.s-size-mini span') ||
                                              product.querySelector('h3 a span') ||
                                              product.querySelector('h2 span') ||
                                              product.querySelector('.a-text-normal');
                                const title = titleEl ? titleEl.textContent.trim() : `Product ${{index + 1}}`;
                                
                                // Extract price (multiple attempts for different formats)
                                let price = 'No price';
                                const priceSelectors = [
                                    '.a-price-whole',
                                    '.a-offscreen',
                                    '[data-a-price-amount]',
                                    '.a-price .sr-only',
                                    '.a-price-range',
                                    '.a-price',
                                    '[class*="price"]'
                                ];
                                
                                for (const selector of priceSelectors) {{
                                    const priceEl = product.querySelector(selector);
                                    if (priceEl) {{
                                        const priceText = priceEl.textContent.trim();
                                        if (priceText && priceText.match(/[0-9]/)) {{
                                            price = priceText.replace(/[^0-9.,?$]/g, '').trim();
                                            if (price) break;
                                        }}
                                    }}
                                }}
                                
                                // Extract rating
                                const ratingEl = product.querySelector('.a-icon-alt') ||
                                               product.querySelector('[aria-label*="stars"]') ||
                                               product.querySelector('[aria-label*="Sterne"]') ||
                                               product.querySelector('.a-star-mini');
                                let rating = 'No rating';
                                if (ratingEl) {{
                                    const ratingText = ratingEl.textContent || ratingEl.getAttribute('aria-label') || '';
                                    const ratingMatch = ratingText.match(/([0-9],?[0-9]?)/);
                                    rating = ratingMatch ? ratingMatch[1] : 'No rating';
                                }}
                                
                                // Extract link
                                const linkEl = product.querySelector('h2 a') || 
                                             product.querySelector('a[href*="/dp/"]') ||
                                             product.querySelector('a[href*="/gp/"]');
                                const link = linkEl ? (linkEl.href.startsWith('http') ? linkEl.href : 'https://amazon.de' + linkEl.href) : 'No link';
                                
                                // Determine source page
                                const pageMatch = currentPage.match(/page=(\\d+)/);
                                const sourcePage = pageMatch ? `Page ${{pageMatch[1]}}` : 'Page 1';
                                
                                if (title !== 'No title' && title.length > 3) {{
                                    data.push([title, price, rating, link, sourcePage]);
                                    productCount++;
                                }}
                            }} catch (err) {{
                                console.log('Error extracting individual product:', err);
                            }}
                        }});
                        
                        console.log(`Extracted ${{productCount}} products from Amazon`);
                        
                    }} else {{
                        // Generic e-commerce extraction for non-Amazon sites
                        console.log('Using generic product extraction...');
                        
                        const genericSelectors = [
                            '[class*="product"]',
                            '[data-testid*="product"]',
                            '.item',
                            '[class*="item"]',
                            '.listing',
                            '[class*="card"]'
                        ];
                        
                        let products = [];
                        for (const selector of genericSelectors) {{
                            products = document.querySelectorAll(selector);
                            if (products.length > 3) break;
                        }}
                        
                        products.forEach((product, index) => {{
                            const title = product.querySelector('h1, h2, h3, h4, [class*="title"], [class*="name"]')?.textContent?.trim() || `Product ${{index + 1}}`;
                            const price = product.querySelector('[class*="price"], [class*="cost"], [data-price]')?.textContent?.trim() || 'No price';
                            const rating = product.querySelector('[class*="rating"], [class*="star"], [class*="score"]')?.textContent?.trim() || 'No rating';
                            const link = product.querySelector('a')?.href || 'No link';
                            const sourcePage = 'Generic Page';
                            
                            if (title !== 'No title' && title.length > 3) {{
                                data.push([title, price, rating, link, sourcePage]);
                                productCount++;
                            }}
                        }});
                    }}
                    
                    // Create CSV content
                    const csvContent = data.map(row => 
                        row.map(cell => `"${{cell?.toString().replace(/"/g, '""') || ''}}"`).join(',')
                    ).join('\\n');
                    
                    // Generate filename
                    const siteName = window.location.hostname.replace(/[^a-z0-9]/gi, '_');
                    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
                    const filename = `${{siteName}}_products_${{timestamp}}.csv`;
                    
                    // Download file
                    const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8' }});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    
                    console.log(`Successfully extracted ${{productCount}} products to ${{filename}}`);
                    return {{ success: true, count: productCount, filename: filename }};
                    
                }} catch (error) {{
                    console.error('Error during Excel extraction:', error);
                    return {{ success: false, error: error.message }};
                }}
            }})();
            """
            
        elif format_type == 'word':
            return f"""
            (async function extractToWord() {{
                try {{
                    {scrolling_code}
                    
                    // Extract Wikipedia article content specifically
                    const title = document.querySelector('h1#firstHeading, h1.firstHeading')?.textContent?.trim() || 'Wikipedia Article';
                    const content = [];
                    
                    // Add title
                    content.push(title);
                    content.push(''); // Empty line
                    
                    // Get main content area (Wikipedia specific)
                    const mainContent = document.querySelector('#mw-content-text .mw-parser-output, #content .mw-parser-output, .mw-parser-output');
                    
                    if (mainContent) {{
                        // Extract sections in order
                        const elements = mainContent.children;
                        for (let i = 0; i < elements.length; i++) {{
                            const el = elements[i];
                            
                            if (el.matches('h1, h2, h3, h4, h5, h6')) {{
                                // Add section heading
                                const heading = el.textContent.trim().replace(/\\[.*?\\]/g, ''); // Remove reference numbers
                                if (heading && !heading.includes('Editar')) {{
                                    content.push('');
                                    content.push(heading.toUpperCase());
                                    content.push('');
                                }}
                            }} else if (el.matches('p')) {{
                                // Add paragraph text
                                const text = el.textContent.trim().replace(/\\[.*?\\]/g, ''); // Remove reference numbers
                                if (text && text.length > 20) {{
                                    content.push(text);
                                    content.push('');
                                }}
                            }} else if (el.matches('ul, ol')) {{
                                // Add list items
                                const items = el.querySelectorAll('li');
                                items.forEach(item => {{
                                    const text = item.textContent.trim().replace(/\\[.*?\\]/g, '');
                                    if (text) {{
                                        content.push('? ' + text);
                                    }}
                                }});
                                content.push('');
                            }} else if (el.matches('table.wikitable, table.infobox')) {{
                                // Add table content
                                const rows = el.querySelectorAll('tr');
                                content.push('--- TABLA ---');
                                rows.forEach(row => {{
                                    const cells = row.querySelectorAll('th, td');
                                    const rowText = Array.from(cells).map(cell => 
                                        cell.textContent.trim().replace(/\\[.*?\\]/g, '')
                                    ).filter(text => text).join(' | ');
                                    if (rowText) {{
                                        content.push(rowText);
                                    }}
                                }});
                                content.push('--- FIN TABLA ---');
                                content.push('');
                            }}
                        }}
                    }} else {{
                        // Fallback: extract all text elements
                        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                        const paragraphs = document.querySelectorAll('p');
                        
                        headings.forEach(heading => {{
                            const text = heading.textContent.trim().replace(/\\[.*?\\]/g, '');
                            if (text) content.push(text.toUpperCase());
                        }});
                        
                        paragraphs.forEach(p => {{
                            const text = p.textContent.trim().replace(/\\[.*?\\]/g, '');
                            if (text && text.length > 20) content.push(text);
                        }});
                    }}
                    
                    // Create Word-compatible format
                    const docContent = content.filter(line => line !== undefined).join('\\n');
                    
                    // Download file
                    const blob = new Blob([docContent], {{ type: 'application/msword' }});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${{title.replace(/[^a-z0-9]/gi, '_')}}.doc`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    
                    console.log('Content extracted to Word format successfully');
                    return {{ success: true, message: 'Word file downloaded successfully', title: title }};
                }} catch (error) {{
                    console.error('Error during Word extraction:', error);
                    return {{ success: false, message: error.message }};
                }}
            }})();
            """
            
        else:  # TXT format
            return f"""
            (async function extractToText() {{
                {scrolling_code}
                
                // Extract all visible text
                const content = [];
                const textElements = document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, td, th, span, div');
                
                textElements.forEach(element => {{
                    const text = element.textContent.trim();
                    if (text && text.length > 10) {{ // Filter short/empty text
                        content.push(text);
                    }}
                }});
                
                // Remove duplicates and create final content
                const uniqueContent = [...new Set(content)];
                const finalText = uniqueContent.join('\\n\\n');
                
                // Download file
                const blob = new Blob([finalText], {{ type: 'text/plain' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'extracted_text.txt';
                a.click();
                URL.revokeObjectURL(url);
                
                console.log('Text extracted to TXT format');
            }})();
            """
    
    def create_extraction_plan(self, goal: str, extraction_details: Dict[str, Any]) -> str:
        """Create a plan for data extraction."""
        format_type = extraction_details.get('format', 'txt')
        needs_scrolling = extraction_details.get('needs_scrolling', False)
        
        plan_steps = [
            f"1. Navigate to the target webpage",
            f"2. Wait for page to fully load"
        ]
        
        if needs_scrolling:
            plan_steps.append("3. Slowly scroll through the entire page to load all content")
            plan_steps.append("4. Execute JavaScript extraction code")
        else:
            plan_steps.append("3. Execute JavaScript extraction code")
        
        plan_steps.append(f"5. Generate and download {format_type.upper()} file with extracted data")
        plan_steps.append("6. Verify file was created successfully")
        
        return "\n".join(plan_steps)
    
    def extract_page_content_simple(self, driver) -> Dict[str, Any]:
        """
        Extract page content using simple text extraction method.
        Returns temporary file path with extracted content.
        """
        try:
            print(f"[DEBUG] Extracting page content using simple text extraction...")
            
            # Use simple JavaScript compatible with older browsers
            simple_js = """
            function extractBodyText() {
                var text = document.body.innerText;
                return text ? text.replace(/^\\s+|\\s+$/g, '') : null;
            }
            
            var extractedText = extractBodyText();
            
            if (extractedText) {
                return {
                    success: true,
                    content: extractedText,
                    url: window.location.href,
                    title: document.title || 'Untitled Page'
                };
            } else {
                return {
                    success: false,
                    error: "No visible text found in the document body."
                };
            }
            """
            
            # Execute the simple JavaScript
            result = driver.execute_script(simple_js)
            
            if result and result.get('success'):
                # Create page content with metadata
                page_content = f"""URL: {result.get('url', 'Unknown')}
TITLE: {result.get('title', 'Unknown')}
EXTRACTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{result['content']}"""
                
                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
                temp_file.write(page_content)
                temp_file.close()
                
                return {
                    'success': True,
                    'temp_file': temp_file.name,
                    'url': result.get('url'),
                    'title': result.get('title'),
                    'content_length': len(result['content']),
                    'extraction_method': 'simple_text'
                }
            else:
                error_msg = result.get('error', 'Unknown extraction error') if result else 'No result from JavaScript'
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            print(f"[DEBUG] Simple extraction failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def auto_trigger_excel_generation(self) -> bool:
        """
        Automatically trigger Excel generation if temp files exist.
        This is called when extraction goals involve Excel output.
        """
        try:
            import subprocess
            import os
            
            # Check if process_temp_files_to_excel.py exists
            script_path = os.path.join(os.path.dirname(__file__), "process_temp_files_to_excel.py")
            if os.path.exists(script_path):
                print("[AUTO-EXCEL] Triggering Excel generation dialog...")
                
                # Execute the script to show file dialog and generate Excel
                result = subprocess.run([
                    'python', script_path
                ], cwd=os.path.dirname(__file__))
                
                return result.returncode == 0
            else:
                print("[AUTO-EXCEL] Excel generation script not found")
                return False
                
        except Exception as e:
            print(f"[AUTO-EXCEL] Error triggering Excel generation: {e}")
            return False
    
    def process_multiple_pages(self, temp_files: List[str], output_format: str, output_path: str = None) -> Dict[str, Any]:
        """
        Process multiple temporary text files using TextProcessorAgent.
        
        Args:
            temp_files: List of temporary file paths containing raw text
            output_format: 'txt', 'word', 'csv', 'excel'
            output_path: Optional output path
            
        Returns:
            Dict with success status, file path, and metadata
        """
        try:
            from text_processor_agent import TextProcessorAgent
            processor = TextProcessorAgent(self.client)
            
            result = processor.process_multiple_pages(temp_files, output_format, output_path)
            
            # Clean up temporary files
            processor.cleanup_temp_files()
            
            return result
            
        except Exception as e:
            print(f"[DEBUG] Multi-page processing failed: {e}")
            return {'success': False, 'error': str(e)}
