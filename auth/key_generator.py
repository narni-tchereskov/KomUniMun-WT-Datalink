from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pathlib import Path

# Set a password here if you want your private key to be encrypted.
KEY_PASSWORD = 553  # Use None for no password.

print("Generating new 2048-bit RSA private key...")
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

encryption_algo = serialization.NoEncryption()
if KEY_PASSWORD is not None:
    password_bytes = str(KEY_PASSWORD).encode("utf-8")
    encryption_algo = serialization.BestAvailableEncryption(password_bytes)

pem_private = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=encryption_algo,
)

public_key = private_key.public_key()
pem_public = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

folder = Path(__file__).parent

with open(folder / "client_private.pem", "wb") as f:
    f.write(pem_private)

with open(folder / "client_public.pem", "wb") as f:
    f.write(pem_public)

print("Private key generated")
