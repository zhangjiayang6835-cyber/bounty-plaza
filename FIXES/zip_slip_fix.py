import os
import zipfile

def safe_extract_zip(zip_file_path: str, target_dir: str):
    """Protects against Zip Slip arbitrary file overwrite vulnerability (Issue #292)."""
    target_dir = os.path.abspath(target_dir)

    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        for member in zip_ref.namelist():
            destination_path = os.path.abspath(os.path.join(target_dir, member))
            if not destination_path.startswith(target_dir + os.sep):
                raise SecurityError(f"Zip Slip Exploit Attempt Blocked: '{member}' target outside root dir.")
            zip_ref.extract(member, target_dir)
