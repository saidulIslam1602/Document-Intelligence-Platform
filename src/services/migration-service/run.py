#!/usr/bin/env python3
"""
Wrapper script to run the migration-service
This handles the import path issues with hyphens in directory names
"""
import sys
import os

# Add the app root to Python path
sys.path.insert(0, '/app')

# Now we can import and run the application
if __name__ == "__main__":
    import uvicorn
    # Import the app from the main module
    from main import app
    
    # Run uvicorn with the app
    uvicorn.run(app, host="0.0.0.0", port=8009)

