#!/usr/bin/env python3
"""
Fix malformed Jupyter notebook cell tags in unity_catalog_deep_dive.ipynb
Replace <language>sql</language> with proper <cell_type>code</cell_type> format
"""

import json
import re

def fix_notebook_cells():
    notebook_path = '/Users/ashwin.srikant/databricks_testing/databricks/databricks-utils/unity_catalog_deep_dive.ipynb'

    print("Reading notebook...")
    with open(notebook_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Count malformed cells before fixing
    malformed_count = len(re.findall(r'<language>sql</language>', content))
    print(f"Found {malformed_count} cells with malformed <language>sql</language> tags")

    # Fix the malformed language tags
    # Replace <language>sql</language> with <cell_type>code</cell_type>
    fixed_content = re.sub(r'<language>sql</language>', '<cell_type>code</cell_type>', content)

    # Also fix cell 30 which should be Python, not SQL
    # Find cell-30 and change it to Python
    cell_30_pattern = r'(<cell id="cell-30"><language>sql</language>)(.*?)(<cell id="cell-31">)'
    cell_30_match = re.search(cell_30_pattern, fixed_content, re.DOTALL)

    if cell_30_match:
        print("Fixing cell-30 to be Python instead of SQL...")
        cell_30_content = cell_30_match.group(2)
        # Replace the SQL tag with Python tag for cell-30
        fixed_cell_30 = f'<cell id="cell-30"><cell_type>code</cell_type>{cell_30_content}<cell id="cell-31">'
        fixed_content = re.sub(cell_30_pattern, fixed_cell_30, fixed_content, flags=re.DOTALL)

    # Count fixed cells
    remaining_malformed = len(re.findall(r'<language>sql</language>', fixed_content))
    print(f"After fixing: {remaining_malformed} malformed tags remaining")

    # Write the fixed content back
    print("Writing fixed notebook...")
    with open(notebook_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)

    print(f"✅ Fixed {malformed_count - remaining_malformed} malformed cell tags")
    print("✅ Notebook cell formatting has been corrected")

if __name__ == "__main__":
    fix_notebook_cells()