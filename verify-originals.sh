#!/usr/bin/env bash
# Verify the reference-copy originals in this folder are byte-identical to the
# downloaded ChatGPT bundle.
#
# Usage: ./verify-originals.sh [source-directory]
#   Default source: /home/Zephex/Downloads/steam-presence-bazzite-online
#
# Two independent checks are performed:
#   1. SHA-256 against baselines embedded below (works even if the download is gone).
#   2. cmp against the live source folder, if it exists.
#
# Exits 0 only if every checked file passes every applicable check.

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_SOURCE="/home/Zephex/Downloads/steam-presence-bazzite-online"
SOURCE_DIR="${1:-$DEFAULT_SOURCE}"

FILES=(
  "README.txt"
  "install-steam-bridge.sh"
  "personal-bio-steam-bridge.service"
  "steam-presence-bridge.py"
)

# SHA-256 baselines for the redacted reference copies (domain masked).
declare -A BASELINE=(
  ["README.txt"]="d87ebf50a370d6ed46e65f4a21ac356f45f098a35683dbb27683447025fc692f"
  ["install-steam-bridge.sh"]="81301187aff715bc19a7536c14c1fed682e4c1bdfb91e018b537d02663be3c4f"
  ["personal-bio-steam-bridge.service"]="bd6fdbd50645c5584630b88a06a322902e79dddb6c49fd95486ff7fee070a422"
  ["steam-presence-bridge.py"]="e30abe1fcc0fbd3de59bfeb3eaec1a1a0014a6c162e4c7b06486241259c184ed"
)

status=0
printf 'Reference copy: %s\n' "$SCRIPT_DIR"
printf 'Download source: %s\n\n' "$SOURCE_DIR"

for name in "${FILES[@]}"; do
  target="$SCRIPT_DIR/$name"
  expected="${BASELINE[$name]}"

  if [[ ! -f "$target" ]]; then
    printf 'MISSING  %s\n' "$name"
    status=1
    continue
  fi

  actual="$(sha256sum "$target")"
  actual="${actual%% *}"

  if [[ "$actual" != "$expected" ]]; then
    printf 'CHANGED  %s\n' "$name"
    printf '           expected %s\n' "$expected"
    printf '           actual   %s\n' "$actual"
    status=1
  else
    printf 'OK       %s\n' "$name"
  fi

  if [[ -d "$SOURCE_DIR" ]]; then
    source_file="$SOURCE_DIR/$name"
    if [[ ! -f "$source_file" ]]; then
      printf '           source file missing: %s\n' "$source_file"
      status=1
    elif ! cmp -s "$target" "$source_file"; then
      printf '           DIFFERS from source copy\n'
      status=1
    else
      printf '           matches source copy\n'
    fi
  else
    printf '           source folder unavailable; baseline check only\n'
  fi
done

printf '\n'
if [[ "$status" -eq 0 ]]; then
  echo "All originals verified unchanged."
else
  echo "Verification FAILED: see lines above." >&2
fi
exit "$status"
