;
; BIND data file for internal.example.com (slave zone)
;
$TTL    86400
@       IN      SOA     ns1.internal.example.com. admin.internal.example.com. (
                              1         ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         86400 )        ; Negative Cache TTL
;
@       IN      NS      ns1.internal.example.com.
@       IN      NS      ns2.internal.example.com.

ns1     IN      A       192.168.1.1
ns2     IN      A       192.168.1.2

; Internal services
api     IN      A       192.168.1.10
db      IN      A       192.168.1.20
app     IN      A       192.168.1.30
dev     IN      A       192.168.1.40
