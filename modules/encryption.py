import os
import base64
import numpy as np
import io

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


class EncryptionManager:
    """
    Gère la dérivation de clé et le chiffrement/déchiffrement
    des templates biométriques (numpy arrays).

    Fichiers générés :
        database/secret.key.enc  → clé de données chiffrée avec le mot de passe maître
        database/secret.salt     → sel aléatoire pour PBKDF2
    """

    KEY_PATH  = "database/secret.key.enc"
    SALT_PATH = "database/secret.salt"
    ITERATIONS = 390_000  # OWASP 2023 recommandation

    # ------------------------------------------------------------------
    # Dérivation de clé depuis le mot de passe maître
    # ------------------------------------------------------------------

    def _derive_master_key(self, master_password: str, salt: bytes) -> bytes:
        """
        Dérive une clé Fernet (32 octets base64url) depuis le mot de passe
        et le sel via PBKDF2-HMAC-SHA256.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.ITERATIONS,
        )
        raw_key = kdf.derive(master_password.encode("utf-8"))
        return base64.urlsafe_b64encode(raw_key)

    # ------------------------------------------------------------------
    # Gestion de la clé de données
    # ------------------------------------------------------------------

    def ensure_data_key(self, master_password: str) -> bytes:
        """
        - Si la clé de données n'existe pas encore → en génère une nouvelle,
          la chiffre avec le mot de passe maître, la sauvegarde.
        - Si elle existe → la déchiffre et la retourne.

        Retourne la clé de données brute (bytes utilisables avec Fernet).
        """
        os.makedirs("database", exist_ok=True)

        if not os.path.exists(self.SALT_PATH) or not os.path.exists(self.KEY_PATH):
            # Première utilisation : créer sel + clé de données
            salt = os.urandom(32)
            master_fernet_key = self._derive_master_key(master_password, salt)
            master_fernet = Fernet(master_fernet_key)

            data_key = Fernet.generate_key()                   # clé de données
            encrypted_data_key = master_fernet.encrypt(data_key)

            with open(self.SALT_PATH, "wb") as f:
                f.write(salt)
            with open(self.KEY_PATH, "wb") as f:
                f.write(encrypted_data_key)

            print("  → Nouvelle clé de données créée et chiffrée.")
            return data_key

        else:
            # Clé existante : déchiffrer
            with open(self.SALT_PATH, "rb") as f:
                salt = f.read()
            with open(self.KEY_PATH, "rb") as f:
                encrypted_data_key = f.read()

            master_fernet_key = self._derive_master_key(master_password, salt)
            master_fernet = Fernet(master_fernet_key)

            try:
                data_key = master_fernet.decrypt(encrypted_data_key)
            except Exception:
                raise ValueError(
                    "Mot de passe maître incorrect ou fichier de clé corrompu."
                )

            print("  → Clé de données chargée depuis le disque.")
            return data_key

    # ------------------------------------------------------------------
    # Chiffrement / Déchiffrement de templates numpy
    # ------------------------------------------------------------------

    def encrypt_template(self, template: np.ndarray, data_key: bytes) -> bytes:
        """
        Sérialise un numpy array et le chiffre avec la clé de données.
        """
        buffer = io.BytesIO()
        np.save(buffer, template)
        raw_bytes = buffer.getvalue()

        fernet = Fernet(data_key)
        return fernet.encrypt(raw_bytes)

    def decrypt_template(self, encrypted_blob: bytes, data_key: bytes) -> np.ndarray:
        """
        Déchiffre et désérialise un numpy array.
        """
        fernet = Fernet(data_key)
        raw_bytes = fernet.decrypt(encrypted_blob)

        buffer = io.BytesIO(raw_bytes)
        return np.load(buffer)
