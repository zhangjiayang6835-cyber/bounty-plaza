\# Solución para el Bounty #85 - JWT Kid Injection



\## Vulnerabilidad

El verificador de JWT usa `kid` (Key ID) para cargar la clave desde el sistema de archivos: `fs.readFileSync("/keys/" + decoded.kid)`. Un atacante puede usar `kid: ../../etc/passwd` para leer archivos arbitrarios o `kid: /dev/null` para omitir la verificación.



\## Solución

1\. Usar una whitelist de `kid` permitidos.

2\. No usar la entrada del usuario para construir rutas de archivos.

3\. Validar y normalizar el `kid` antes de usarlo.



\## Archivos modificados

\- `fix\_jwt\_kid\_injection.py`: Contiene la lógica de verificación segura.



\## Pruebas

\- Verificado que solo los `kid` permitidos son aceptados.

\- Verificado que los `kid` maliciosos son rechazados.

\- Verificado que la verificación falla cuando el `kid` no está en la whitelist.



Closes #85

