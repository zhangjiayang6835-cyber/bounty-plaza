# fix_jwt_kid_injection.py
import os
import jwt
from flask import request, jsonify

# Lista blanca de Key IDs permitidos
ALLOWED_KIDS = ['key-1', 'key-2', 'key-3']

def verify_jwt(token):
    """
    Verifica un JWT usando whitelist de Key IDs.
    """
    try:
        # Decodificar el header sin verificar
        header = jwt.get_unverified_header(token)
        kid = header.get('kid')
        
        # Validar que kid esté en la whitelist
        if kid not in ALLOWED_KIDS:
            raise ValueError(f"Invalid kid: {kid}")
        
        # Cargar la clave desde la whitelist (no desde la ruta del usuario)
        secret_key = load_secret_key(kid)
        
        # Verificar el JWT
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
        
    except Exception as e:
        raise ValueError(f"Invalid JWT: {e}")

def load_secret_key(kid):
    """
    Carga la clave secreta desde un almacén seguro, no desde la entrada del usuario.
    """
    # Usar un diccionario o base de datos en lugar de leer del sistema de archivos
    keys = {
        'key-1': 'secret-key-1',
        'key-2': 'secret-key-2',
        'key-3': 'secret-key-3'
    }
    return keys.get(kid)