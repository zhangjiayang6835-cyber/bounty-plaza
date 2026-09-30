```solidity
function getAgentCard(bytes calldata _arg) external view returns (bytes) {
    (bytes memory result) = _getAgentCard(_arg);
    return result;
}

function _getAgentCard(bytes calldata _arg) internal pure returns (bytes) {
    (bool ok, bytes memory data) = abi.decode(_arg, (bool, bytes));
    if (ok) {
        return abi.encode( (bool, bytes) (true, data) );
    }
    return abi.encode( (bool, bytes) (false, data) );
}
```