#!/usr/bin/env bash
# Hook PreToolUse (matcher Bash, filtro `if: Bash(git commit:*)`).
# Bloquea el commit si openapi.json no coincide con la especificación que
# genera el código ahora mismo. El comando de regeneración es el que está
# escrito en README.md §Especificación OpenAPI.
#
# Sale 0 => deja pasar el commit. Sale 2 => lo bloquea y el texto de stderr
# se le muestra a Claude (contrato de los hooks PreToolUse).

set -uo pipefail
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

esperado="$(
  uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True))" 2>/dev/null
)" || {
  echo "No se pudo generar la especificación (¿uv run falla?). Revísalo antes de commitear." >&2
  exit 2
}

if [ -z "$esperado" ]; then
  echo "La generación de la especificación devolvió vacío. Revísalo antes de commitear." >&2
  exit 2
fi

if diff -q <(printf '%s\n' "$esperado") openapi.json >/dev/null 2>&1; then
  exit 0
fi

cat >&2 <<'MSG'
openapi.json no coincide con la especificación que genera el código.

Regenéralo con el comando de README.md §Especificación OpenAPI:

  uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True))" > openapi.json

Luego `git add openapi.json` y repite el commit. Si el cambio de la
especificación es intencionado, inclúyelo en este mismo commit o en uno
previo.
MSG
exit 2
