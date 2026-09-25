```solidity
function getA() public view returns (uint) {
    return a;
}

function getB() public view returns (uint) {
    return b;
}

function getAB() public view returns (uint) {
    return a * b;
}

function getC() public view returns (uint) {
    return c;
}

function isConditionMet() public view returns (bool) {
    return (a * b >= c);
}
```