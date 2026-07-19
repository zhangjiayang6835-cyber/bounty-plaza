#!/bin/bash

# Function to get the last tag
get_last_tag() {
    git describe --abbrev=0 --tags
}

# Get the last tag
LAST_TAG=$(get_last_tag)

# Check if there are any tags
if [ -z "$LAST_TAG" ]; then
    echo "No tags found. Please add a tag to your repository."
    exit 1
fi

# Initialize changelog
echo "# Changelog" > CHANGELOG.md
echo "" >> CHANGELOG.md

# Fetch commits since the last tag
git log $LAST_TAG..HEAD --pretty=format:'%h %s' | while read -r line; do
    COMMIT_HASH=$(echo $line | awk '{print $1}')
    COMMIT_MSG=$(echo $line | awk '{for(i=2;i<=NF;i++) printf "%s ", $i; print ""}')

    # Categorize the commit
    if [[ $COMMIT_MSG =~ ^.*\b(Add|add|ADD)\b.*$ ]]; then
        CATEGORY="Added"
    elif [[ $COMMIT_MSG =~ ^.*\b(Fix|fix|FIX)\b.*$ ]]; then
        CATEGORY="Fixed"
    elif [[ $COMMIT_MSG =~ ^.*\b(Change|change|CHANGE)\b.*$ ]]; then
        CATEGORY="Changed"
    elif [[ $COMMIT_MSG =~ ^.*\b(Remove|remove|REMOVE)\b.*$ ]]; then
        CATEGORY="Removed"
    else
        CATEGORY="Other"
    fi

    # Append to the changelog
    echo "## ${CATEGORY}" >> CHANGELOG.md
    echo "- ${COMMIT_MSG} (${COMMIT_HASH})" >> CHANGELOG.md
done

# Sort the changelog by category
sort -o CHANGELOG.md CHANGELOG.md

echo "Changelog generated successfully: CHANGELOG.md"
