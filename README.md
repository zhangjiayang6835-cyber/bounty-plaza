# Generate Changelog Script

This script generates a structured `CHANGELOG.md` from a project's git history.

## Setup Instructions

1. Clone this repository.
2. Make the script executable:
   ```bash
chmod +x changelog.sh
```
3. Run the script:
   ```bash
./changelog.sh
```

The script will generate a `CHANGELOG.md` file in the current directory.

## Example Usage

```bash
./changelog.sh
```

This will generate a `CHANGELOG.md` file with categorized commit messages.

## Sample Output

```markdown
## Changelog

### Added
- Add new feature XYZ (abc1234)

### Fixed
- Fix bug ABC (def5678)

### Changed
- Change configuration settings (ghi9101)

### Removed
- Remove deprecated function (jkl1121)
```

### Testing

To test the script, you can run it in a repository with a few commits and tags. Here are the steps:

1. Create a new Git repository.
2. Add a few commits with different types of messages (e.g., "Add new feature", "Fix bug", "Change configuration").
3. Tag a commit.
4. Add more commits after the tag.
5. Run the script and check the generated `CHANGELOG.md`.

### Example Repository

```bash
mkdir test_repo
cd test_repo
git init
echo "Initial commit" > README.md
git add README.md
git commit -m "Initial commit"

# Add some commits
echo "Feature 1" > feature1.txt
git add feature1.txt
git commit -m "Add new feature XYZ"

echo "Bug fix" > bugfix.txt
git add bugfix.txt
git commit -m "Fix bug ABC"

echo "Config change" > config.txt
git add config.txt
git commit -m "Change configuration settings"

# Tag the current commit
git tag v1.0.0

# Add more commits
echo "Deprecated function" > deprecate.txt
git add deprecate.txt
git commit -m "Remove deprecated function"

# Run the script
../path/to/changelog.sh

# Check the generated CHANGELOG.md
cat CHANGELOG.md
```

This should generate a `CHANGELOG.md` file with the categorized commit messages.

### Conclusion

This script provides a simple and effective way to generate a structured `CHANGELOG.md` from a project's git history. It categorizes commit messages and outputs them in a readable format.
