import ast
import os
import re

def remove_docstrings_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
    except Exception:
        print(f"Failed to parse {filepath}")
        return
        
    docstring_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node):
                docstring_nodes.append(node.body[0])
                
    lines_to_remove = set()
    for node in docstring_nodes:
        for i in range(node.lineno, node.end_lineno + 1):
            lines_to_remove.add(i)
            
    lines = source.split('\n')
    new_lines = []
    for i, line in enumerate(lines, 1):
        if i not in lines_to_remove:
            new_lines.append(line)
            
    final_lines = []
    for line in new_lines:
        # Strip lines that are pure comments
        if line.strip().startswith('#'):
            continue
        final_lines.append(line)
        
    final_source = '\n'.join(final_lines)
    # clean multiple blank lines
    final_source = re.sub(r'\n{3,}', '\n\n', final_source)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_source.strip() + '\n')

for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            remove_docstrings_from_file(os.path.join(root, file))

print("Completed stripping comments.")
