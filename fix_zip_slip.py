# fix_zip_slip.py
import os
import zipfile
import tempfile

class ZipSlipProtection:
    """Protect against Zip Slip path traversal attacks."""

    @staticmethod
    def safe_extract(zip_path, extract_dir=None):
        """
        Safely extract a ZIP archive, preventing path traversal.
        Raises ValueError if a malicious entry is detected.
        """
        if extract_dir is None:
            extract_dir = tempfile.mkdtemp()

        extract_dir = os.path.realpath(os.path.abspath(extract_dir))

        with zipfile.ZipFile(zip_path, 'r') as zf:
            for entry in zf.namelist():
                # Resolve the full path
                full_path = os.path.realpath(os.path.join(extract_dir, entry))

                # Check for path traversal
                if not full_path.startswith(extract_dir + os.sep):
                    raise ValueError(f"Zip Slip detected: {entry} would write outside target directory")

                # Check for absolute paths
                if os.path.isabs(entry):
                    raise ValueError(f"Zip Slip detected: absolute path {entry}")

                # Check for path traversal sequences
                if '..' in entry.split(os.sep):
                    raise ValueError(f"Zip Slip detected: path traversal in {entry}")

                # Create parent directories if needed
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                # Extract the file
                with zf.open(entry) as source, open(full_path, 'wb') as target:
                    target.write(source.read())

        return extract_dir

    @staticmethod
    def is_safe_path(entry_path):
        """Check if a ZIP entry path is safe."""
        if '..' in entry_path.split(os.sep):
            return False
        if os.path.isabs(entry_path):
            return False
        return True