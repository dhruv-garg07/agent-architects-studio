import os

file_path = 'templates/gitmem/hub_api_keys.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('\\`', '`')
content = content.replace('\\${', '${')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed")
