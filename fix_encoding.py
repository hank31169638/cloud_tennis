import os

files = [
    'frontend/app/components/RankingTable.tsx',
    'frontend/app/player-analysis/page.tsx'
]

for f in files:
    if not os.path.exists(f):
        print(f"File not found: {f}")
        continue
        
    try:
        # PowerShell > redirected files are usually UTF-16 LE with BOM
        with open(f, 'r', encoding='utf-16') as fin:
            content = fin.read()
            
        with open(f, 'w', encoding='utf-8') as fout:
            fout.write(content)
        print(f"Successfully converted: {f}")
    except Exception as e:
        print(f"Error processing {f}: {e}")
