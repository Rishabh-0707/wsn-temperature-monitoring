"""Record the exact compiled project sources and executable after a successful build."""
import hashlib
import json
from pathlib import Path
import sys
root, runtime = map(Path, sys.argv[1:])
source = root/'ns3'
files = sorted([*(source/'src').glob('*.cc'), *(source/'src').glob('*.h'), *(source/'scratch').glob('*.cc')])
exe=runtime/'scratch/wsn-platform/ns3.46-wsn-temperature-default'
manifest={'simulator_version':'3.46','binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
          'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(runtime/'wsn-build.json').write_text(json.dumps(manifest,indent=2)+'\n')
