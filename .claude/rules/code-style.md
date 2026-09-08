# Repartir cambios sin reescribir código

Aplica a cualquier automatización de este repositorio que **reparta o
reorganice cambios que ya están en el árbol de trabajo** en commits —hoy
`.claude/skills/segmentar-commits/SKILL.md`, y cualquiera que se añada después.

## La regla

- Ningún reparto **reescribe código para simular un estado intermedio**: no se
  edita, borra ni restaura una sola línea para que un commit "salga" como se
  quiere.
- Cada commit se arma **solo con `git add`** sobre el cambio que ya existe:
  archivos completos, o `git add -p` para tomar *hunks* sueltos (`git add -N`
  antes de `-p` si el archivo aún no tiene seguimiento).
- Si dos intenciones comparten un archivo modificado, se separan con
  `git add -p`, nunca editando el archivo.

## Verificar un estado intermedio

Si hace falta comprobar un commit en aislamiento antes de seguir, se usa
`git stash` (o `git stash --include-untracked`) para apartar lo que todavía no
está en el índice, se corre la comprobación, y se restaura con `git stash pop`.
Eso no toca código. El estado intermedio se **verifica**, no se **fabrica**.

## Por qué

El árbol de trabajo es la única fuente; el reparto solo elige qué parte de él
entra en cada commit. Editar código para forzar un estado intermedio introduce
diferencias que nadie revisó y puede dejar el commit distinto de lo aprobado.
