#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$WSN_ROOT"
mkdir -p .runtime
printf 'CONTIKI := %s\n' "$CONTIKI" > .runtime/contiki.mk
NODES="${1:-5}"
[[ "$NODES" =~ ^[0-9]+$ ]] || { echo 'Usage: run_simulation.sh [5|10] [output-directory]'; exit 2; }
SIMULATION="${WSN_SIMULATION:-contiki/simulations/wsn_${NODES}_nodes.csc}"
OUTPUT="${2:-analysis/results/cooja_${NODES}_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUTPUT"
OUTPUT="$(cd "$OUTPUT" && pwd)"
[[ ! -f "$OUTPUT/manifest.json" ]] || { echo "Refusing to overwrite an experiment: $OUTPUT"; exit 2; }
COOJA_JAR="${COOJA_JAR:-$CONTIKI/tools/cooja/build/libs/cooja.jar}"
[[ -f "$COOJA_JAR" ]] || { echo "Build Cooja first: cd $CONTIKI/tools/cooja && ./gradlew jar"; exit 1; }
cp "${SIMULATION%.csc}.json" "$OUTPUT/config.json"
cp "$SIMULATION" "$OUTPUT/simulation.csc"
python3 - "$OUTPUT" "$CONTIKI" "$COOJA_JAR" <<'PY'
import datetime, hashlib, json, pathlib, subprocess, sys, uuid
out, contiki = pathlib.Path(sys.argv[1]), sys.argv[2]
manifest = json.loads((out / 'config.json').read_text())
manifest.update(run_id=str(uuid.uuid4()), started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                source='cooja', name=f"Cooja · {manifest['nodes']} sensors · {manifest['duration_s']} s", telemetry_complete=True)
for key, path in [('contiki_commit', contiki), ('cooja_commit', contiki + '/tools/cooja')]:
    manifest[key] = subprocess.check_output(['git', '-C', path, 'rev-parse', 'HEAD'], text=True).strip()
manifest['cooja_jar_sha256'] = hashlib.sha256(pathlib.Path(sys.argv[3]).read_bytes()).hexdigest()
manifest['java_version'] = subprocess.check_output(['java','-version'],stderr=subprocess.STDOUT,text=True).splitlines()[0]
manifest['source_sha256'] = {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in pathlib.Path('contiki').rglob('*')
                           if p.is_file() and p.suffix in ('.c','.h') and 'build' not in p.parts}
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
PY
echo "Running Cooja with $NODES sensors; logs: $OUTPUT"
java -Djdk.lang.Process.launchMechanism=FORK --enable-native-access=ALL-UNNAMED -jar "$COOJA_JAR" --no-gui --no-log-color \
  --contiki="$CONTIKI" --logdir="$OUTPUT" "$SIMULATION" \
  > "$OUTPUT/cooja-console.log" 2>&1 || { tail -60 "$OUTPUT/cooja-console.log"; exit 1; }
echo "Cooja finished. Inspect $OUTPUT/COOJA.testlog and import with scripts/bridge.py."
