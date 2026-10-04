;
; BIND data file for example.com
;
$TTL    86400
@       IN      SOA     ns1.example.com. admin.example.com. (
                              1         ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         86400 )        ; Negative Cache TTL
;
@       IN      NS      ns1.example.com.
@       IN      NS      ns2.example.com.
@       IN      A       203.0.113.1
@       IN      MX      10 mail.example.com.

ns1     IN      A       203.0.113.1
ns2     IN      A       203.0.113.2
mail    IN      A       203.0.113.10
www     IN      A       203.0.113.100

; Internal servers (not visible to external queries)
internal IN      A       192.168.1.10
db      IN      A       192.168.1.20
app     IN      A       192.168.1.30
