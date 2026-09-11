#!/usr/bin/env bash
# Hook PostToolUse (matcher Write|Edit).
# Se dispara tras cada Write/Edit; filtra en Python por si el archivo tocado
# es uno de los que afectan al schema de OpenAPI. Si no lo es, sale en
# silencio. Si lo es: regenera openapi.json (comando de README.md
# §Especificación OpenAPI) y avisa de que docs/esquema.md puede haber
# quedado viejo, nombrando la skill describir-esquema que lo regenera.
#
# No bloquea nada (PostToolUse ya corrió la edición): siempre sale 0.
# systemMessage se muestra al usuario; additionalContext se inyecta al modelo.

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

# Archivos que afectan al schema que produce app.openapi(): las rutas, sus
# responses/summary, y los modelos Pydantic de entrada/salida. app/models.py
# describe tablas (esquema de datos), no el schema HTTP: fuera de este filtro.
case "$archivo" in
  */app/main.py|*/app/schemas.py|*/app/routers/*.py) ;;
  *) exit 0 ;;
esac

salida_regen="$(
  uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True))" 2>&1 > openapi.json
)"
estado=$?

if [ $estado -ne 0 ]; then
  printf '{"systemMessage": "No se pudo regenerar openapi.json tras editar %s. Corre a mano el comando de README.md §Especificación OpenAPI."}\n' \
    "$(basename "$archivo")"
  exit 0
fi

printf '{"systemMessage": "openapi.json regenerado (cambió %s). docs/esquema.md puede haber quedado desactualizado; regénralo con la skill describir-esquema si el cambio tocó modelos o migraciones."}\n' \
  "$(basename "$archivo")"
exit 0
