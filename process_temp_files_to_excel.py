#!/usr/bin/env python3
"""
Script to process existing temporary files and generate Excel
"""
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Configure API key for processing
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "test_key")

try:
    from safe_print_utils import safe_print_global as safe_print
    from content_processor import ContentProcessor
    from file_generator import FileGenerator
    from llm_controller import LLMController
    import tempfile
    
    def process_temp_files_to_document(original_objective=None):
        """Process existing temporary files and generate appropriate document based on objective"""
        
        safe_print("=== PROCESSING TEMPORARY FILES TO DOCUMENT ===")
        
        # Use provided objective or default
        if original_objective:
            safe_print(f"[OBJECTIVE] Using provided objective: {original_objective}")
        else:
            original_objective = "Process and structure web content from extracted pages"
            safe_print(f"[OBJECTIVE] Using default objective: {original_objective}")
        
        # Search for recent temporary files (last 2 hours)
        temp_dir = Path(tempfile.gettempdir())
        temp_files = []
        cutoff_time = datetime.now().timestamp() - 7200  # 2 hours
        
        safe_print(f"[SEARCH] Searching temporary files in: {temp_dir}")
        
        for temp_file in temp_dir.glob("tmp*.txt"):
            try:
                if temp_file.stat().st_mtime > cutoff_time:
                    # Check if contains web content
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        content = f.read(100).lower()  # Read only first 100 chars
                        if any(word in content for word in ['http', 'www', 'title:', 'url:', 'extracted:']) or len(content) > 50:
                            temp_files.append({
                                'file': str(temp_file),
                                'size': temp_file.stat().st_size,
                                'modified': datetime.fromtimestamp(temp_file.stat().st_mtime)
                            })
            except Exception as e:
                continue
        
        if not temp_files:
            safe_print("[ERROR] No recent temporary files found")
            return False
            
        # Sort by modification date
        temp_files.sort(key=lambda x: x['modified'])
        
        safe_print(f"[FOUND] Found {len(temp_files)} temporary files:")
        for i, tf in enumerate(temp_files, 1):
            safe_print(f"  {i}. {Path(tf['file']).name} - {tf['size']:,} chars - {tf['modified'].strftime('%H:%M:%S')}")
        
        # Create extracted pages structure
        extracted_pages = []
        processed_results = []
        
        for i, tf in enumerate(temp_files[:3], 1):  # Only first 3
            try:
                with open(tf['file'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Try to extract URL from content if available
                url_from_content = "Unknown URL"
                title_from_content = f"Web Page {i}"
                
                try:
                    # Look for URL: pattern in the content
                    lines = content.split('\n')[:10]  # Check first 10 lines
                    for line in lines:
                        if line.startswith('URL:'):
                            url_from_content = line.replace('URL:', '').strip()
                        elif line.startswith('TITLE:'):
                            title_from_content = line.replace('TITLE:', '').strip()
                except:
                    pass
                
                page_data = {
                    'page_number': i,
                    'url': url_from_content,
                    'title': title_from_content,
                    'content': content,
                    'extracted_at': tf['modified'].isoformat(),
                    'content_length': len(content)
                }
                
                extracted_pages.append(page_data)
                safe_print(f"[PAGE {i}] Loaded: {len(content):,} characters")
                
            except Exception as e:
                safe_print(f"[ERROR] Error processing file {tf['file']}: {e}")
                continue
        
        if not extracted_pages:
            safe_print("[ERROR] Could not load pages")
            return False
        
        # Real LLM processing with flexible objectives
        safe_print("[LLM] Processing content with real LLM based on original objective...")
        
        # Initialize real LLM controller
        try:
            llm_controller = LLMController(os.getenv("GROQ_API_KEY", "test_key"))
        except Exception as e:
            safe_print(f"[ERROR] Could not initialize LLM: {e}")
            safe_print("[INFO] Continuing with basic content consolidation...")
            llm_controller = None
        
        # Determine output format from objective (table vs document format)
        objective_lower = original_objective.lower()
        wants_table_format = any(keyword in objective_lower for keyword in ['excel', 'tabla', 'table', 'spreadsheet', 'csv'])
        
        # Process each page with real LLM based on objective
        processed_content = []
        for page_data in extracted_pages:
            try:
                if llm_controller:
                    # Dynamic prompt based on objective and desired output format
                    if wants_table_format:
                        extraction_prompt = f"""
                        Task: "{original_objective}"
                        
                        Process this web page content according to the task above and format the results as a structured ASCII table:
                        
                        {page_data['content'][:10000]}
                        
                        Return the data in ASCII table format. For example:
                        | Column 1    | Column 2    | Column 3    |
                        |-------------|-------------|-------------|
                        | Data 1      | Data 2      | Data 3      |
                        | Data 4      | Data 5      | Data 6      |
                        
                        Structure the table columns based on what makes sense for the specific task.
                        Add a brief explanation after the table if needed.
                        """
                    else:
                        # Document format - any task the user specified
                        extraction_prompt = f"""
                        Task: "{original_objective}"
                        
                        Process this web page content according to the task specified above:
                        
                        {page_data['content'][:10000]}
                        
                        Complete the task as requested and return the results in a clear, well-organized format.
                        The task could be anything - extraction, analysis, summary, comparison, etc.
                        Follow the user's instructions exactly.
                        """
                    
                    try:
                        response = llm_controller.client.chat.completions.create(
                            model="moonshotai/kimi-k2-instruct",
                            messages=[
                                {"role": "system", "content": "You are an expert data processor. Follow the user's instructions exactly and return well-formatted content."},
                                {"role": "user", "content": extraction_prompt}
                            ],
                            temperature=0.4,
                        )
                        
                        llm_response = response.choices[0].message.content.strip()
                        
                        # Clean the response
                        if llm_response.startswith('```'):
                            llm_response = llm_response.replace('```', '').strip()
                        
                        processed_content.append({
                            'page_number': page_data['page_number'],
                            'url': page_data['url'],
                            'title': page_data['title'],
                            'processed_content': llm_response,
                            'original_length': len(page_data['content'])
                        })
                        
                        safe_print(f"[LLM {page_data['page_number']}] Content processed successfully")
                        
                    except Exception as e:
                        safe_print(f"[LLM {page_data['page_number']}] Error with LLM processing: {e}")
                        # Fallback to raw content snippet
                        processed_content.append({
                            'page_number': page_data['page_number'],
                            'url': page_data['url'],
                            'title': page_data['title'],
                            'processed_content': f"[RAW CONTENT PREVIEW - {len(page_data['content']):,} chars]\n\n{page_data['content'][:1000]}...",
                            'original_length': len(page_data['content'])
                        })
                
                else:
                    # Basic content processing without LLM
                    content_preview = page_data['content'][:1500] + "..." if len(page_data['content']) > 1500 else page_data['content']
                    processed_content.append({
                        'page_number': page_data['page_number'],
                        'url': page_data['url'],
                        'title': page_data['title'],
                        'processed_content': f"[CONTENT PREVIEW - LLM NOT AVAILABLE]\n\n{content_preview}",
                        'original_length': len(page_data['content'])
                    })
                
                safe_print(f"[PROCESS {page_data['page_number']}] Page processed successfully")
                
            except Exception as e:
                safe_print(f"[ERROR] Error processing page {page_data['page_number']}: {e}")
                continue
        
        if not processed_content:
            safe_print("[ERROR] No pages could be processed")
            return False
        
        # Consolidate results based on objective and desired format
        safe_print("[CONSOLIDATE] Consolidating processed content...")
        
        # Build final consolidated content based on format
        if wants_table_format:
            # For table format - ONLY LLM generated table data, no metadata
            consolidated_data = ""
            for content in processed_content:
                # Extract only the LLM processed content (tables)
                consolidated_data += content['processed_content'] + "\n\n"
        else:
            # For document format, create consolidated results based on the user's task
            consolidated_data = f"TASK RESULTS: {original_objective}\n\n"
            consolidated_data += f"Processing completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            consolidated_data += f"Pages analyzed: {len(processed_content)}\n\n"
            
            all_results = []
            for content in processed_content:
                all_results.append(f"Page {content['page_number']}: {content['processed_content']}")
            
            # If we have LLM, create a final consolidated result
            if llm_controller:
                try:
                    final_consolidation_prompt = f"""
                    Task: {original_objective}
                    
                    Consolidate these individual page results into a comprehensive final result:
                    
                    Individual Results:
                    {chr(10).join(all_results)}
                    
                    Provide a cohesive, well-structured result that fulfills the original task completely.
                    """
                    
                    response = llm_controller.client.chat.completions.create(
                        model="moonshotai/kimi-k2-instruct",
                        messages=[
                            {"role": "system", "content": "You are an expert at consolidating information. Complete the user's task exactly as specified."},
                            {"role": "user", "content": final_consolidation_prompt}
                        ],
                        # Removed max_tokens to allow complete response
                        temperature=0.1
                    )
                    
                    final_result = response.choices[0].message.content.strip()
                    consolidated_data += f"CONSOLIDATED RESULT:\n\n{final_result}\n\n"
                    safe_print("[CONSOLIDATE] Final result generated by LLM")
                    
                except Exception as e:
                    safe_print(f"[WARNING] Could not generate consolidated result: {e}")
                    consolidated_data += "INDIVIDUAL PAGE RESULTS:\n\n"
                    for content in processed_content:
                        consolidated_data += f"Page {content['page_number']}: {content['title']}\n"
                        consolidated_data += f"{content['processed_content']}\n\n"
            else:
                consolidated_data += "INDIVIDUAL PAGE RESULTS:\n\n"
                for content in processed_content:
                    consolidated_data += f"Page {content['page_number']}: {content['title']}\n"
                    consolidated_data += f"{content['processed_content']}\n\n"
        
        # Generate output file based on format preference
        if wants_table_format:
            safe_print("[EXCEL] Generating Excel file with pure table data...")
            file_type = "excel"
        else:
            safe_print("[WORD] Generating Word document with processed content...")
            file_type = "word"
        
        file_generator = FileGenerator()
        
        summary_info = {
            'pages_extracted': len(extracted_pages),
            'pages_processed': len(processed_content), 
            'total_content_chars': sum(p['content_length'] for p in extracted_pages),
            'processing_type': 'Table/Excel' if wants_table_format else 'Document/Word',
            'pages_info': [
                {
                    'page_number': p['page_number'],
                    'title': p['title'],
                    'url': p['url'],
                    'content_length': p['content_length']
                }
                for p in extracted_pages
            ]
        }
        
        if file_type == "excel":
            output_path = file_generator.generate_excel_file(
                consolidated_data,
                original_objective,
                summary_info
            )
        else:
            output_path = file_generator.generate_word_file(
                consolidated_data,
                original_objective,
                summary_info
            )
        
        if output_path:
            safe_print(f"[SUCCESS] File generated successfully: {output_path}")
            
            # Show success dialog
            file_generator.show_success_dialog(output_path)
            
            # Clean up used temporary files
            safe_print("[CLEANUP] Cleaning up temporary files...")
            for tf in temp_files[:3]:
                try:
                    os.remove(tf['file'])
                    safe_print(f"[DELETED] {Path(tf['file']).name}")
                except Exception as e:
                    safe_print(f"[WARNING] Could not delete {tf['file']}: {e}")
            
            return True
        else:
            safe_print("[ERROR] Error generating output file")
            return False
    
    if __name__ == "__main__":
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Process temporary files and generate documents')
        parser.add_argument('--goal', type=str, help='The original objective from the user')
        args = parser.parse_args()
        
        # Use the provided goal or None (will use default)
        user_goal = args.goal if args.goal else None
        
        success = process_temp_files_to_document(original_objective=user_goal)
        if success:
            safe_print("\n[COMPLETE] PROCESSING SUCCESSFUL!")
            safe_print("Output file generated with processed web content")
        else:
            safe_print("\n[ERROR] PROCESSING FAILED")
            
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you have all necessary modules")
except Exception as e:
    print(f"Unexpected error: {e}")
