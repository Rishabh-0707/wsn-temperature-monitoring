#!/usr/bin/env bash
# Install the tested GNU Make version locally when the host only has old Make.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="$ROOT/.runtime/toolchain"
mkdir -p "$PREFIX/bin" "$ROOT/.runtime"
if [[ -x "$PREFIX/bin/make" ]]; then "$PREFIX/bin/make" --version | head -1; exit 0; fi
if command -v gmake >/dev/null 2>&1; then
  ln -s "$(command -v gmake)" "$PREFIX/bin/make"
  "$PREFIX/bin/make" --version | head -1
  exit 0
fi
ARCHIVE="$ROOT/.runtime/make-4.4.1.tar.gz"
curl -fL --retry 2 https://ftp.gnu.org/gnu/make/make-4.4.1.tar.gz -o "$ARCHIVE"
python3 - "$ARCHIVE" <<'PY'
import hashlib, pathlib, sys
digest = hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest()
expected = 'dd16fb1d67bfab79a72f5e8390735c49e3e8e70b4945a15ab1f81ddb78658fb3'
if digest != expected: raise SystemExit('GNU Make archive checksum mismatch')
PY
tar -xzf "$ARCHIVE" -C "$ROOT/.runtime"
cd "$ROOT/.runtime/make-4.4.1"
./configure --prefix="$PREFIX"
make -j4
make install
"$PREFIX/bin/make" --version | head -1
