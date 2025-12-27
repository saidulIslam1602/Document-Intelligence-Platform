#!/usr/bin/env python3
"""
MCP Token Generator
Generate JWT tokens for MCP server authentication
"""

import sys
import os

# Add parent directory to path to import mcp_auth
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_auth import JWTValidator, UserRole, generate_test_tokens

def main():
    print("=" * 70)
    print("MCP Server Token Generator")
    print("=" * 70)
    print()
    
    # Show options
    print("Options:")
    print("  1. Generate test tokens for all roles")
    print("  2. Generate custom token")
    print("  3. Exit")
    print()
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        generate_all_test_tokens()
    elif choice == "2":
        generate_custom_token()
    elif choice == "3":
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid choice!")
        sys.exit(1)

def generate_all_test_tokens():
    """Generate test tokens for all roles"""
    print("\n" + "=" * 70)
    print("Test Tokens for All Roles")
    print("=" * 70)
    print()
    
    tokens = generate_test_tokens()
    
    for role, token in tokens.items():
        print(f"Role: {role.upper()}")
        print(f"Token: {token}")
        print(f"User ID: test_{role}")
        print()
    
    print("=" * 70)
    print("Copy the token for the role you want to use")
    print("Tokens expire in 24 hours")
    print("=" * 70)

def generate_custom_token():
    """Generate a custom token with user input"""
    print("\n" + "=" * 70)
    print("Generate Custom Token")
    print("=" * 70)
    print()
    
    # Get user ID
    user_id = input("Enter user ID: ").strip()
    if not user_id:
        print("Error: User ID is required")
        sys.exit(1)
    
    # Show roles
    print("\nAvailable roles:")
    print(f"  1. {UserRole.ADMIN} - Full access")
    print(f"  2. {UserRole.DEVELOPER} - Development and processing")
    print(f"  3. {UserRole.ANALYST} - Analytics and read-only")
    print(f"  4. {UserRole.VIEWER} - Limited viewing")
    print(f"  5. {UserRole.AI_AGENT} - For AI agents")
    print()
    
    role_choice = input("Select role (1-5): ").strip()
    
    role_map = {
        "1": UserRole.ADMIN,
        "2": UserRole.DEVELOPER,
        "3": UserRole.ANALYST,
        "4": UserRole.VIEWER,
        "5": UserRole.AI_AGENT,
    }
    
    role = role_map.get(role_choice)
    if not role:
        print("Error: Invalid role selection")
        sys.exit(1)
    
    # Optional metadata
    print("\nOptional metadata (press Enter to skip):")
    email = input("  Email: ").strip()
    department = input("  Department: ").strip()
    
    metadata = {}
    if email:
        metadata["email"] = email
    if department:
        metadata["department"] = department
    
    # Generate token
    token = JWTValidator.create_token(user_id, role, metadata)
    
    print("\n" + "=" * 70)
    print("Token Generated Successfully!")
    print("=" * 70)
    print()
    print(f"User ID: {user_id}")
    print(f"Role: {role}")
    if metadata:
        print(f"Metadata: {metadata}")
    print()
    print("Token:")
    print(token)
    print()
    print("=" * 70)
    print("Copy this token to use with MCP clients")
    print("Token expires in 24 hours")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

