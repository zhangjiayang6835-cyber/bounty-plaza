```python
import pathlib
import sys

def fix_typo_in_readme(readme_path: pathlib.Path):
    if not readme_path.is_file():
        sys.stderr.write(f"Error: {readme_path} does not exist.\n")
        return 1

    content = readme_path.read_text(encoding="utf-8")
    # Replace only the exact typo "Welcom" (case‑sensitive) with "Welcome"
    new_content = content.replace("Welcom", "Welcome")

    if new_content == content:
        print("No typo found; file unchanged.")
        return 0

    readme_path.write_text(new_content, encoding="utf-8")
    print(f"Typo fixed in {readme_path}")
    return 0

if __name__ == "__main__":
    # Assume the script is run from the repository root.
    readme_file = pathlib.Path("README.md")
    sys.exit(fix_typo_in_readme(readme_file))
```