#!/usr/bin/env python3
"""Build an isolated Cooja jar for an installed Java 23 JDK, without editing Contiki.

This is tested for the repository's recorded Cooja revision. Its Java sources use
APIs available in Java 23 even though the upstream Gradle build targets Java 25.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def prepare(contiki, java_home):
    source = contiki / "tools/cooja"
    original = source / "build/libs/cooja.jar"
    dependencies = source / "build/libs/lib"
    if not original.is_file() or not dependencies.is_dir():
        raise SystemExit("An existing built Cooja jar and dependency directory are required")
    dest = ROOT / ".runtime/cooja-java23"
    classes = dest / "classes"
    classes.mkdir(parents=True, exist_ok=True)
    sources = list((source / "java").rglob("*.java")) + list((source / "tools/coffee-manager").rglob("*.java"))
    subprocess.run([str(java_home / "bin/javac"), "--release", "23", "-cp", str(dependencies / "*"),
                    "-d", str(classes), *map(str, sources)], check=True)
    jar = dest / "cooja.jar"
    with zipfile.ZipFile(original) as old, zipfile.ZipFile(jar, "w", zipfile.ZIP_DEFLATED) as new:
        for item in old.infolist():
            if not item.filename.endswith(".class"):
                new.writestr(item, old.read(item.filename))
        for path in classes.rglob("*.class"):
            new.write(path, str(path.relative_to(classes)))
    link = dest / "lib"
    if not link.exists(): link.symlink_to(dependencies, target_is_directory=True)
    (dest / "java-home").write_text(str(java_home) + "\n")
    subprocess.run([str(java_home / "bin/java"), "-jar", str(jar), "--version"], check=True)
    print(f"Local compatible jar: {jar}")

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--contiki", type=Path, default=Path(os.environ.get("CONTIKI", Path.home()/"contiki-ng")))
    p.add_argument("--java-home", type=Path)
    a=p.parse_args()
    if not a.java_home:
        if Path('/usr/libexec/java_home').is_file():
            a.java_home=Path(subprocess.check_output(['/usr/libexec/java_home','-v','23'],text=True).strip())
        else:
            a.java_home=Path(os.environ.get('JAVA_HOME', Path(shutil.which('javac')).resolve().parents[1]))
    prepare(a.contiki.resolve(), a.java_home.resolve())
