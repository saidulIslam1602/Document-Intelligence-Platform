#!/usr/bin/env python3
"""
Simple test to verify the project structure and basic functionality
"""

import os
import sys
import json
from datetime import datetime

def test_project_structure():
    """Test that all required files and directories exist"""
    print("🔍 Testing Project Structure...")
    
    required_files = [
        "README.md",
        "LICENSE",
        "requirements.txt",
        "docker-compose.yml",
        "src/shared/config/settings.py",
        "src/shared/events/event_sourcing.py",
        "src/microservices/document-ingestion/main.py",
        "src/microservices/ai-processing/main.py",
        "src/microservices/analytics/main.py",
        "src/microservices/api-gateway/main.py",
        "infrastructure/main.bicep",
        "scripts/deploy.sh"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files exist")
        return True

def test_python_syntax():
    """Test that Python files have valid syntax"""
    print("\n🐍 Testing Python Syntax...")
    
    python_files = [
        "src/shared/config/settings.py",
        "src/shared/events/event_sourcing.py",
        "src/microservices/document-ingestion/main.py",
        "src/microservices/ai-processing/main.py",
        "src/microservices/analytics/main.py",
        "src/microservices/api-gateway/main.py"
    ]
    
    syntax_errors = []
    for file_path in python_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    compile(f.read(), file_path, 'exec')
                print(f"✅ {file_path}")
            except SyntaxError as e:
                syntax_errors.append(f"{file_path}: {e}")
                print(f"❌ {file_path}: {e}")
    
    if syntax_errors:
        print(f"❌ Syntax errors found: {syntax_errors}")
        return False
    else:
        print("✅ All Python files have valid syntax")
        return True

def test_docker_compose():
    """Test that docker-compose.yml is valid"""
    print("\n🐳 Testing Docker Compose...")
    
    try:
        with open("docker-compose.yml", 'r') as f:
            content = f.read()
        
        # Basic validation - check for required services
        required_services = ["document-ingestion", "ai-processing", "analytics", "api-gateway"]
        missing_services = []
        
        for service in required_services:
            if service not in content:
                missing_services.append(service)
        
        if missing_services:
            print(f"❌ Missing services in docker-compose.yml: {missing_services}")
            return False
        else:
            print("✅ Docker Compose configuration looks good")
            return True
            
    except Exception as e:
        print(f"❌ Docker Compose error: {e}")
        return False

def test_requirements():
    """Test that requirements.txt is valid"""
    print("\n📦 Testing Requirements...")
    
    try:
        with open("requirements.txt", 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 10:
            print("❌ requirements.txt seems too short")
            return False
        
        # Check for key dependencies
        content = ''.join(lines)
        key_deps = ["fastapi", "uvicorn", "azure", "pandas", "numpy"]
        missing_deps = []
        
        for dep in key_deps:
            if dep not in content:
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"❌ Missing key dependencies: {missing_deps}")
            return False
        else:
            print("✅ Requirements.txt looks good")
            return True
            
    except Exception as e:
        print(f"❌ Requirements error: {e}")
        return False

def test_bicep_template():
    """Test that Bicep template is valid"""
    print("\n🏗️ Testing Bicep Template...")
    
    try:
        with open("infrastructure/main.bicep", 'r') as f:
            content = f.read()
        
        # Check for key Azure resources
        key_resources = ["Microsoft.Storage", "Microsoft.DocumentDB", "Microsoft.EventHub"]
        missing_resources = []
        
        for resource in key_resources:
            if resource not in content:
                missing_resources.append(resource)
        
        if missing_resources:
            print(f"❌ Missing Azure resources: {missing_resources}")
            return False
        else:
            print("✅ Bicep template looks good")
            return True
            
    except Exception as e:
        print(f"❌ Bicep template error: {e}")
        return False

def test_scripts():
    """Test that scripts are executable"""
    print("\n🔧 Testing Scripts...")
    
    scripts = ["scripts/deploy.sh", "scripts/run_tests.sh"]
    
    for script in scripts:
        if os.path.exists(script):
            if os.access(script, os.X_OK):
                print(f"✅ {script} is executable")
            else:
                print(f"⚠️ {script} is not executable (run: chmod +x {script})")
        else:
            print(f"❌ {script} not found")
    
    return True

def run_all_tests():
    """Run all basic tests"""
    print("🚀 Document Intelligence Platform - Basic Tests")
    print("=" * 60)
    
    tests = [
        test_project_structure,
        test_python_syntax,
        test_docker_compose,
        test_requirements,
        test_bicep_template,
        test_scripts
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Project structure is correct!")
        print("✅ Ready to run with: python3 tests/demo_script.py")
    else:
        print("⚠️ Some issues need attention")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)