import java.io.*;

public class SafeObjectInputStream extends ObjectInputStream {
    private static final String[] ALLOWED_CLASSES = {
        "java.lang.String",
        "java.lang.Number",
        "java.lang.Long",
        "java.lang.Integer"
    };

    public SafeObjectInputStream(InputStream in) throws IOException {
        super(in);
    }

    @Override
    protected Class<?> resolveClass(ObjectStreamClass desc) throws IOException, ClassNotFoundException {
        boolean allowed = false;
        for (String cls : ALLOWED_CLASSES) {
            if (desc.getName().equals(cls)) {
                allowed = true;
                break;
            }
        }
        if (!allowed) {
            throw new InvalidClassException("Java RMI Deserialization Blocked (Issue #277): ", desc.getName());
        }
        return super.resolveClass(desc);
    }
}
