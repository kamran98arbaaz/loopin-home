import os
import re

# Patterns
route_pattern = re.compile(r'@(?:\w+\.)?route\([\'"]([^\'"]+)[\'"]')
model_pattern = re.compile(r'class\s+(\w+)\(db\.Model\)')
func_pattern = re.compile(r'^def\s+(\w+)\(')
class_pattern = re.compile(r'^class\s+(\w+)\(.*\):')

def index_codebase(root_dir="."):
    index = []

    for root, dirs, files in os.walk(root_dir, topdown=True):
        # skip ignored dirs
        dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "venv", "node_modules", "migrations"]]

        rel_path = os.path.relpath(root, root_dir)
        indent_level = rel_path.count(os.sep)
        indent = "    " * indent_level

        if rel_path != ".":
            index.append(f"{indent}{os.path.basename(root)}/")

        for file in files:
            if file.endswith(".py") or file.endswith(".html"):
                file_indent = "    " * (indent_level + 1)
                index.append(f"{file_indent}{file}")

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        lines = f.readlines()
                except:
                    continue

                # scan for routes, models, functions, classes
                for line in lines:
                    line = line.strip()
                    if match := route_pattern.search(line):
                        index.append(f"{file_indent}    [ROUTE] {match.group(1)}")
                    elif match := model_pattern.search(line):
                        index.append(f"{file_indent}    [MODEL] {match.group(1)}")
                    elif match := func_pattern.match(line):
                        index.append(f"{file_indent}    [FUNC] {match.group(1)}")
                    elif match := class_pattern.match(line):
                        index.append(f"{file_indent}    [CLASS] {match.group(1)}")

    return "\n".join(index)

if __name__ == "__main__":
    print(index_codebase("."))
