\# Solución para el Bounty #57 - Bleichenbacher Oracle



\## Vulnerabilidad

La implementación RSA-OAEP devuelve mensajes de error distintos según el tipo de fallo, creando un oracle que permite ataques de Bleichenbacher.



\## Solución

1\. Unificar todos los mensajes de error.

2\. Implementar comparaciones en tiempo constante.

3\. Usar una respuesta dummy para fallos de descifrado.



\## Archivos modificados

\- `fix\_bleichenbacher.py`: Contiene la lógica de descifrado seguro.



\## Pruebas

\- Verificado que los mensajes de error son idénticos.

\- Verificado que las comparaciones son en tiempo constante.

\- Verificado que no se filtra información del descifrado.



Closes #57

