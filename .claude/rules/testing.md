# Reproducir antes de corregir

Aplica a todo fallo reportado en este repositorio: un bug que describe el
usuario, un test que ya falla, un error en un log, un comportamiento que no
coincide con `docs/contrato-api.md`.

## La regla

1. **Primero se reproduce**, con un caso real **contra el sistema**, no
   razonando sobre el código:
   - un **test que se ejecuta en rojo** por ese fallo —lo normal—, en `tests/`,
     que pasará a verde solo cuando el fallo esté corregido; o
   - si el fallo no cabe en un test (infraestructura, arranque, un comando
     externo), una **ejecución real** —`curl`, un script, el propio servidor—
     cuya salida deje **evidencia registrada** del fallo (en el PR, en el
     cuerpo del commit, o en `evidencias/`).
2. Se observa el rojo / la evidencia. Recién entonces se escribe la corrección.
3. Se corrige, y se comprueba que el mismo test pasa a verde / la misma
   ejecución ya no falla.

## La reproducción no se oculta

- El test de reproducción **se queda tal como se escribió**: no se borra, no se
  debilita, no se renombra para que parezca otra cosa. Queda como test de
  regresión.
- Si la reproducción fue una ejecución manual, su evidencia se conserva; no se
  reescribe la descripción del arreglo para dar a entender que el fallo nunca
  ocurrió.
- Si reproducir el fallo exige cambiar comportamiento acordado, se edita antes
  `docs/contrato-api.md`, en un commit separado (ver `CLAUDE.md` §Fuentes de
  verdad y §Pruebas).

## Por qué

Un parche sin reproducción previa no prueba que el fallo exista, no prueba que
lo corrija, y no deja nada que impida la regresión. Es el mismo principio que
`CLAUDE.md` §Pruebas aplica a las capacidades nuevas ("empieza por un test que
falla"), trasladado a los fallos.
