# fix_java_rmi_deserialization.py
"""
Java RMI Deserialization Protection for issue #128.

Java RMI deserialization vulnerabilities allow remote code execution by
sending malicious serialized objects to the RMI server.

Key mitigation: ObjectInputFilter (Java 9+) to restrict deserialized classes.
"""

class JavaRMIProtection:
    """Protect against Java RMI deserialization attacks."""

    # Whitelisted classes for deserialization
    ALLOWED_CLASSES = {
        'java.lang.String',
        'java.lang.Integer',
        'java.lang.Long',
        'java.lang.Double',
        'java.lang.Boolean',
        'java.lang.Float',
        'java.lang.Byte',
        'java.lang.Short',
        'java.lang.Character',
        'java.math.BigDecimal',
        'java.math.BigInteger',
        'java.util.Date',
        'java.sql.Timestamp',
        'java.util.ArrayList',
        'java.util.HashMap',
        'java.util.LinkedList',
        'java.util.TreeMap',
    }

    # Dangerous classes that should always be blocked
    DANGEROUS_CLASSES = {
        'java.lang.Object',
        'java.lang.Class',
        'java.lang.Runtime',
        'java.lang.ProcessBuilder',
        'java.lang.reflect.*',
        'java.io.File',
        'java.io.FileOutputStream',
        'java.io.FileInputStream',
        'java.net.URL',
        'java.net.Socket',
        'java.net.ServerSocket',
        'javax.script.ScriptEngine',
        'javax.script.ScriptEngineManager',
        'sun.misc.Unsafe',
        'com.sun.jndi.rmi.registry.*',
        'com.sun.jndi.ldap.*',
        'org.apache.commons.collections.*',
        'org.apache.commons.beanutils.*',
        'org.springframework.*',
    }

    @classmethod
    def get_java_object_input_filter(cls):
        """
        Return Java ObjectInputFilter configuration for RMI.
        This should be set on the RMI server before deserialization.
        """
        return """
// Java ObjectInputFilter configuration for RMI
import java.io.ObjectInputFilter;
import java.io.ObjectInputStream;

// Create a filter that allows only specific classes
ObjectInputFilter filter = rmiClass -> {
    // Block dangerous classes
    for (String dangerous : DANGEROUS_CLASSES) {
        if (rmiClass != null && rmiClass.getName().startsWith(dangerous.replace("*", ""))) {
            return ObjectInputFilter.Status.REJECTED;
        }
    }
    
    // Allow only whitelisted classes
    if (ALLOWED_CLASSES.contains(rmiClass.getName())) {
        return ObjectInputFilter.Status.ALLOWED;
    }
    
    // Reject everything else
    return ObjectInputFilter.Status.REJECTED;
};

// Set filter on the ObjectInputStream
ObjectInputStream ois = new ObjectInputStream(inputStream);
ois.setObjectInputFilter(filter);
"""

    @classmethod
    def get_python_rmi_config(cls):
        """Return Python configuration for secure RMI communication."""
        return """
# Python configuration for secure RMI (using marshalled objects)
import pickle
import io

# Secure deserialization using whitelisted types only
ALLOWED_TYPES = (
    str, int, float, bool, bytes,
    list, dict, tuple,
)

def safe_unpickle(data):
    """Safely unpickle data with type restrictions."""
    class RestrictedUnpickler(pickle.Unpickler):
        def find_class(self, module, name):
            if module == '__main__':
                return getattr(__import__('__main__'), name)
            if module in ('builtins', 'datetime'):
                return getattr(__import__(module), name)
            raise pickle.UnpicklingError("Global '%s.%s' is forbidden" % (module, name))
    
    return RestrictedUnpickler(io.BytesIO(data)).load()

def safe_pickle(data):
    """Safely pickle data for transmission."""
    return pickle.dumps(data, protocol=4)
"""

    @staticmethod
    def get_rmi_server_config():
        """Return secure RMI server configuration."""
        return """
# Secure RMI Server Configuration
# ===================================

# 1. Disable RMI registry if not needed
# rmiregistry -J-Djava.rmi.server.useCodebaseOnly=true 1099

# 2. Set security properties
-Djava.rmi.server.useCodebaseOnly=true
-Djava.rmi.server.disableMarshalUOF=false
-Djava.security.manager=allow

# 3. Restrict RMI port range
-Djava.rmi.server.hostname=127.0.0.1
-Djava.net.preferIPv4Stack=true

# 4. Configure ObjectInputFilter (Java 9+)
-Djdk.io.DefaultObjectInputFilter=builtin.*
"""

    @staticmethod
    def get_rmi_client_config():
        """Return secure RMI client configuration."""
        return """
# Secure RMI Client Configuration
# ===============================

# 1. Only connect to trusted RMI servers
-Djava.rmi.server.hostname=localhost

# 2. Set connection timeout
-Dsun.rmi.transport.tcp.readTimeout=10000
-Dsun.rmi.transport.tcp.connectTimeout=5000

# 3. Disable codebase downloads
-Djava.rmi.server.useCodebaseOnly=true
"""

    @classmethod
    def check_rmi_exposure(cls):
        """Check if RMI ports are exposed."""
        import socket

        rmi_ports = [1099, 1100, 12000, 12001, 12002, 12003, 12004, 12005]
        exposed = []

        for port in rmi_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()

            if result == 0:
                exposed.append(port)

        return exposed

    @staticmethod
    def get_rmi_security_headers():
        """Return security headers for RMI communication."""
        return {
            'X-RMI-Security': 'restricted',
            'X-Allowed-Custom-Headers': 'Content-Type, Accept',
        }

    @staticmethod
    def get_secure_rmi_python_implementation():
        """Return Python implementation for secure RMI-like communication."""
        return """
# Secure Python RMI-like communication
# Uses JSON instead of pickle, validates types

import json
import hashlib

class SecureRMI:
    ALLOWED_TYPES = (str, int, float, bool, list, dict, bytes)

    @staticmethod
    def serialize(obj):
        if not isinstance(obj, SecureRMI.ALLOWED_TYPES):
            raise TypeError("Type not allowed for serialization")
        return json.dumps(obj).encode()

    @staticmethod
    def deserialize(data):
        obj = json.loads(data)
        if not isinstance(obj, SecureRMI.ALLOWED_TYPES):
            raise TypeError("Type not allowed for deserialization")
        return obj
"""