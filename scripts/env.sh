#!/usr/bin/env bash
# Source this file; all installations are kept inside this project.
WSN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export CONTIKI="${CONTIKI:-$HOME/contiki-ng}"
export PATH="$WSN_ROOT/.runtime/toolchain/bin:$WSN_ROOT/.venv/bin:$PATH"
if [[ -z "${JAVA_HOME:-}" && -f "$WSN_ROOT/.runtime/cooja-java23/java-home" ]]; then
  export JAVA_HOME="$(cat "$WSN_ROOT/.runtime/cooja-java23/java-home")"
  export COOJA_JAR="${COOJA_JAR:-$WSN_ROOT/.runtime/cooja-java23/cooja.jar}"
fi
if [[ -z "${JAVA_HOME:-}" ]]; then
  for WSN_JDK in "$WSN_ROOT"/.runtime/jdk-*/Contents/Home "$WSN_ROOT"/.runtime/jdk-*; do
    if [[ -x "$WSN_JDK/bin/java" ]]; then export JAVA_HOME="$WSN_JDK"; break; fi
  done
fi
if [[ -n "${JAVA_HOME:-}" ]]; then export PATH="$JAVA_HOME/bin:$PATH"; fi
