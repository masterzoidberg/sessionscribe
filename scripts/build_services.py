#!/usr/bin/env python3
"""
Build script to create PyInstaller executables for all FastAPI services.
This script builds standalone executables that can be bundled with Electron.
"""

import os
import subprocess
import sys
from pathlib import Path

def build_service(service_name: str, service_dir: Path) -> bool:
    """Build a single service with PyInstaller."""
    spec_file = service_dir / f"{service_name}_service.spec"
    
    if not spec_file.exists():
        print(f"❌ Spec file not found: {spec_file}")
        return False
    
    print(f"🔨 Building {service_name} service...")
    
    try:
        # Run PyInstaller
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller",
            str(spec_file),
            "--distpath", str(service_dir / "dist"),
            "--workpath", str(service_dir / "build"),
        ], 
        cwd=service_dir,
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            exe_path = service_dir / "dist" / f"{service_name}_service.exe"
            if exe_path.exists():
                print(f"✅ {service_name} service built successfully: {exe_path}")
                return True
            else:
                print(f"❌ {service_name} executable not found after build")
                return False
        else:
            print(f"❌ {service_name} build failed:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ {service_name} build timed out")
        return False
    except Exception as e:
        print(f"❌ {service_name} build error: {e}")
        return False

def main():
    """Build all services."""
    project_root = Path(__file__).parent.parent
    services_dir = project_root / "services"
    
    services = ["asr", "redaction", "insights_bridge", "note_builder"]
    success_count = 0
    
    print("🚀 Building SessionScribe services...")
    
    for service in services:
        service_dir = services_dir / service
        if service_dir.exists():
            if build_service(service, service_dir):
                success_count += 1
        else:
            print(f"❌ Service directory not found: {service_dir}")
    
    print(f"\n📊 Build Summary: {success_count}/{len(services)} services built successfully")
    
    if success_count == len(services):
        print("🎉 All services built successfully!")
        return 0
    else:
        print("❌ Some services failed to build")
        return 1

if __name__ == "__main__":
    sys.exit(main())