# Simple test of JavaScript extraction and matching
from browser_controller import BrowserController
import time

print('Testing JavaScript extraction on X.com...')

browser = BrowserController()
if not browser.driver:
    print('Failed to initialize browser')
    exit(1)

try:
    # Navigate to X.com
    browser.navigate_to('https://x.com/home')
    time.sleep(8)  # Wait longer for page to load
    
    print('Current URL:', browser.driver.current_url)
    print('Page title:', browser.driver.title)
    
    # Test the element extraction
    print('\nTesting element extraction...')
    js_file_path = r'c:\Users\ALEXR\OneDrive\Desktop\Browser\web_agent\extractJsonInteractive_simple.js'
    with open(js_file_path, 'r', encoding='utf-8') as file:
        extraction_js = file.read()
    
    # Add return and execute
    extraction_js_with_return = 'return ' + extraction_js
    current_elements = browser.driver.execute_script(extraction_js_with_return)
    
    print('Elements extracted successfully!')
    elements = current_elements.get('elements', [])
    print(f'Total elements found: {len(elements)}')
    
    if elements:
        print('\nAll elements:')
        for i, elem in enumerate(elements):
            text = elem.get('text', 'No text')
            tag = elem.get('tag', 'Unknown')
            selector = elem.get('selector', 'No selector')
            print(f'  {i+1}: {tag} - "{text}" -> {selector}')
    
    # Test matching for post/tweet/send keywords
    print('\nTesting keyword matching for ["post", "tweet", "send"]:')
    keywords = ['post', 'tweet', 'send']
    matching_elements = []
    
    for elem in elements:
        text = elem.get('text', '').lower() if elem.get('text') else ''
        aria_label = elem.get('aria-label', '').lower() if elem.get('aria-label') else ''
        data_testid = elem.get('data-testid', '').lower() if elem.get('data-testid') else ''
        
        search_text = f'{text} {aria_label} {data_testid}'
        
        for keyword in keywords:
            if keyword.lower() in search_text:
                matching_elements.append((elem, keyword, search_text))
                break
    
    print(f'Found {len(matching_elements)} matching elements:')
    for elem, keyword, search_text in matching_elements:
        print(f'  - {elem["tag"]} "{elem.get("text", "")}" (matched "{keyword}" in "{search_text.strip()}") -> {elem["selector"]}')

except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
finally:
    if hasattr(browser, 'driver') and browser.driver:
        browser.driver.quit()
