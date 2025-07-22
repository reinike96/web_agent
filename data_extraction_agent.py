"""
Data Extraction Agent for intelligent web data extraction with JavaScript generation.
Handles multiple output formats (TXT, Excel, Word) with automatic format detection.
"""

import re
import json
from typing import Dict, Any, Tuple, Optional
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
        
        # Extraction keywords for intent detection
        self.extraction_keywords = [
            'extract', 'extraer', 'download', 'descargar', 'save', 'guardar',
            'export', 'exportar', 'scrape', 'obtain', 'obtener', 'collect',
            'recopilar', 'gather', 'datos', 'data', 'información', 'information'
        ]
        
        # Format keywords
        self.format_keywords = {
            'excel': ['excel', 'xlsx', 'xls', 'spreadsheet', 'hoja de cálculo'],
            'word': ['word', 'docx', 'doc', 'document', 'documento'],
            'txt': ['txt', 'text', 'texto', 'plain text']
        }
    
    def detect_extraction_intent(self, goal: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Detect if the goal involves data extraction and determine the details.
        
        Returns:
            tuple: (is_extraction, extraction_details)
        """
        goal_lower = goal.lower()
        
        # Check for extraction keywords
        has_extraction_keywords = any(keyword in goal_lower for keyword in self.extraction_keywords)
        
        if not has_extraction_keywords:
            return False, {}
        
        # Determine output format
        detected_format = 'txt'  # Default format
        for format_type, keywords in self.format_keywords.items():
            if any(keyword in goal_lower for keyword in keywords):
                detected_format = format_type
                break
        
        # Extract target content hints
        target_hints = []
        content_patterns = [
            r'table[s]?', r'lista[s]?', r'list[s]?', r'datos?', r'data',
            r'información', r'information', r'texto', r'text', r'contenido', r'content'
        ]
        
        for pattern in content_patterns:
            if re.search(pattern, goal_lower):
                target_hints.append(pattern)
        
        extraction_details = {
            'format': detected_format,
            'target_hints': target_hints,
            'goal': goal,
            'needs_scrolling': any(word in goal_lower for word in ['slow', 'lento', 'complete', 'completo', 'all', 'todo'])
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
                max_tokens=2000,
                temperature=0.1
            )
            
            js_code = response.choices[0].message.content.strip()
            
            # Clean and validate the JavaScript code
            js_code = self._clean_javascript_code(js_code)
            
            return js_code
            
        except Exception as e:
            # Fallback to template-based generation
            return self._generate_fallback_extraction_code(format_type, goal, needs_scrolling)
    
    def _clean_javascript_code(self, js_code: str) -> str:
        """Clean and validate JavaScript code."""
        # Remove markdown code blocks if present
        js_code = re.sub(r'^```(?:javascript|js)?\n?', '', js_code, flags=re.MULTILINE)
        js_code = re.sub(r'\n?```$', '', js_code, flags=re.MULTILINE)
        
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
                {scrolling_code}
                
                // Extract data from tables and lists
                const data = [];
                const tables = document.querySelectorAll('table');
                const lists = document.querySelectorAll('ul, ol');
                
                // Extract table data
                tables.forEach(table => {{
                    const rows = table.querySelectorAll('tr');
                    rows.forEach(row => {{
                        const cells = row.querySelectorAll('td, th');
                        const rowData = Array.from(cells).map(cell => cell.textContent.trim());
                        if (rowData.length > 0) data.push(rowData);
                    }});
                }});
                
                // Extract list data
                lists.forEach(list => {{
                    const items = list.querySelectorAll('li');
                    items.forEach(item => {{
                        data.push([item.textContent.trim()]);
                    }});
                }});
                
                // Create CSV format for Excel
                const csvContent = data.map(row => 
                    row.map(cell => `"${{cell}}"`).join(',')
                ).join('\\n');
                
                // Download file
                const blob = new Blob([csvContent], {{ type: 'text/csv' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'extracted_data.csv';
                a.click();
                URL.revokeObjectURL(url);
                
                console.log('Data extracted to Excel format');
            }})();
            """
            
        elif format_type == 'word':
            return f"""
            (async function extractToWord() {{
                {scrolling_code}
                
                // Extract text content
                const content = [];
                const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                const paragraphs = document.querySelectorAll('p');
                const lists = document.querySelectorAll('ul, ol');
                
                headings.forEach(heading => {{
                    content.push(heading.textContent.trim());
                }});
                
                paragraphs.forEach(p => {{
                    const text = p.textContent.trim();
                    if (text) content.push(text);
                }});
                
                lists.forEach(list => {{
                    const items = list.querySelectorAll('li');
                    items.forEach(item => {{
                        content.push('• ' + item.textContent.trim());
                    }});
                }});
                
                // Create Word-compatible format
                const docContent = content.join('\\n\\n');
                
                // Download file
                const blob = new Blob([docContent], {{ type: 'application/msword' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'extracted_content.doc';
                a.click();
                URL.revokeObjectURL(url);
                
                console.log('Content extracted to Word format');
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
