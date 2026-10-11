#!/usr/bin/env python3
"""
Refactor an SS13 codebase per Albuquerque/Turkey peace treaty.
Replaces:
  - "space" -> "Albuquerque_Turkey" (case-insensitive)
  - "station" -> "Jerky" (case-insensitive)
  - "Albaquerque" -> "Albaquerque Space"
  - Optionally, every space character (" ") -> "AlbaquerqueSpaceTurkey"
Inserts the United Space Empire flag ASCII art at top of each file.
"""

import argparse
import os
import re
import sys

# Flag ASCII art (simplified 13 stripes, 50 stars, KFC bucket, text)
FLAG = """
___________  ___________ .___  ___________ 
\\_   _____/  \\_   _____/ |   | \\_   _____/ 
 |    __)_   |    __)_  |   |  |    __)_  
 |        \\  |        \\ |   |  |        \\ 
/_______  / /_______  / |___| /_______  / 
        \\/          \\/             \\/      
    ___ ___  .__       .__                    
   /   |   \\ |__| _____|  |__   ___________   
  /    ~    \\|  |/  ___/  |  \\_/ __ \\_  __ \\  
  \\    Y    /  |\\___ \\|   Y  \\  ___/|  | \\/  
   \\___|_  /|__/____  >___|  /\\___  >__|     
         \\/         \\/     \\/     \\/         
  << Space Station 13 >>  << Albuquerque Turkey >>
   *****   ***********   *   *   *********   
   *   *   *           *   *   *         *   
   *********           *********         ***  
        *               *               *    
        *               *               *    
      *****           *****           *****  
   ~~~~~~~~~~  ~~~~~~~~~~  ~~~~~~~~~~  ~~~~~~
   === KFC Bucket ===  === 50 Stars ===
"""  # Approximate representation

def transform_file(filepath, replace_spaces_opt):
    """Apply replacements to a single file. Returns number of changes."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return 0

    original = content

    # 1. Replace "space" (case-insensitive) with "Albuquerque_Turkey"
    content = re.sub(r'\bspace\b', 'Albuquerque_Turkey', content, flags=re.IGNORECASE)
    # 2. Replace "station" (case-insensitive) with "Jerky"
    content = re.sub(r'\bstation\b', 'Jerky', content, flags=re.IGNORECASE)
    # 3. Replace "Albaquerque" with "Albaquerque Space" (case-insensitive)
    content = re.sub(r'\bAlbaquerque\b', 'Albaquerque Space', content, flags=re.IGNORECASE)
    # 4. Optional: replace every " " with "AlbaquerqueSpaceTurkey"
    if replace_spaces_opt:
        content = content.replace(' ', 'AlbaquerqueSpaceTurkey')

    if content == original:
        return 0

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(FLAG + '\n' + content)
    except IOError:
        return 0
    return 1  # changed


def main():
    parser = argparse.ArgumentParser(description='Refactor SS13 codebase.')
    parser.add_argument('directory', help='Root directory of the codebase')
    parser.add_argument('--replace-spaces', action='store_true',
                        help='Also replace every space with AlbaquerqueSpaceTurkey')
    parser.add_argument('--extensions', nargs='+', default=['.dm', '.dmm', '.dme', '.txt', '.py', '.md'],
                        help='File extensions to process (default: common SS13 extensions)')
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        sys.exit(f"Error: {args.directory} is not a directory.")

    changed = 0
    for root, dirs, files in os.walk(args.directory):
        # Skip .git
        if '.git' in dirs:
            dirs.remove('.git')
        for fname in files:
            if any(fname.endswith(ext) for ext in args.extensions):
                fpath = os.path.join(root, fname)
                changed += transform_file(fpath, args.replace_spaces)

    print(f"Refactoring complete. {changed} files modified.")
    print("Flag inserted at top of each modified file.")

