import subprocess
import os

files = {
    'frontend/app/components/RankingTable.tsx': 'temp/main:frontend/app/components/RankingTable.tsx',
    'frontend/app/player-analysis/page.tsx': 'temp/main:frontend/app/player-analysis/page.tsx'
}

for local_path, remote_path in files.items():
    try:
        # Use utf-8 explicitly for git output (standard)
        # However, if files contain non-utf8 (unlikely for tsx), need binaries mode.
        # TSX is text.
        content = subprocess.check_output(['git', 'show', remote_path])
        # Decode as utf-8 (assuming source is utf-8)
        content_str = content.decode('utf-8')
        
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(content_str)
        print(f"Restored {local_path} from {remote_path}")
    except Exception as e:
        print(f"Error restoring {local_path}: {e}")
