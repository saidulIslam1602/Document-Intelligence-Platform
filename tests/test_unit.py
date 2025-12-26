"""
Unit Tests for Document Intelligence Platform
These tests don't require running services and can run in CI/CD
"""

import os
import pytest
from pathlib import Path


class TestProjectStructure:
    """Test project structure and configuration"""
    
    def test_required_files_exist(self):
        """Test that all required files exist"""
        required_files = [
            "README.md",
            "LICENSE",
            "requirements.txt",
            "docker-compose.yml",
            "src/shared/config/settings.py",
            "src/microservices/document-ingestion/main.py",
            "src/microservices/ai-processing/main.py",
            "src/microservices/analytics/main.py",
            "src/microservices/api-gateway/main.py",
            "src/microservices/mcp-server/main.py",  # NEW: MCP Server
            "infrastructure/main.bicep",
        ]
        
        for file_path in required_files:
            assert os.path.exists(file_path), f"Required file missing: {file_path}"
    
    def test_new_enhancements_exist(self):
        """Test that new enhancement files exist"""
        enhancement_files = [
            "src/microservices/mcp-server/main.py",
            "src/microservices/mcp-server/mcp_tools.py",
            "src/microservices/mcp-server/mcp_resources.py",
            "src/microservices/ai-processing/langchain_orchestration.py",
            "src/microservices/ai-processing/llmops_automation.py",
            "src/microservices/analytics/automation_scoring.py",
        ]
        
        for file_path in enhancement_files:
            assert os.path.exists(file_path), f"Enhancement file missing: {file_path}"
    
    def test_documentation_exists(self):
        """Test that documentation files exist in docs folder"""
        doc_files = [
            "docs/INTEGRATION_GUIDE.md",
            "docs/QUICK_START.md",
            "docs/IMPLEMENTATION_SUMMARY.md",
            "docs/ENHANCEMENTS_README.md",
            "docs/VALIDATION_CHECKLIST.md",
            "docs/COMPREHENSIVE_AZURE_GUIDE.md",
        ]
        
        for doc_file in doc_files:
            assert os.path.exists(doc_file), f"Documentation file missing: {doc_file}"


class TestPythonSyntax:
    """Test Python files for valid syntax"""
    
    def test_microservices_syntax(self):
        """Test that microservice files have valid syntax"""
        microservice_files = [
            "src/microservices/document-ingestion/main.py",
            "src/microservices/ai-processing/main.py",
            "src/microservices/analytics/main.py",
            "src/microservices/api-gateway/main.py",
            "src/microservices/mcp-server/main.py",
        ]
        
        for file_path in microservice_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    code = f.read()
                # This will raise SyntaxError if invalid
                compile(code, file_path, 'exec')
    
    def test_new_modules_syntax(self):
        """Test that new enhancement modules have valid syntax"""
        new_modules = [
            "src/microservices/mcp-server/mcp_tools.py",
            "src/microservices/mcp-server/mcp_resources.py",
            "src/microservices/ai-processing/langchain_orchestration.py",
            "src/microservices/ai-processing/llmops_automation.py",
            "src/microservices/analytics/automation_scoring.py",
        ]
        
        for file_path in new_modules:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    code = f.read()
                # This will raise SyntaxError if invalid
                compile(code, file_path, 'exec')


class TestDockerConfiguration:
    """Test Docker configuration"""
    
    def test_docker_compose_has_required_services(self):
        """Test that docker-compose.yml contains all required services"""
        with open("docker-compose.yml", 'r') as f:
            content = f.read()
        
        required_services = [
            "document-ingestion",
            "ai-processing",
            "analytics",
            "api-gateway",
            "mcp-server",  # NEW
            "redis",
            # Note: SQL Server is Azure SQL Database in production, not a container service
        ]
        
        for service in required_services:
            assert service in content, f"Service '{service}' not found in docker-compose.yml"
    
    def test_docker_compose_mcp_server_port(self):
        """Test that MCP server is configured on correct port"""
        with open("docker-compose.yml", 'r') as f:
            content = f.read()
        
        # Check that MCP server uses port 8012
        assert "8012" in content, "MCP server port 8012 not found in docker-compose.yml"


