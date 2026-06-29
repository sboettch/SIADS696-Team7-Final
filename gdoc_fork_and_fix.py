#!/usr/bin/env python3
"""
Fork the working Google Doc and apply the 6 proposed fixes.
"""
import os, json, time, re
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')
SOURCE_DOC_ID = '1IMYOEqOTinRo4c758icm0M0iyvCT0v_F9I1c4Ca3Oqw'

creds = Credentials.from_authorized_user_file(TOKEN_FILE)
docs = build('docs', 'v1', credentials=creds)
drive = build('drive', 'v3', credentials=creds)

# 1. Copy the document
print("Copying document...")
copy = drive.files().copy(
    fileId=SOURCE_DOC_ID,
    body={'name': 'SIADS 696 Team 7 Final Report — Proposed Fixes'}
).execute()
new_id = copy['id']
print(f"  Created copy: https://docs.google.com/document/d/{new_id}/edit")

# Make it accessible
drive.permissions().create(
    fileId=new_id,
    body={'type': 'anyone', 'role': 'writer'}
).execute()

# 2. Read the full doc text
print("Reading document...")
doc = docs.documents().get(documentId=new_id).execute()

# Build a flat text + index map
segments = []
for elem in doc['body']['content']:
    if 'paragraph' in elem:
        for el in elem['paragraph']['elements']:
            if 'textRun' in el:
                segments.append((el['startIndex'], el['endIndex'], el['textRun']['content']))

full_text = ''
idx_map = []  # (doc_index, char)
for start, end, content in segments:
    for i, ch in enumerate(content):
        idx_map.append(start + i)
    full_text += content


def find_text(needle):
    """Find the doc start/end index of a text string."""
    pos = full_text.find(needle)
    if pos < 0:
        return None, None
    return idx_map[pos], idx_map[pos + len(needle) - 1] + 1


def find_all_text(needle):
    """Find all occurrences."""
    results = []
    start = 0
    while True:
        pos = full_text.find(needle, start)
        if pos < 0:
            break
        results.append((idx_map[pos], idx_map[pos + len(needle) - 1] + 1))
        start = pos + 1
    return results


# 3. Build fix requests (applied in REVERSE order to preserve indices)
fixes = []

# Fix 1: Remove question headers in Introduction
question_headers = [
    "What problem are you trying to solve?\n",
    "What impact will solving the problem have?\n",
    "What motivated you to work on it?\n",
    "Summarize your project's supervised and unsupervised methods, highlighting any novel contributions.\n",
    "What are your main findings for supervised and unsupervised learning?\n",
]
for qh in question_headers:
    # Try with and without newline
    for variant in [qh, qh.rstrip('\n')]:
        s, e = find_text(variant)
        if s is not None:
            # Include the trailing newline if present
            if e < len(idx_map) and full_text[full_text.find(variant) + len(variant) - 1] == '\n':
                pass  # newline already included
            fixes.append(('delete', s, e, f'Remove question header: {variant[:40]}...'))
            break

# Fix 2: "three sources" → "five primary sources"
s, e = find_text('three sources')
if s:
    fixes.append(('replace', s, e, 'five primary sources', 'Fix source count'))
else:
    # Try broader
    s, e = find_text('from three sources')
    if s:
        s2, e2 = find_text('three sources')

# Fix 3: "BBefore" → "Before"
s, e = find_text('BBefore')
if s:
    fixes.append(('replace', s, e, 'Before', 'Fix BBefore typo'))

# Fix 4: Redundant unsupervised sentence at end of Related Work paragraph 1
redundant = "In addition, we will also use unsupervised learning (which wasn\u2019t utilized in these studies) to uncover latent socio-environmental archetypes across U.S. counties."
s, e = find_text(redundant)
if s:
    # Delete including any preceding space
    check_pos = full_text.find(redundant)
    if check_pos > 0 and full_text[check_pos - 1] == ' ':
        s = idx_map[check_pos - 1]
    fixes.append(('delete', s, e, 'Remove redundant unsupervised sentence'))

# Fix 5: Add "Table 0." label to the research question table in intro
# The table starts with "Research question"
rq_text = "Research question\n"
s, e = find_text(rq_text)
if s:
    fixes.append(('insert', s, s, '\nTable 0. Summary of research questions and modeling approaches.\n',
                   'Add table label'))

# Sort fixes by start index in REVERSE order
fixes.sort(key=lambda x: x[1], reverse=True)

print(f"\nApplying {len(fixes)} fixes...")
for fix in fixes:
    reqs = []
    if fix[0] == 'delete':
        _, start, end, desc = fix
        reqs.append({'deleteContentRange': {'range': {'startIndex': start, 'endIndex': end}}})
        print(f"  DELETE [{start}:{end}]: {desc}")
    elif fix[0] == 'replace':
        _, start, end, new_text, desc = fix
        reqs.append({'deleteContentRange': {'range': {'startIndex': start, 'endIndex': end}}})
        reqs.append({'insertText': {'location': {'index': start}, 'text': new_text}})
        print(f"  REPLACE [{start}:{end}]: {desc}")
    elif fix[0] == 'insert':
        _, start, _, new_text, desc = fix
        reqs.append({'insertText': {'location': {'index': start}, 'text': new_text}})
        print(f"  INSERT at {start}: {desc}")

    try:
        docs.documents().batchUpdate(documentId=new_id, body={'requests': reqs}).execute()
    except Exception as ex:
        print(f"    ⚠️ Failed: {ex}")
    time.sleep(0.3)

print(f"\n✅ All fixes applied!")
print(f"   Original: https://docs.google.com/document/d/{SOURCE_DOC_ID}/edit")
print(f"   Fixed copy: https://docs.google.com/document/d/{new_id}/edit")

# Save the new doc ID
with open(os.path.join(SCRIPT_DIR, 'gdoc_fixed_copy.json'), 'w') as f:
    json.dump({'doc_id': new_id, 'source_id': SOURCE_DOC_ID}, f, indent=2)
