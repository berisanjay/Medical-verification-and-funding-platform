# Fix all em dashes in entity_extractor.py
with open('nlp/entity_extractor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all em dashes with regular hyphens
content = content.replace('—', '-')

with open('nlp/entity_extractor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ All em dashes fixed!")
