# DNS Zone Transfer Fix

This configuration addresses the DNS Zone Transfer vulnerability by implementing:

1. **Restricted Zone Transfers**: Only allows transfers to specified slave servers using TSIG authentication
2. **TSIG Authentication**: Uses HMAC-SHA256 for secure zone transfers
3. **Split-Horizon DNS**: Separates internal and external DNS zones

## Configuration Files

- `named.conf.options`: Main BIND options
- `named.conf.zones`: Zone definitions with transfer restrictions
- `db.internal.example.com`: Internal DNS zone (not exposed to external queries)
- `db.example.com`: External DNS zone
- `db.192.168.1`: Reverse zone for internal network

## Key Security Features

1. `allow-transfer { key transfer-key; <slave-ip>; };` - Only allows transfers to authorized slaves
2. `allow-query` restrictions - Limits who can query internal zones
3. Separate internal and external zone files
4. TSIG key for secure communication

## Implementation Notes

1. Replace "YourSecureTSIGKeyHere=" with a securely generated TSIG key
2. Update IP addresses to match your network configuration
3. Ensure proper file permissions (bind:bind) for all zone files
4. Test configuration with `named-checkconf` and `named-checkzone`