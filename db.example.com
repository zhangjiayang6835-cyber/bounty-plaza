;
; BIND data file for example.com
;
$TTL    604800
@       IN      SOA     ns1.example.com. admin.example.com. (
                              1         ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         604800 )       ; Negative Cache TTL
;
@       IN      NS      ns1.example.com.
@       IN      A       203.0.113.10
ns1     IN      A       203.0.113.10
www     IN      A       203.0.113.20
mail    IN      A       203.0.113.30
api     IN      A       203.0.113.40