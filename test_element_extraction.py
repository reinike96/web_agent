# Test the enhanced action controller element extraction
from enhanced_action_controller import EnhancedActionController
from browser_controller import BrowserController
from llm_controller import LLMController
import time

print('Testing Enhanced Action Controller element extraction...')

# Initialize components
browser = BrowserController()
if not browser.driver:
    print('Failed to initialize browser')
    exit(1)

llm = LLMController('dummy_key')  # Use dummy key for testing
controller = EnhancedActionController(browser, llm)

try:
    # Navigate to X.com
    browser.navigate_to('https://x.com/home')
    time.sleep(5)
    
    # Test the element extraction part only
    print('Testing element extraction...')
    js_file_path = r'c:\Users\ALEXR\OneDrive\Desktop\Browser\web_agent\extractJsonInteractive_simple.js'
    with open(js_file_path, 'r', encoding='utf-8') as file:
        extraction_js = file.read()
    
    # Add return and execute
    extraction_js_with_return = 'return ' + extraction_js
    current_elements = browser.driver.execute_script(extraction_js_with_return)
    
    print('Elements extracted successfully!')
    elements = current_elements.get('elements', [])
    print(f'Element count: {len(elements)}')
    
    if elements:
        print('First 3 elements:')
        for i, elem in enumerate(elements[:3]):
            print(f'  {i+1}: {elem["tag"]} - {elem["text"]} - {elem["selector"]}')
    
    # Now test if the LLM fallback would work with these elements
    print('\nTesting LLM fallback simulation...')
    action = {'action': 'click_button', 'parameters': {'keywords': ['post', 'tweet', 'send']}}
    page_info = {}  # Empty to force fallback
    
    # Simulate what happens in the fallback (without calling LLM)
    print('Action:', action['action'])
    print('Parameters:', action['parameters'])
    print('Available elements count:', len(elements))
    
    # Look for matching elements
    keywords = action['parameters'].get('keywords', [])
    matching_elements = []
    for elem in elements:
        text = elem.get('text', '').lower() if elem.get('text') else ''
        for keyword in keywords:
            if keyword.lower() in text:
                matching_elements.append(elem)
                break
    
    print(f'Elements matching keywords {keywords}: {len(matching_elements)}')
    for elem in matching_elements:
        print(f'  - {elem["tag"]} "{elem["text"]}" -> {elem["selector"]}')
    
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
finally:
    if hasattr(browser, 'driver') and browser.driver:
        browser.driver.quit()
