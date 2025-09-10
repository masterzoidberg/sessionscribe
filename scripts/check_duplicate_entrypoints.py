#!/usr/bin/env python3
"""
CI guard script to prevent duplicate Electron entrypoints.
Fails the build if duplicate main.ts/preload.ts files are found outside src/.
"""

import os
import sys
from pathlib import Path

def check_duplicate_entrypoints() -> bool:
    """
    Check for duplicate Electron entrypoints outside src/ directory.
    
    Returns:
        True if no duplicates found, False if duplicates exist
    """
    project_root = Path(__file__).parent.parent
    electron_dir = project_root / "apps" / "desktop" / "electron"
    
    if not electron_dir.exists():
        print("❌ Electron directory not found")
        return False
    
    # Files that should only exist in src/
    protected_files = ["main.ts", "main.js", "preload.ts", "preload.js"]
    duplicates_found = []
    
    # Check for duplicates in the root electron directory
    for file_name in protected_files:
        root_file = electron_dir / file_name
        src_file = electron_dir / "src" / file_name.replace('.js', '.ts')  # We only want .ts in src/
        
        if root_file.exists():
            duplicates_found.append(str(root_file))
    
    if duplicates_found:
        print("❌ Duplicate Electron entrypoints found:")
        for duplicate in duplicates_found:
            print(f"   {duplicate}")
        print("\nThese files should only exist in apps/desktop/electron/src/")
        print("Remove the duplicates to fix this error.")
        return False
    
    # Verify src/ files exist
    required_src_files = [
        electron_dir / "src" / "main.ts",
        electron_dir / "src" / "preload.ts"
    ]
    
    missing_src_files = []
    for src_file in required_src_files:
        if not src_file.exists():
            missing_src_files.append(str(src_file))
    
    if missing_src_files:
        print("❌ Required src/ files missing:")
        for missing in missing_src_files:
            print(f"   {missing}")
        return False
    
    print("✅ No duplicate Electron entrypoints found")
    print("✅ Required src/ files exist")
    return True

def main():
    """Main entry point for CI check."""
    print("Checking for duplicate Electron entrypoints...")
    
    if check_duplicate_entrypoints():
        print("Entrypoint check passed!")
        return 0
    else:
        print("Entrypoint check failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())