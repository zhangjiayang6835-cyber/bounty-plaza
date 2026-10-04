;
; BIND data file for internal.example.com
;
$TTL    604800
@       IN      SOA     ns1.internal.example.com. admin.internal.example.com. (
                              2         ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         604800 )       ; Negative Cache TTL
;
@       IN      NS      ns1.internal.example.com.
@       IN      A       192.168.1.10
ns1     IN      A       192.168.1.10
mail    IN      A       192.168.1.20
www     IN      A       192.168.1.30
db      IN      A       192.168.1.40
server1 IN      A       192.168.1.50
server2 IN      A       192.168.1.60