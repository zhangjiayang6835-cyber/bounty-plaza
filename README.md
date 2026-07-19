# Generate Changelog Script

This script automatically generates a structured `CHANGELOG.md` from a project's git history.

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Make the script executable:**
   ```bash
   chmod +x changelog.sh
   ```

3. **Run the script:**
   ```bash
  ./changelog.sh
   ```

The script will generate a `CHANGELOG.md` file in the root directory of your project.

## Usage

- **Command to run the script:**
  ```bash
 ./changelog.sh
  ```

- **Output:**
  - A `CHANGELOG.md` file will be created or updated in the root directory of your project.
  - The changelog will be categorized into `Added`, `Fixed`, `Changed`, and `Removed` sections based on the commit messages.

## Example Output

```markdown
# Changelog

## Added
- Add new feature XYZ (abc1234)
- Add support for ABC (def5678)

## Fixed
- Fix bug in XYZ (ghi9101)
- Fix issue with ABC (jkl2345)

## Changed
- Change behavior of XYZ (mno3456)
- Change configuration for ABC (pqr7890)

## Removed
- Remove deprecated function XYZ (stu0123)
- Remove unused code ABC (vwx4567)
```

## Notes

- The script assumes that you have at least one git tag in your repository.
- If no tags are found, the script will prompt you to add a tag.
- The script uses keywords in the commit messages to categorize the changes. You can modify the keywords as needed.

### Testing

To test the script, follow these steps:

1. **Create a sample repository:**
   ```bash
   mkdir test-repo
   cd test-repo
   git init
   echo "Initial commit" > README.md
   git add README.md
   git commit -m "Initial commit"
   git tag v0.1.0
   echo "Add new feature" > feature.txt
   git add feature.txt
   git commit -m "Add new feature XYZ"
   echo "Fix bug" > fix.txt
   git add fix.txt
   git commit -m "Fix bug in XYZ"
   echo "Change behavior" > change.txt
   git add change.txt
   git commit -m "Change behavior of XYZ"
   echo "Remove deprecated function" > remove.txt
   git add remove.txt
   git commit -m "Remove deprecated function XYZ"
   ```

2. **Run the script:**
   ```bash
  ./changelog.sh
   ```

3. **Verify the output:**
   - Check the `CHANGELOG.md` file in the `test-repo` directory.

### Submission

1. Comment `/opire try` in the GitHub issue.
2. Submit a PR with the `changelog.sh` and `README.md` files.
3. Payment will be released automatically on merge.

This solution should meet all the acceptance criteria and provide a functional way to generate a `CHANGELOG.md` from a project's git history.
