#!/usr/bin/env python3
"""
Pre-flight checker for SOA-CLI
Verifies system readiness before running the pipeline
"""

import sys
import subprocess
from pathlib import Path

# Get workspace root (parent of scripts/ directory)
WORKSPACE_ROOT = Path(__file__).parent.parent


def check_python():
    """Check Python version"""
    print("[1/7] Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"    ✗ Python {version.major}.{version.minor} (need 3.8+)")
        return False
    print(f"    ✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """Check if required Python packages are installed"""
    print("\n[2/7] Python dependencies...")
    
    required = [
        'faiss',
        'sentence_transformers',
        'sklearn',
        'numpy'
    ]
    
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
            print(f"    ✓ {pkg}")
        except ImportError:
            print(f"    ✗ {pkg} (missing)")
            missing.append(pkg)
    
    if missing:
        print(f"\n    Install with: pip install -r requirements.txt")
        return False
    
    return True


def check_qwen():
    """Check if Qwen CLI is available"""
    print("\n[3/7] Qwen CLI...")
    try:
        result = subprocess.run(['which', 'qwen'], 
                              capture_output=True, 
                              text=True)
        if result.returncode == 0:
            print(f"    ✓ qwen found at: {result.stdout.strip()}")
            return True
        else:
            print(f"    ✗ qwen not found in PATH")
            print(f"    Install from: https://github.com/QwenLM/Qwen")
            return False
    except Exception as e:
        print(f"    ✗ Error checking for qwen: {e}")
        return False


def check_directories():
    """Check if required directories exist"""
    print("\n[4/7] Directory structure...")
    
    required_dirs = [
        'papers',
        'prompts',
        'artifacts',
        'artifacts/states',
        'artifacts/prisma',
        'artifacts/vector_db',
        'artifacts/reader',
        'artifacts/extracted',
        'artifacts/critic',
        'artifacts/clusters',
        'artifacts/synthesis',
        'artifacts/soa',
        'src',
        'scripts',
        'docs'
    ]
    
    all_exist = True
    for d in required_dirs:
        path = WORKSPACE_ROOT / d
        if path.exists():
            print(f"    ✓ {d}/")
        else:
            print(f"    ✗ {d}/ (missing)")
            all_exist = False
    
    return all_exist


def check_prompts():
    """Check if all system prompts exist"""
    print("\n[5/7] System prompts...")
    
    required_prompts = [
        'reader.system.txt',
        'extractor.system.txt',
        'critic.system.txt',
        'cluster.system.txt',
        'synthesis.system.txt',
        'writer.system.txt',
        'repair.system.txt',
        'verifier.system.txt'
    ]
    
    all_exist = True
    for p in required_prompts:
        path = WORKSPACE_ROOT / 'prompts' / p
        if path.exists():
            print(f"    ✓ {p}")
        else:
            print(f"    ✗ {p} (missing)")
            all_exist = False
    
    return all_exist


def check_scripts():
    """Check if main scripts exist"""
    print("\n[6/7] Core scripts...")
    
    required_files = [
        'soa_cli.py',  # Main entry point
        'src/theme_builder.py',
        'src/vectorize.py',
        'src/similarity_cluster.py',
        'src/hallucination_detector.py',
        'src/repair_loop.py',
        'src/__init__.py'
    ]
    
    all_exist = True
    for s in required_files:
        path = WORKSPACE_ROOT / s
        if path.exists():
            print(f"    ✓ {s}")
        else:
            print(f"    ✗ {s} (missing)")
            all_exist = False
    
    return all_exist


def check_papers():
    """Check if papers directory has PDFs"""
    print("\n[7/7] Research papers...")
    
    papers_dir = WORKSPACE_ROOT / 'papers'
    pdfs = list(papers_dir.glob('*.pdf'))
    
    if not pdfs:
        print(f"    ⚠ No PDF files found in papers/")
        print(f"    Add your research papers before running pipeline")
        return False
    
    print(f"    ✓ Found {len(pdfs)} PDF files")
    return True


def main():
    """Run all checks"""
    print("="*60)
    print("SOA-CLI Pre-Flight Check")
    print("="*60 + "\n")
    
    checks = [
        check_python,
        check_dependencies,
        check_qwen,
        check_directories,
        check_prompts,
        check_scripts,
        check_papers
    ]
    
    results = [check() for check in checks]
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✓ All checks passed ({passed}/{total})")
        print("\nReady to run: python soa_cli.py")
        return 0
    else:
        print(f"✗ {total - passed} check(s) failed ({passed}/{total} passed)")
        print("\nPlease fix the issues above before running the pipeline")
        return 1


if __name__ == "__main__":
    sys.exit(main())
