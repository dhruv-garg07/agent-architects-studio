import json
import re


import re

def extract_python_code(text_block):
    """
    Extracts the Python code block from a string that uses triple backticks.

    Args:
        text_block (str): String containing a Python code block (```python ... ```)

    Returns:
        str: The extracted Python code, or raises ValueError if not found.
    """
    match = re.search(r"```python\s(.*?)```", text_block, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        raise ValueError("No Python code block found in the text.")

# Example usage:
text = '''```python
import tkinter as tk
from tkinter import messagebox
# ... rest of the code ...
root.mainloop()
```'''

# code = extract_python_code(text)
# print(code)

def extract_json_from_string(response_str):
    """
    Extracts a JSON object from a string containing a code block with or without a language specifier.

    Args:
        response_str (str): The input string containing a JSON object wrapped in triple backticks.

    Returns:
        dict: Parsed JSON object.

    Raises:
        ValueError: If JSON block or format is invalid.
    """
    # Match ```json { ... } ``` or just ``` { ... } ```
    try:
        pattern = r"```(?:json)?\s*(\{(?:.|\n)*?\})\s*```"
        match = re.search(pattern, response_str, re.IGNORECASE)
        
        if not match:
            raise ValueError("No valid JSON block found in the input text.")
        
        json_str = match.group(1)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    except Exception as e:
        print("ERROR: ", e)

# Example usage
response = '''here hows  ```json
{
  "sequential_tasks": [
    "Create a simple user interface to collect email details.",
    "Implement input validation for the form fields.",
    "Set up an email service configuration.",
    "Implement email sending functionality with error handling.",
    "Add a confirmation notification after email is sent."
  ],
  "parallel_tasks": [
    "Create a form template with fields for name, subject, message, and contact information.",      
    "Set up email service credentials and configuration."
  ]
}
```'''

# result = extract_json_from_string(response)
# print(result)
import re

import re

def extract_powershell_commands(script_text):
    """
    Extract all PowerShell commands from code blocks marked as ```powershell.
    Works even if other languages (e.g., json) are present in between.
    """
    if isinstance(script_text, list):
        script_text = "\n".join(script_text)

    # Match all ```powershell ... ``` blocks, ignoring case
    ps_blocks = re.findall(r"```powershell\s*(.*?)\s*```", script_text, re.DOTALL | re.IGNORECASE)

    commands = []
    for block in ps_blocks:
        # Split commands by newline or semicolon
        parts = re.split(r"[;\n]+", block.strip())
        commands.extend(cmd.strip() for cmd in parts if cmd.strip())

    return commands



# # Example usage
# example_data = [
#     '<think>',
#     "Okay, I need to create a virtual environment and install Flask in the specified folder using PowerShell. First, I should navigate to the correct directory. Then, I'll use the python command to create the virtual environment. After that, I'll activate it and install Flask using pip. I should make sure each command is correct and in the right order.",
#     '</think>',
#     '**Step-by-Step Explanation:**',
#     '1. **Navigate to the Project Directory:**',
#     '- Use `cd` to change the directory to `C:\\Desktop\\python_workspace_311\\flask_text_analyzer`.',
#     '2. **Create the Virtual Environment:**',
#     '- Run `python -m venv venv` to create a virtual environment named `venv` in your project directory.',
#     '3. **Activate the Virtual Environment:**',
#     '- Use `.\\venv\\Scripts\\Activate.ps1` to activate the virtual environment in PowerShell.',
#     '4. **Install Flask:**',
#     '- Execute `pip install flask` to install Flask within the activated virtual environment.',
#     '**Commands:**',
#     '```powershell',
#     'cd C:\\Desktop\\python_workspace_311\\flask_text_analyzer',
#     'python -m venv venv',
#     '.\\venv\\Scripts\\Activate.ps1',
#     'pip install flask',
#     '```'
# ]

# print(extract_powershell_commands(example_data))


def get_language_from_filename(filename):
    extension_map = {
        "py": "Python",
        "js": "JavaScript",
        "ts": "TypeScript",
        "java": "Java",
        "c": "C",
        "cpp": "C++",
        "cs": "C#",
        "rb": "Ruby",
        "go": "Go",
        "rs": "Rust",
        "php": "PHP",
        "swift": "Swift",
        "kt": "Kotlin",
        "m": "Objective-C",
        "scala": "Scala",
        "lua": "Lua",
        "sh": "Shell",
        "bat": "Batch",
        "pl": "Perl",
        "r": "R",
        "jl": "Julia",
        "dart": "Dart",
        "groovy": "Groovy",
        "hs": "Haskell",
        "clj": "Clojure",
        "ex": "Elixir",
        "erl": "Erlang",
        "sql": "SQL",
        "html": "HTML",
        "htm": "HTML",
        "css": "CSS",
        "xml": "XML",
        "json": "JSON",
        "yaml": "YAML",
        "yml": "YAML",
        "md": "Markdown",
        "tex": "LaTeX",
        "xsl": "XSLT",
        "tsx": "TypeScript JSX",
        "jsx": "JavaScript JSX",
        "coffee": "CoffeeScript",
        "f": "Fortran",
        "f90": "Fortran",
        "nim": "Nim",
        "pas": "Pascal",
        "vb": "Visual Basic",
        "vbs": "VBScript",
        "ada": "Ada",
        "lisp": "Lisp",
        "scm": "Scheme",
        "rkt": "Racket",
        "ps1": "PowerShell",
        "awk": "AWK",
        "tcl": "Tcl",
        "d": "D",
        "pro": "Prolog",
        "asm": "Assembly",
        "s": "Assembly",
        "h": "C/C++ Header",
        "mm": "Objective-C++",
        "vue": "Vue.js",
        "svelte": "Svelte",
        "sol": "Solidity",
        "zig": "Zig",
        "ml": "OCaml",
        "fs": "F#",
        "apk": "Android Package (binary)",
        "ipynb": "Jupyter Notebook",
    }

    ext = filename.split(".")[-1].lower()
    return extension_map.get(ext, "Unknown Language")

# print(get_language_from_filename("bubble_sort.py"))     # Python
# print(get_language_from_filename("script.css"))         # CSS
# print(get_language_from_filename("main.rs"))            # Rust
# print(get_language_from_filename("dashboard.vue"))      # Vue.js
# print(get_language_from_filename("notebook.ipynb"))     # Jupyter Notebook
# print(get_language_from_filename("unknown.xyz"))        # Unknown Language

import re

def extract_code_block(text_block, language=None):
    """
    Extracts a code block from a string that uses triple backticks.

    Args:
        text_block (str): String containing a code block (e.g., ```python ... ```)
        language (str, optional): Specific language to match (e.g., 'python', 'js').
                                  If None, extracts the first code block regardless of language.

    Returns:
        str: The extracted code block, or raises ValueError if not found.
    """
    if language:
        pattern = rf"```{re.escape(language)}\s(.*?)```"
    else:
        pattern = r"```(?:\w+)?\s(.*?)```"

    match = re.search(pattern, text_block, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        raise ValueError("No code block found in the text.")