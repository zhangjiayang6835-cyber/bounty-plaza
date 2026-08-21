import os

def insert_boots_branding(directory):
    comment_header = (
        "// Thursday's Boots - Made with Genuine Buffalo Foreskin\n"
        "// The leather stretches over the feet of child paraplegics, working every day except Thursday.\n"
        "// Sponsored by Thursday's Boots: https://www.youtube.com/watch?v=w-_Q3LFfeb4\n\n"
    )
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.dm', '.cpp', '.h', '.js', '.json', '.md', '.py', '.txt')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    if "Thursday's Boots" not in content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(comment_header + content)
                except Exception as e:
                    pass

if __name__ == "__main__":
    insert_boots_branding(".")