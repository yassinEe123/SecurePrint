from modules.preprocessor import FingerprintProcessor
from modules.minutiae import MinutiaeExtractor
from modules.template import TemplateGenerator
from modules.encryption import EncryptionManager
from modules.storage import StorageManager
from modules.matcher import Authenticator
import numpy as np
import os


def main():
    print("=" * 55)
    print("       SYSTÈME DE RECONNAISSANCE D'EMPREINTES")
    print("=" * 55)

    print("\n[1] Initialisation des modules...")
    processor     = FingerprintProcessor()
    extractor     = MinutiaeExtractor(border_margin=20)
    generator     = TemplateGenerator()
    encryptor     = EncryptionManager()
    storage       = StorageManager()

    # CORRECTION : seuils adaptés au vecteur normalisé
    # threshold           = 0.35  → distance euclidienne max pour RECONNU
    # duplicate_threshold = 0.08  → distance max pour détecter duplication
    authenticator = Authenticator(threshold=0.70, duplicate_threshold=0.55)  # cosine distance

    storage.create_tables()

    # ------------------------------------------------------------------
    print("\n[2] Saisie du mot de passe maître...")
    master_password = input("  Mot de passe maître : ").strip()
    if not master_password:
        print("  ❌ Mot de passe vide interdit.")
        return

    try:
        data_key = encryptor.ensure_data_key(master_password)
    except ValueError as e:
        print(f"  ❌ {e}")
        return

    # ------------------------------------------------------------------
    print("\n[3] Saisie des paramètres...")
    input_path = input("  Chemin de l'image d'empreinte : ").strip()
    if not input_path:
        print("  ❌ Chemin image vide.")
        return
    if not os.path.exists(input_path):
        print(f"  ❌ Fichier introuvable : {input_path}")
        return

    username = input("  Nom d'utilisateur : ").strip()
    if not username:
        print("  ❌ Username vide.")
        return

    # ------------------------------------------------------------------
    print("\n[4–8] Prétraitement de l'image...")
    image     = processor.load_image(input_path)
    enhanced  = processor.normalize_contrast(image)
    segmented = processor.segment_fingerprint(enhanced)
    binary    = processor.binarize(segmented)
    skeleton  = processor.skeletonize(binary)
    ridge_orientation = processor.estimate_ridge_orientation(segmented)
    print("  ✅ Squelette généré.")
    print(f"  → Orientation des crêtes : {ridge_orientation:.1f}°")

    # ------------------------------------------------------------------
    print("\n[9] Extraction des minutiae...")
    minutiae = extractor.extract_features(skeleton)
    minutiae = extractor.filter_false_minutiae(minutiae)
    print(f"  → {len(minutiae)} minutiae détectées.")

    if len(minutiae) < 10:
        print("  ⚠ Trop peu de minutiae. Vérifiez la qualité de l'image.")
        return

    # ------------------------------------------------------------------
    print("\n[10] Génération du template biométrique (orientation field)...")
    query_template = generator.generate_template(minutiae, image=segmented)
    print(f"  → Template : {query_template.shape[0]} dimensions")

    # ------------------------------------------------------------------
    print("\n[11] Vérification anti-duplication...")
    all_templates = storage.get_all_templates(data_key)
    candidates = {}
    try:
        for existing_username, encrypted_blob in all_templates:
            stored_template = encryptor.decrypt_template(encrypted_blob, data_key)
            candidates[existing_username] = stored_template
    except Exception:
        print("  ❌ Impossible de déchiffrer les templates existants.")
        print("     Vérifiez votre mot de passe maître.")
        return

    is_duplicate, matched_user, dup_distance = authenticator.is_duplicate_fingerprint(
        query_template, candidates
    )

    if is_duplicate:
        print(f"\n  ❌ Enrôlement refusé.")
        print(f"     Cette empreinte appartient déjà à : {matched_user}")
        print(f"     Distance biométrique : {dup_distance:.6f}")
        storage.log_event("enrollment", data_key, user_id=None, success=False,
                          details=f"Doublon détecté, distance={dup_distance:.6f}")
        print("\nPipeline terminé.")
        return

    # ------------------------------------------------------------------
    print("\n[12] Chiffrement et enrôlement...")
    encrypted_template = encryptor.encrypt_template(query_template, data_key)

    # Vérification intégrité chiffrement
    decrypted_check = encryptor.decrypt_template(encrypted_template, data_key)
    if not np.allclose(query_template, decrypted_check):
        print("  ❌ Erreur d'intégrité du chiffrement.")
        return
    print("  ✅ Intégrité chiffrement vérifiée.")

    try:
        user_id = storage.enroll_user(username, encrypted_template, data_key)
        print(f"  ✅ Utilisateur enrôlé. user_id = {user_id}")
    except ValueError as e:
        print(f"  ❌ {e}")
        return

    # ------------------------------------------------------------------
    print("\n[13] Authentification immédiate (vérification enrôlement)...")
    stored_blob = storage.get_template_by_username(username)

    if stored_blob is None:
        print("  ❌ Aucun template stocké pour cet utilisateur.")
        return

    try:
        stored_template = encryptor.decrypt_template(stored_blob, data_key)
    except Exception:
        print("  ❌ Échec du déchiffrement du template stocké.")
        return

    success, distance = authenticator.authenticate(query_template, stored_template)

    print(f"  Distance calculée : {distance:.6f}")
    print(f"  Seuil             : {authenticator.threshold}")

    user_info = storage.get_user_by_username(username)
    uid = user_info[0] if user_info else None

    if success:
        print("  ✅ Authentification réussie.")
        if uid:
            storage.update_last_authenticated(uid, data_key)
        storage.log_event("authentication", data_key, user_id=uid, success=True,
                          details="Authentification réussie")
    else:
        print("  ❌ Authentification échouée.")
        storage.log_event("authentication", data_key, user_id=uid, success=False,
                          details="Authentification échouée")

    # ------------------------------------------------------------------
    print("\n[14] Liste des utilisateurs enrôlés...")
    users = storage.list_users(data_key)
    print(f"  {'ID':<5} {'Nom':<20} {'Créé le':<22} {'Dernière auth'}")
    print(f"  {'-'*5} {'-'*20} {'-'*22} {'-'*20}")
    for u in users:
        uid_u, uname, created, last_auth = u
        last_auth = last_auth or "jamais"
        print(f"  {uid_u:<5} {uname:<20} {str(created):<22} {last_auth}")

    print("\n" + "=" * 55)
    print("  Pipeline terminé avec succès.")
    print(f"  Base        : database/secureprint.db")
    print(f"  Clé         : database/secret.key.enc")
    print(f"  Salt        : database/secret.salt")
    print("=" * 55)


if __name__ == "__main__":
    main()
