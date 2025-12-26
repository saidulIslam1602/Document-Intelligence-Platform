#!/usr/bin/env python3
"""Fix all __init__.py files to properly export classes"""
import os
import re

# Define the modules and their exports
exports = {
    "src/shared/auth/__init__.py": ["AuthService"],
    "src/shared/cache/__init__.py": ["RedisCache", "cache_service"],
    "src/shared/config/__init__.py": ["config_manager", "ConfigManager"],
    "src/shared/events/__init__.py": ["EventStore", "EventBus", "DocumentUploadedEvent", "EventType"],
    "src/shared/health/__init__.py": ["HealthCheck"],
    "src/shared/http/__init__.py": ["HTTPClient"],
    "src/shared/monitoring/__init__.py": ["PerformanceMonitor", "monitor_performance"],
    "src/shared/resilience/__init__.py": ["CircuitBreaker", "RetryPolicy"],
    "src/shared/routing/__init__.py": ["IntelligentRouter"],
    "src/shared/services/__init__.py": ["ServiceRegistry"],
    "src/shared/storage/__init__.py": ["DataLakeService", "SQLService", "BlobStorageService"],
    "src/shared/utils/__init__.py": ["Logger", "Validator"],
}

for file_path, exports_list in exports.items():
    if os.path.exists(file_path):
        # Get module name from file path
        module_parts = file_path.replace("src/shared/", "").replace("/__init__.py", "").split("/")
        module_name = module_parts[-1] if module_parts else "module"
        
        # Create import statements
        imports = []
        for export in exports_list:
            # Convert CamelCase to snake_case for file names
            file_name = re.sub(r'(?<!^)(?=[A-Z])', '_', export).lower()
            if not file_name.endswith('_service') and not file_name.endswith('_manager'):
                file_name = file_name.replace('_', '_', 1)
            imports.append(f"from .{file_name} import {export}")
        
        # Create content
        content = f'''"""{module_name.replace('_', ' ').title()} Module"""

{chr(10).join(imports)}

__all__ = {exports_list}
'''
        
        print(f"Would update: {file_path}")
        print(content)
        print("-" * 80)

print("Run this script to see what would be updated")
