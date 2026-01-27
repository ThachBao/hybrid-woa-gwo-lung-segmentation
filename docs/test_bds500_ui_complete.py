"""
Test script for BDS500 UI integration - Complete verification
Tests both backend API and frontend files
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_backend_api():
    """Test that backend API is properly configured"""
    print("=" * 60)
    print("TEST 1: Backend API")
    print("=" * 60)
    
    try:
        from src.ui.app import app
        
        # Check if /api/eval_bds500 endpoint exists
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        
        if '/api/eval_bds500' in rules:
            print("✓ /api/eval_bds500 endpoint exists")
        else:
            print("✗ /api/eval_bds500 endpoint NOT FOUND")
            return False
        
        # Check if endpoint accepts POST
        for rule in app.url_map.iter_rules():
            if str(rule) == '/api/eval_bds500':
                if 'POST' in rule.methods:
                    print("✓ Endpoint accepts POST method")
                else:
                    print("✗ Endpoint does NOT accept POST")
                    return False
        
        print("\n✅ Backend API test PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Backend API test FAILED: {e}\n")
        return False


def test_frontend_html():
    """Test that HTML contains BDS500 evaluation tab"""
    print("=" * 60)
    print("TEST 2: Frontend HTML")
    print("=" * 60)
    
    html_path = os.path.join('src', 'ui', 'templates', 'index.html')
    
    if not os.path.exists(html_path):
        print(f"✗ HTML file not found: {html_path}\n")
        return False
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('data-tab="bds500eval"', 'Tab button exists'),
        ('id="tabBDS500Eval"', 'Tab content container exists'),
        ('id="formBDS500Eval"', 'Evaluation form exists'),
        ('id="btnEvalBDS500"', 'Submit button exists'),
        ('id="evalProgress"', 'Progress indicator exists'),
        ('id="evalResults"', 'Results container exists'),
        ('name="split"', 'Split selector exists'),
        ('name="algorithms"', 'Algorithm checkboxes exist'),
        ('name="k"', 'K parameter input exists'),
        ('name="seed"', 'Seed parameter input exists'),
    ]
    
    all_passed = True
    for check_str, description in checks:
        if check_str in content:
            print(f"✓ {description}")
        else:
            print(f"✗ {description} - NOT FOUND")
            all_passed = False
    
    if all_passed:
        print("\n✅ Frontend HTML test PASSED\n")
    else:
        print("\n✗ Frontend HTML test FAILED\n")
    
    return all_passed


def test_frontend_javascript():
    """Test that JavaScript contains BDS500 handlers"""
    print("=" * 60)
    print("TEST 3: Frontend JavaScript")
    print("=" * 60)
    
    js_path = os.path.join('src', 'ui', 'static', 'app.js')
    
    if not os.path.exists(js_path):
        print(f"✗ JavaScript file not found: {js_path}\n")
        return False
    
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('formBDS500Eval', 'Form reference exists'),
        ('btnEvalBDS500', 'Button reference exists'),
        ('evalProgress', 'Progress reference exists'),
        ('evalResults', 'Results reference exists'),
        ("tabName === 'bds500eval'", 'Tab switching logic exists'),
        ("'/api/eval_bds500'", 'API endpoint call exists'),
        ('displayBDS500Results', 'Results display function exists'),
        ('algo_stats', 'Algorithm statistics handling exists'),
        ('dice_mean', 'DICE score handling exists'),
    ]
    
    all_passed = True
    for check_str, description in checks:
        if check_str in content:
            print(f"✓ {description}")
        else:
            print(f"✗ {description} - NOT FOUND")
            all_passed = False
    
    if all_passed:
        print("\n✅ Frontend JavaScript test PASSED\n")
    else:
        print("\n✗ Frontend JavaScript test FAILED\n")
    
    return all_passed


def test_frontend_css():
    """Test that CSS contains BDS500 styling"""
    print("=" * 60)
    print("TEST 4: Frontend CSS")
    print("=" * 60)
    
    css_path = os.path.join('src', 'ui', 'static', 'index.css')
    
    if not os.path.exists(css_path):
        print(f"✗ CSS file not found: {css_path}\n")
        return False
    
    with open(css_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('.bds500-eval-container', 'Main container style exists'),
        ('.bds500-eval-header', 'Header style exists'),
        ('.bds500-eval-layout', 'Layout style exists'),
        ('.bds500-eval-form-card', 'Form card style exists'),
        ('.eval-algo-grid', 'Algorithm grid style exists'),
        ('.eval-progress', 'Progress style exists'),
        ('.progress-bar', 'Progress bar style exists'),
        ('.eval-logs', 'Logs style exists'),
        ('.bds500-eval-results-card', 'Results card style exists'),
        ('.summary-grid', 'Summary grid style exists'),
        ('.algo-comparison-table', 'Comparison table style exists'),
        ('.warning-banner', 'Warning banner style exists'),
    ]
    
    all_passed = True
    for check_str, description in checks:
        if check_str in content:
            print(f"✓ {description}")
        else:
            print(f"✗ {description} - NOT FOUND")
            all_passed = False
    
    if all_passed:
        print("\n✅ Frontend CSS test PASSED\n")
    else:
        print("\n✗ Frontend CSS test FAILED\n")
    
    return all_passed


def test_integration_completeness():
    """Test that all components are properly integrated"""
    print("=" * 60)
    print("TEST 5: Integration Completeness")
    print("=" * 60)
    
    # Check that all files exist
    files = [
        ('src/ui/app.py', 'Backend API'),
        ('src/ui/templates/index.html', 'HTML template'),
        ('src/ui/static/app.js', 'JavaScript'),
        ('src/ui/static/index.css', 'CSS'),
        ('src/runner/eval_bds500_k10_seed42.py', 'Evaluation script'),
        ('src/data/bsds500.py', 'Dataset loader'),
    ]
    
    all_exist = True
    for filepath, description in files:
        if os.path.exists(filepath):
            print(f"✓ {description}: {filepath}")
        else:
            print(f"✗ {description}: {filepath} - NOT FOUND")
            all_exist = False
    
    if all_exist:
        print("\n✅ Integration completeness test PASSED\n")
    else:
        print("\n✗ Integration completeness test FAILED\n")
    
    return all_exist


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("BDS500 UI INTEGRATION - COMPLETE TEST SUITE")
    print("=" * 60 + "\n")
    
    results = []
    
    results.append(("Backend API", test_backend_api()))
    results.append(("Frontend HTML", test_frontend_html()))
    results.append(("Frontend JavaScript", test_frontend_javascript()))
    results.append(("Frontend CSS", test_frontend_css()))
    results.append(("Integration Completeness", test_integration_completeness()))
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:30s} {status}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! BDS500 UI integration is complete.\n")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the output above.\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
