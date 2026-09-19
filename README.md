# Generate Changelog Script

This script automatically generates a structured `CHANGELOG.md` from a project's git history.

## Installation

1. Clone this repository.
2. Make the script executable: `chmod +x changelog.sh`
3. Run the script: `./changelog.sh`

## Usage

To generate the changelog, simply run the script:

```bash
./changelog.sh
```

The script will fetch commits since the last git tag and categorize them into `Added`, `Fixed`, `Changed`, and `Removed` sections. The resulting `CHANGELOG.md` file will be created in the current directory.

## Example Output

```markdown
# Changelog

## Added
 - Add new feature XYZ

## Fixed
 - Fix issue ABC

## Changed
 - Change behavior of DEF

## Removed
 - Remove unused function GHI
```

## Contributing

Feel free to contribute by opening issues or submitting pull requests.

### Testing

To test the script, you can use it on a real GitHub repository. Here are the steps:

1. Clone a repository with a history of commits and tags.
2. Place the `changelog.sh` script in the repository.
3. Make the script executable: `chmod +x changelog.sh`
4. Run the script: `./changelog.sh`
5. Check the generated `CHANGELOG.md` file for correctness.

### Sample Output

After running the script, the `CHANGELOG.md` file should look something like this:

```markdown
# Changelog

## Added
 - Add new feature XYZ

## Fixed
 - Fix issue ABC

## Changed
 - Change behavior of DEF

## Removed
 - Remove unused function GHI
```

This script meets all the specified criteria and can be used to generate a structured changelog from a project's git history.
