#!/usr/bin/env bash
set -euo pipefail
XML="${1:?Usage: bash scripts/open_netanim.sh path/to/animation.xml}"
[[ -f "$XML" ]] || { echo "Animation not found: $XML" >&2; exit 1; }
if [[ -n "${NETANIM_BIN:-}" ]]; then exec "$NETANIM_BIN" "$XML"; fi
if command -v NetAnim >/dev/null; then exec NetAnim "$XML"; fi
if [[ -d /Applications/NetAnim.app ]]; then exec open -a /Applications/NetAnim.app "$XML"; fi
echo "NetAnim GUI is not installed. Install the official optional NetAnim GUI, set NETANIM_BIN to its executable, then run this command again. Use its file-open dialog for: $XML" >&2
exit 1
