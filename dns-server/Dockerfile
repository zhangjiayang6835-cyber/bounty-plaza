FROM bind:9.16

# Copy configuration files
COPY config/named.conf /etc/bind/named.conf
COPY config/named.conf.options /etc/bind/named.conf.options
COPY config/named.conf.local /etc/bind/named.conf.local
COPY config/named.conf.default-zones /etc/bind/named.conf.default-zones
COPY config/keys.conf /etc/bind/keys.conf

# Copy zone files
COPY config/db.internal /etc/bind/db.internal
COPY config/db.example /etc/bind/db.example

# Expose DNS ports
EXPOSE 53/tcp 53/udp

# Run BIND as non-root
USER bind

# Start BIND
CMD ["named", "-g"]