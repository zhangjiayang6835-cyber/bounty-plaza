# DNS Zone Transfer Security Fix

This repository contains configuration files to fix the DNS Zone Transfer vulnerability described in issue #308.

## Problem
The DNS server was allowing zone transfers from any IP address, which could lead to internal network mapping by attackers.

## Solution
The implemented solution includes:
1. Restricting zone transfers (AXFR) to authorized slave servers only
2. Implementing TSIG (Transaction SIGnature) authentication for zone transfers
3. Using split-horizon DNS to separate internal and external views
4. Configuring proper access controls for recursive queries

## Configuration Files
- `dns-server/config/named.conf.options`: Main BIND options with security settings
- `dns-server/config/named.conf.local`: Zone configurations with transfer restrictions
- `dns-server/config/keys.conf`: TSIG keys for authentication
- `docker-compose.yml`: Docker setup for testing the configuration

## Testing
To test the configuration:
1. Start the DNS server and slave using `docker-compose up`
2. Attempt a zone transfer from an unauthorized IP (should fail)
3. Attempt a zone transfer from the slave server (should succeed with TSIG)

## Verification
The following security measures are in place:
- ✅ AXFR only allowed to slave servers with TSIG authentication
- ✅ TSIG signatures enabled for zone transfers
- ✅ Split-horizon DNS for internal and external zones