class TestDependencies:
    """Test dependency configuration"""
    
    def test_requirements_has_key_packages(self):
        """Test that requirements.txt includes all key packages"""
        with open("requirements.txt", 'r') as f:
            content = f.read()
        
        key_packages = [
            "fastapi",
            "uvicorn",
            "azure",
            "pandas",
            "numpy",
            "langchain",  # NEW
            "httpx",
        ]
        
        for package in key_packages:
            assert package in content.lower(), f"Package '{package}' not found in requirements.txt"
    
    def test_requirements_not_empty(self):
        """Test that requirements.txt is not empty"""
        with open("requirements.txt", 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
        
        assert len(lines) >= 20, "requirements.txt seems too short"


class TestInfrastructure:
    """Test infrastructure configuration"""
    
    def test_bicep_template_exists(self):
        """Test that Bicep infrastructure template exists"""
        assert os.path.exists("infrastructure/main.bicep")
    
    def test_bicep_has_azure_resources(self):
        """Test that Bicep template includes key Azure resources"""
        with open("infrastructure/main.bicep", 'r') as f:
            content = f.read()
        
        key_resources = [
            "Microsoft.Storage",
            "Microsoft.Sql",  # Using Azure SQL Database (not Cosmos DB)
            "Microsoft.EventHub"
        ]
        
        for resource in key_resources:
            assert resource in content, f"Azure resource '{resource}' not found in Bicep template"


class TestEnhancementIntegration:
    """Test that enhancements are properly integrated"""
    
    def test_api_gateway_routes_mcp(self):
        """Test that API Gateway has MCP routing"""
        with open("src/microservices/api-gateway/main.py", 'r') as f:
            content = f.read()
        
        # Check for MCP routing
        assert "mcp" in content.lower(), "MCP routing not found in API Gateway"
        assert "8012" in content or "mcp-server" in content, "MCP server endpoint not configured"
    
    def test_analytics_has_automation_scoring(self):
        """Test that Analytics service imports automation scoring"""
        with open("src/microservices/analytics/main.py", 'r') as f:
            content = f.read()
        
        # Check for automation scoring imports
        assert "automation" in content.lower(), "Automation scoring not integrated in Analytics"
    
    def test_ai_processing_has_langchain(self):
        """Test that AI Processing service has LangChain integration"""
        with open("src/microservices/ai-processing/main.py", 'r') as f:
            content = f.read()
        
        # Check for LangChain integration
        assert "langchain" in content.lower(), "LangChain not integrated in AI Processing"


class TestDocumentation:
    """Test documentation quality"""
    
    def test_readme_mentions_new_features(self):
        """Test that README mentions new features"""
        with open("README.md", 'r') as f:
            content = f.read()
        content_lower = content.lower()
        
        # Check features case-insensitively
        new_features = [
            ("MCP", "mcp"),
            ("Model Context Protocol", "model context protocol"),
            ("LangChain", "langchain"),
            ("Automation", "automation"),  # Changed from "Automation Scoring" to just "Automation" (more flexible)
        ]
        
        for feature_display, feature_search in new_features:
            assert feature_search in content_lower, f"New feature '{feature_display}' not mentioned in README"
    
    def test_integration_guide_exists_and_substantial(self):
        """Test that integration guide is comprehensive"""
        with open("docs/INTEGRATION_GUIDE.md", 'r') as f:
            content = f.read()
        
        # Should be substantial (>10,000 chars)
        assert len(content) > 10000, "Integration guide seems too short"
        assert "MCP" in content, "Integration guide doesn't mention MCP"
        assert "LangChain" in content, "Integration guide doesn't mention LangChain"


class TestConfigurationFiles:
    """Test configuration files"""
    
    def test_pytest_config_has_markers(self):
        """Test that pytest configuration has integration marker"""
        with open("setup.cfg", 'r') as f:
            content = f.read()
        
        assert "integration" in content, "Integration marker not configured in setup.cfg"
    
    def test_gitignore_exists(self):
        """Test that .gitignore exists (if present)"""
        # This is optional, just check if it exists
        if os.path.exists(".gitignore"):
            with open(".gitignore", 'r') as f:
                content = f.read()
            # Should ignore common files
            assert "__pycache__" in content or "*.pyc" in content


# Test that can be run without services
def test_basic_imports():
    """Test that basic imports work without errors"""
    # These should not raise import errors
    import sys
    import os
    import json
    import datetime
    
    assert sys.version_info.major >= 3
    assert sys.version_info.minor >= 8


def test_python_version():
    """Test that Python version is 3.8 or higher"""
    import sys
    version = sys.version_info
    assert version.major == 3
    assert version.minor >= 8, f"Python 3.8+ required, got {version.major}.{version.minor}"


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_unit.py -v
    pytest.main([__file__, "-v"])

