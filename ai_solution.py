To resolve the issue where USDC-quoted pairs are not displaying the correct market cap, the code should ensure that the market cap is converted to USDC when the quote currency is USDC. 

Here is the corrected code:

```javascript
marketcap = (price * volume).toFormat();
if (quoteCurrency == 'USDC') {
    marketcap = convert(marketcap, 'BTC', 'USDC');
}
```