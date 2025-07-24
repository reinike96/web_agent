# Test JavaScript extraction
from browser_controller import BrowserController
import time

print('Testing JavaScript execution...')
browser = BrowserController()

if not browser.driver:
    print('Failed to initialize browser')
    exit(1)

try:
    browser.navigate_to('https://x.com/home')
    time.sleep(5)
    
    # Test simple JavaScript first
    print('Testing simple JavaScript...')
    result1 = browser.driver.execute_script('return document.title;')
    print('Document title:', result1)
    
    # Test IIFE structure
    print('Testing IIFE structure...')
    iife_test = r"""
    return (function() { 
        return {test: "hello", buttons: document.querySelectorAll("button").length}; 
    })();
    """
    result2 = browser.driver.execute_script(iife_test)
    print('IIFE result:', result2)
    
    # Test the actual extraction script
    print('Testing extraction script...')
    js_file_path = r'c:\Users\ALEXR\OneDrive\Desktop\Browser\web_agent\extractJsonInteractive_simple.js'
    with open(js_file_path, 'r', encoding='utf-8') as file:
        extraction_js = file.read()
    
    # Add explicit return at the start 
    extraction_js_with_return = "return " + extraction_js
    
    result3 = browser.driver.execute_script(extraction_js_with_return)
    print('Extraction result type:', type(result3))
    print('Extraction result:', result3)
    
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
finally:
    if hasattr(browser, 'driver') and browser.driver:
        browser.driver.quit()
