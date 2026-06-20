#!/bin/bash
# build_skills.sh — Regenerate the distributable .skill bundles from the
# authoritative skill folders in .claude/skills/.
#
# Single source of truth: the skills live in .claude/skills/<name>/ (which is what
# Claude Code auto-loads on clone). The root-level *.skill zips are just packaged
# copies for Cowork / Claude Desktop ("Save skill"). Never hand-edit a .skill zip —
# edit the folder under .claude/skills/, then run this script to refresh the zips.
#
# Usage:  bash build_skills.sh

set -e
cd "$(dirname "$0")"

SKILLS_DIR=".claude/skills"
SKILLS=(linkedin-csm-scraper linkedin-csm-enrichment)

for name in "${SKILLS[@]}"; do
  src="$SKILLS_DIR/$name"
  out="$name.skill"
  if [ ! -d "$src" ]; then
    echo "ERROR: $src not found — is the skill folder present?" >&2
    exit 1
  fi
  rm -f "$out"
  # Zip from inside .claude/skills so the archive root is "<name>/..."
  ( cd "$SKILLS_DIR" && zip -r -X -q "../../$out" "$name" -x '*.DS_Store' '*__pycache__*' )
  echo "Built $out  <-  $src"
done

echo "Done. The .claude/skills/ folders are authoritative; these zips are generated copies."
