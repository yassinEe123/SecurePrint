import os
import sqlite3
import hashlib
from datetime import datetime
from cryptography.fernet import Fernet


class StorageManager:
    """
    Stockage SQLite avec chiffrement Fernet de TOUTES les données sensibles.

    Conformité RGPD :
    - Aucune donnée personnelle en clair dans la base
    - Templates biométriques chiffrés
    - Identifiants utilisateurs chiffrés (+ hash sans sel pour le lookup)
    - Horodatages chiffrés (révèlent des patterns comportementaux)
    - Logs d'audit entièrement chiffrés
    - Droit à l'effacement via DELETE CASCADE + VACUUM

    Colonnes en clair autorisées :
    - id (INTEGER, clé technique interne)
    - username_hash (pseudonyme SHA-256 pour les requêtes de recherche)
    - user_id dans audit_log (clé technique, ne permet pas l'identification
      sans la data_key pour déchiffrer la table users)
    """

    def __init__(self, db_path: str = "database/secureprint.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    # ------------------------------------------------------------------
    # Connexion
    # ------------------------------------------------------------------

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA secure_delete = ON;")
        return conn

    # ------------------------------------------------------------------
    # Helpers de chiffrement
    # ------------------------------------------------------------------

    def _hash_username(self, username: str) -> str:
        return hashlib.sha256(username.encode("utf-8")).hexdigest()

    def _encrypt(self, value: str, data_key: bytes) -> bytes:
        return Fernet(data_key).encrypt(value.encode("utf-8"))

    def _decrypt(self, blob: bytes, data_key: bytes) -> str:
        return Fernet(data_key).decrypt(blob).decode("utf-8")

    def _now_encrypted(self, data_key: bytes) -> bytes:
        return self._encrypt(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), data_key)

    # ------------------------------------------------------------------
    # Création des tables (schéma 100 % chiffré)
    # ------------------------------------------------------------------

    def create_tables(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            username_hash               TEXT    UNIQUE NOT NULL,
            username_encrypted          BLOB    NOT NULL,
            created_at_encrypted        BLOB    NOT NULL,
            last_authenticated_encrypted BLOB
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id              INTEGER NOT NULL,
            encrypted_template   BLOB    NOT NULL,
            created_at_encrypted BLOB    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type_encrypted BLOB NOT NULL,
            user_id              INTEGER,
            success_encrypted    BLOB NOT NULL,
            timestamp_encrypted  BLOB NOT NULL,
            ip_encrypted         BLOB,
            details_encrypted    BLOB
        );
        """)

        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    def log_event(self, event_type: str, data_key: bytes,
                  user_id=None, success=True,
                  ip_address="127.0.0.1", details=""):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO audit_log
            (event_type_encrypted, user_id, success_encrypted,
             timestamp_encrypted, ip_encrypted, details_encrypted)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            self._encrypt(event_type, data_key),
            user_id,
            self._encrypt(str(int(success)), data_key),
            self._now_encrypted(data_key),
            self._encrypt(ip_address, data_key) if ip_address else None,
            self._encrypt(details, data_key)     if details    else None,
        ))

        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Enrôlement
    # ------------------------------------------------------------------

    def enroll_user(self, username: str, encrypted_template: bytes,
                    data_key: bytes):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
            INSERT INTO users (username_hash, username_encrypted, created_at_encrypted)
            VALUES (?, ?, ?)
            """, (
                self._hash_username(username),
                self._encrypt(username, data_key),
                self._now_encrypted(data_key),
            ))
            user_id = cursor.lastrowid

            cursor.execute("""
            INSERT INTO templates (user_id, encrypted_template, created_at_encrypted)
            VALUES (?, ?, ?)
            """, (user_id, encrypted_template, self._now_encrypted(data_key)))

            conn.commit()
            conn.close()

            self.log_event("enrollment", data_key, user_id=user_id,
                           success=True, details="Utilisateur enrôlé avec succès")
            return user_id

        except sqlite3.IntegrityError:
            conn.rollback()
            conn.close()
            self.log_event("enrollment", data_key, success=False,
                           details="Échec : username existe déjà")
            raise ValueError(f"L'utilisateur '{username}' existe déjà.")

        except Exception as e:
            conn.rollback()
            conn.close()
            self.log_event("enrollment", data_key, success=False,
                           details=f"Erreur inattendue : {e}")
            raise

    # ------------------------------------------------------------------
    # Recherche utilisateur
    # ------------------------------------------------------------------

    def get_user_by_username(self, username: str):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, created_at_encrypted, last_authenticated_encrypted
        FROM users WHERE username_hash = ?
        """, (self._hash_username(username),))

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        user_id, created_enc, last_enc = row
        return (user_id, username, created_enc, last_enc)

    def get_user_by_username_decrypted(self, username: str, data_key: bytes):
        row = self.get_user_by_username(username)
        if row is None:
            return None
        user_id, uname, created_enc, last_enc = row
        created  = self._decrypt(created_enc, data_key)
        last_auth = self._decrypt(last_enc, data_key) if last_enc else None
        return (user_id, uname, created, last_auth)

    # ------------------------------------------------------------------
    # Récupération de template
    # ------------------------------------------------------------------

    def get_template_by_username(self, username: str):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT t.encrypted_template
        FROM templates t
        JOIN users u ON t.user_id = u.id
        WHERE u.username_hash = ?
        ORDER BY t.created_at_encrypted DESC
        LIMIT 1
        """, (self._hash_username(username),))

        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def get_all_templates(self, data_key: bytes):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT u.username_encrypted, t.encrypted_template
        FROM templates t
        JOIN users u ON t.user_id = u.id
        """)

        rows = cursor.fetchall()
        conn.close()

        return [
            (self._decrypt(uname_enc, data_key), tmpl_enc)
            for uname_enc, tmpl_enc in rows
        ]

    # ------------------------------------------------------------------
    # Mise à jour dernière authentification
    # ------------------------------------------------------------------

    def update_last_authenticated(self, user_id: int, data_key: bytes):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE users SET last_authenticated_encrypted = ? WHERE id = ?
        """, (self._now_encrypted(data_key), user_id))

        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Suppression utilisateur (droit à l'effacement RGPD)
    # ------------------------------------------------------------------

    def delete_user(self, username: str, data_key: bytes) -> bool:
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username_hash = ?",
                       (self._hash_username(username),))
        row = cursor.fetchone()

        if row is None:
            conn.close()
            self.log_event("deletion", data_key, success=False,
                           details="Suppression impossible : utilisateur introuvable")
            return False

        cursor.execute("DELETE FROM users WHERE username_hash = ?",
                       (self._hash_username(username),))
        conn.commit()
        cursor.execute("VACUUM;")
        conn.commit()
        conn.close()

        self.log_event("deletion", data_key, success=True,
                       details="Suppression utilisateur effectuée")
        return True

    # ------------------------------------------------------------------
    # Liste des utilisateurs (déchiffrée)
    # ------------------------------------------------------------------

    def list_users(self, data_key: bytes):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, username_encrypted, created_at_encrypted,
               last_authenticated_encrypted
        FROM users ORDER BY id
        """)

        rows = cursor.fetchall()
        conn.close()

        result = []
        for user_id, uname_enc, created_enc, last_enc in rows:
            username  = self._decrypt(uname_enc, data_key)
            created   = self._decrypt(created_enc, data_key)
            last_auth = self._decrypt(last_enc, data_key) if last_enc else None
            result.append((user_id, username, created, last_auth))

        return result

    # ------------------------------------------------------------------
    # Liste des logs d'audit (déchiffrée)
    # ------------------------------------------------------------------

    def list_audit_logs(self, data_key: bytes):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, event_type_encrypted, user_id, success_encrypted,
               timestamp_encrypted, ip_encrypted, details_encrypted
        FROM audit_log ORDER BY id
        """)

        rows = cursor.fetchall()
        conn.close()

        result = []
        for log_id, evt_enc, uid, succ_enc, ts_enc, ip_enc, det_enc in rows:
            event_type = self._decrypt(evt_enc,  data_key)
            success    = bool(int(self._decrypt(succ_enc, data_key)))
            timestamp  = self._decrypt(ts_enc,   data_key)
            ip         = self._decrypt(ip_enc,   data_key) if ip_enc  else None
            details    = self._decrypt(det_enc,  data_key) if det_enc else None
            result.append((log_id, event_type, uid, success, timestamp, ip, details))

        return result
