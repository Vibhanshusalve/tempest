import os
import glob

def fix_future_import(filepath):
    """Move 'from __future__ import annotations' to the top of the file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find and remove all future import lines
        future_imports = []
        new_lines = []
        for line in lines:
            if line.strip().startswith('from __future__ import'):
                future_imports.append(line)
            else:
                new_lines.append(line)
        
        if not future_imports:
            return False  # No future imports found
        
        # Find insertion point (after shebang/encoding comments)
        insert_pos = 0
        for i, line in enumerate(new_lines):
            if line.strip().startswith('#'):
                insert_pos = i + 1
            else:
                break
        
        # Insert future imports at the top
        for future_import in reversed(future_imports):
            new_lines.insert(insert_pos, future_import)
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print(f"✓ Fixed: {filepath}")
        return True
    except Exception as e:
        print(f"✗ Error fixing {filepath}: {e}")
        return False

# Find all Python files in cogs directory
python_files = glob.glob('cogs/**/*.py', recursive=True)

fixed_count = 0
for py_file in python_files:
    if fix_future_import(py_file):
        fixed_count += 1

print(f"\n✓ Fixed {fixed_count} files")
