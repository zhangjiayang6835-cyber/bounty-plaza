\# Solución para el Bounty #60 - Reentrancy via ERC-777 Callback



\## Vulnerabilidad

La función `withdraw()` actualiza el balance del usuario \*\*después\*\* de llamar a `transfer()`. Un contrato ERC-777 puede reentrar y retirar fondos antes de que el balance se actualice.



\## Solución

1\. Se aplica el patrón \*\*Checks-Effects-Interactions\*\*: se actualiza el estado (balances) antes de realizar la transferencia (interacción externa).

2\. Se utiliza el modificador `nonReentrant` de OpenZeppelin para prevenir ataques de reentrancia.



\## Archivos modificados

\- `fix\_reentrancy.sol`: Contiene la lógica segura de retiro.



\## Pruebas

\- Verificado que el balance se actualiza antes de la transferencia.

\- Verificado que el `ReentrancyGuard` bloquea llamadas recursivas.

\- La función no es vulnerable a ataques de reentrancia.



Closes #60

