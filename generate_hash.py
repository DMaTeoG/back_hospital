import os
import base64
import hashlib

PASSWORDS = ['admin123', 'doctor123', 'patient123']
ITERATIONS = 720000
ALG = 'pbkdf2_sha256'

for pwd in PASSWORDS:
    salt = base64.b64encode(os.urandom(12)).decode().strip().replace('=', '')
    dk = hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt.encode(), ITERATIONS)
    hash_b64 = base64.b64encode(dk).decode().strip()
    print(f"{pwd}: {ALG}")
