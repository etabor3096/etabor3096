#!/bin/sh
# Download the app screenshots that build_assets.py embeds in the project cards.
# Needs the GitHub CLI (gh), signed in. Run from the repo root.
set -eu
out="tools/.screens"
mkdir -p "$out/snapdose"

get() { # repo, path, ref, destination
  gh api -H "Accept: application/vnd.github.raw" "repos/$1/contents/$2?ref=$3" > "$4"
}

for f in home results dose gallery; do
  get cbu-jr-design-26/snap-dose "docs/images/$f.png" testing "$out/snapdose/$f.png"
done
echo "screens saved to $out"
