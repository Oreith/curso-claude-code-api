#!/usr/bin/env bash
# Hook PostToolUse (matcher Write|Edit).
# Se dispara tras cada Write/Edit; filtra en Python por si el archivo tocado
# es openapi.json. Si lo es, avisa de que la colección de Postman puede haber
# quedado vieja y nombra la skill que la regenera. Solo avisa: no llama a
# ninguna herramienta de Postman ni ejecuta la skill por su cuenta.
#
# No bloquea nada (PostToolUse ya corrió la edición): siempre sale 0.
# systemMessage se muestra al usuario.

set -uo pipefail
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

entrada="$(cat)"

archivo="$(
  printf '%s' "$entrada" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get('tool_input', {}).get('file_path', ''))
"
)"

case "$archivo" in
  */openapi.json|openapi.json) ;;
  *) exit 0 ;;
esac

printf '{"systemMessage": "openapi.json cambió: la colección de Postman puede haber quedado vieja. Regenérala con la skill construir-coleccion-postman."}\n'
exit 0
