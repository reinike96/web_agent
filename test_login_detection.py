#!/usr/bin/env python3
"""
Test script for the improved login detection system
"""

def test_login_detection():
    """Test the enhanced login detection"""
    print("=== TESTING LOGIN DETECTION SYSTEM ===\n")
    
    from page_analyzer import PageAnalyzer
    
    # Create dummy browser
    class DummyBrowser:
        def __init__(self):
            self.driver = None
    
    analyzer = PageAnalyzer(DummyBrowser())
    
    # Test Case 1: X.com login page
    print("TEST 1: X.com Login Page")
    x_elements = [
        {'tag': 'button', 'text': 'Mostrar m?s sobre sus opciones.', 'data-testid': None, 'type': 'button'},
        {'tag': 'button', 'text': 'Aceptar todas las cookies', 'data-testid': None, 'type': 'button'},  
        {'tag': 'button', 'text': 'Registrarse con Google', 'data-testid': 'google_placeholder_button', 'type': 'button'},
        {'tag': 'button', 'text': 'Registrarse con Apple', 'data-testid': 'apple_sign_in_button', 'type': 'button'},
        {'tag': 'button', 'text': 'Iniciar sesi?n', 'data-testid': 'loginButton', 'type': 'button'}
    ]
    
    result1 = analyzer.detect_login_or_captcha({'interactive_elements': {'elements': x_elements}})
    print(f"  Requires Intervention: {result1.get('requires_intervention', False)}")
    print(f"  Type: {result1.get('type', 'none')}")
    print(f"  Details: {result1.get('details', 'none')}")
    print(f"  Expected: Should detect login required\n")
    
    # Test Case 2: Regular Wikipedia page (no login needed)
    print("TEST 2: Wikipedia Page (No Login)")
    wiki_elements = [
        {'tag': 'input', 'text': '', 'data-testid': 'search-input', 'type': 'input'},
        {'tag': 'button', 'text': 'Search', 'data-testid': None, 'type': 'button'},
        {'tag': 'link', 'text': 'Article', 'data-testid': None, 'type': 'link'},
        {'tag': 'link', 'text': 'Read more', 'data-testid': None, 'type': 'link'}
    ]
    
    result2 = analyzer.detect_login_or_captcha({'interactive_elements': {'elements': wiki_elements}})
    print(f"  Requires Intervention: {result2.get('requires_intervention', False)}")
    print(f"  Type: {result2.get('type', 'none')}")
    print(f"  Details: {result2.get('details', 'none')}")
    print(f"  Expected: Should NOT require intervention\n")
    
    # Test Case 3: CAPTCHA page
    print("TEST 3: CAPTCHA Page")
    captcha_elements = [
        {'tag': 'div', 'text': 'Verify you are human', 'data-testid': None, 'type': 'div'},
        {'tag': 'button', 'text': 'I am not a robot', 'data-testid': None, 'type': 'button'},
    ]
    
    result3 = analyzer.detect_login_or_captcha({'interactive_elements': {'elements': captcha_elements}})
    print(f"  Requires Intervention: {result3.get('requires_intervention', False)}")
    print(f"  Type: {result3.get('type', 'none')}")
    print(f"  Details: {result3.get('details', 'none')}")
    print(f"  Expected: Should detect CAPTCHA\n")
    
    print("=== TESTING MANUAL INTERVENTION STEP DETECTION ===\n")
    
    from new_orchestrator import NewOrchestrator
    
    # Test manual intervention step detection
    test_steps = [
        "Navigate to x.com",
        "MANUAL_INTERVENTION: Complete login process if required", 
        "Click on Tweet button",
        "MANUAL INTERVENTION: Solve CAPTCHA if present",
        "Type message in composer"
    ]
    
    # Create dummy orchestrator (we just need the method)
    class TestOrchestrator:
        def is_manual_intervention_step(self, task: str) -> bool:
            clean_task = task.strip().upper()
            return "MANUAL_INTERVENTION" in clean_task or "MANUAL INTERVENTION" in clean_task
    
    orchestrator = TestOrchestrator()
    
    for step in test_steps:
        is_manual = orchestrator.is_manual_intervention_step(step)
        print(f"Step: {step}")
        print(f"  Manual Intervention: {is_manual}")
        print()

if __name__ == "__main__":
    test_login_detection()
