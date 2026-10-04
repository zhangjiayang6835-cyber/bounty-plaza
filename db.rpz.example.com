;
; RPZ (Response Policy Zone) for split-horizon DNS
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

; Block access to internal domains
internal.example.com   CNAME   .
api.internal.example.com   CNAME   .
db.internal.example.com   CNAME   .

; Return NXDOMAIN for sensitive internal domains
1.168.192.in-addr.arpa. CNAME   .

; Override external records with internal information
www.example.com      CNAME   www-internal.example.com.
www-internal.example.com.   IN      A       192.168.1.100
