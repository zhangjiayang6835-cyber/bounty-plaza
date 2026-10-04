# DNS Zone Transfer Security Fix

This repository contains configuration files to fix DNS zone transfer vulnerabilities as described in issue #250.

## Problem

DNS servers were allowing zone transfers (AXFR) from any IP address, which could expose internal network topology to attackers.

## Solution

The configuration files implement the following security measures:

1. **Restrict AXFR to only slave servers**
   - BIND: `allow-transfer` directive with specific IP addresses
   - Unbound: Zone transfers are disabled by default

2. **Enable TSIG signatures for authentication**
   - BIND: TSIG key configuration for secure zone transfers
   - Unbound: SSL/TLS certificate configuration for secure communication

3. **Split-horizon DNS for internal domains**
   - Different views for internal and external clients
   - Internal clients see internal network information
   - External clients see only public information

## Files

- `named.conf.options`: BIND configuration file
- `unbound.conf`: Unbound configuration file
- `README.md`: This file

## Deployment Instructions

### For BIND

1. Replace the existing `named.conf.options` with this file
2. Update the TSIG secret with a secure key
3. Adjust IP addresses to match your network
4. Restart the BIND service

### For Unbound

1. Replace the existing `unbound.conf` with this file
2. Generate SSL certificates if not already present
3. Adjust IP addresses and domain names to match your environment
4. Restart the Unbound service

## Verification

After deployment, verify the configuration:

1. Check that zone transfers are only allowed to specified slave servers
2. Verify TSIG signatures are working
3. Confirm split-horizon DNS is functioning correctly
4. Test from both internal and external networks to ensure proper access controls

## Notes

- Replace all example IP addresses and domain names with your actual values
- Generate strong TSIG keys and SSL certificates
- Regularly review and update access control lists
- Monitor DNS server logs for any unauthorized access attempts