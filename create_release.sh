#!/usr/bin/env bash
set -e

current=$(cat VERSION)
echo "Current version: $current"

read -rp "New version (x.x.x): " new_version

if [[ ! "$new_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: version must be in the form x.x.x" >&2
    exit 1
fi

echo "$new_version" > VERSION
git add VERSION
if git diff --cached --quiet; then
    echo "Version unchanged — nothing new to commit, re-tagging v$new_version"
else
    git commit -m "Bump version to $new_version"
    git push origin main
fi

# Delete existing tag locally and remotely so CI/CD fires fresh
if git tag -l "v$new_version" | grep -q .; then
    git tag -d "v$new_version"
fi
if git ls-remote --tags origin "refs/tags/v$new_version" | grep -q .; then
    git push origin --delete "v$new_version"
fi

git tag "v$new_version"
git push origin "v$new_version"
echo "Released v$new_version"
echo "Watch progress at: https://github.com/raulpenaguiao/backup_gui/actions"
