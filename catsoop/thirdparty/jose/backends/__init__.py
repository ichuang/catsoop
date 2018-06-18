
try:
    from .pycrypto_backend import RSAKey
except ImportError:
    try:
        from .cryptography_backend import CryptographyRSAKey as RSAKey
    except ImportError:
        from .rsa_backend import RSAKey

try:
    from .cryptography_backend import CryptographyECKey as ECKey
except ImportError:
    from .ecdsa_backend import ECDSAECKey as ECKey
