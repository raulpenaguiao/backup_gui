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
git commit -m "Bump version to $new_version"
git push origin main
git tag "v$new_version"
git push origin "v$new_version"
echo "Released v$new_version"
