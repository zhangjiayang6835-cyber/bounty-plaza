import io
import pickle

class RestrictedUnpickler(pickle.Unpickler):
    """Restricted unpickler preventing arbitrary code execution exploits (Issue #302)."""
    SAFE_MODULES = {'datetime', 'decimal'}

    def find_class(self, module, name):
        if module in self.SAFE_MODULES:
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"Forbidden unpickling attempt from module: '{module}', class: '{name}'")

def safe_loads(pickled_bytes: bytes):
    return RestrictedUnpickler(io.BytesIO(pickled_bytes)).load()
