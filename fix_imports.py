import os
import re

def fix_relative_imports(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Replace relative imports
    # from core -> from core
    # from models -> from models
    # from schemas -> from schemas
    # from repositories -> from repositories
    # from services -> from services
    # from routes -> from routes
    # from . -> import (for same directory imports)
    
    content = re.sub(r'from \.\.(\w+)', r'from \1', content)
    content = re.sub(r'from \.(\w+)', r'from \1', content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def process_directory(directory):
    fixed_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_relative_imports(file_path):
                    fixed_files.append(file_path)
    return fixed_files

if __name__ == "__main__":
    fixed = process_directory(".")
    print(f"Fixed {len(fixed)} files:")
    for f in fixed:
        print(f"  - {f}")
