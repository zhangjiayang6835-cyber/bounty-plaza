package com.security.fixes;

import java.io.*;
import java.rmi.server.RMIClassLoader;

public class RMISecureObjectInputStream extends ObjectInputStream {
    private static final String[] ALLOWED_CLASSES = {
        "java.lang.String",
        "java.lang.Number",
        "java.util.ArrayList"
    };

    public RMISecureObjectInputStream(InputStream in) throws IOException {
        super(in);
    }

    @Override
    protected Class<?> resolveClass(ObjectStreamClass desc) throws IOException, ClassNotFoundException {
        boolean allowed = false;
        for (String allowedClass : ALLOWED_CLASSES) {
            if (desc.getName().equals(allowedClass)) {
                allowed = true;
                break;
            }
        }
        if (!allowed) {
            throw new InvalidClassException("Unauthorized RMI Deserialization attempt: " + desc.getName());
        }
        return super.resolveClass(desc);
    }
}
