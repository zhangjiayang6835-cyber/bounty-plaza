#!/bin/bash

# Function to categorize commit messages
categorize_commit() {
    local message="$1"
    if [[ $message =~ ^[Aa]dd ]]; then
        echo "Added"
    elif [[ $message =~ ^[Ff]ix ]]; then
        echo "Fixed"
    elif [[ $message =~ ^[Cc]hange ]]; then
        echo "Changed"
    elif [[ $message =~ ^[Rr]emove ]]; then
        echo "Removed"
    else
        echo "Other"
    fi
}

# Get the latest tag
latest_tag=$(git describe --tags --abbrev=0)

# Generate the changelog
echo "# Changelog" > CHANGELOG.md
echo "" >> CHANGELOG.md

# Loop through all commits since the last tag
while read -r commit; do
    # Get the commit message
    message=$(git log -1 --pretty=%B $commit)
    
    # Categorize the commit
    category=$(categorize_commit "$message")
    
    # Append to the changelog
    echo "## $category" >> CHANGELOG.md
    echo " - $message" >> CHANGELOG.md
done < <(git log --pretty=format:"%H" $latest_tag..HEAD)

echo "Changelog generated successfully."
