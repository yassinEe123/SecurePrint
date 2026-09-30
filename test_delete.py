from modules.storage import StorageManager


def main():
    storage = StorageManager()

    username = "drama"

    print("[1] Utilisateurs avant suppression :")
    users_before = storage.list_users()
    for user in users_before:
        print(user)

    print("\n[2] Suppression de l'utilisateur...")
    deleted = storage.delete_user(username)
    print(f"Suppression réussie : {deleted}")

    print("\n[3] Utilisateurs après suppression :")
    users_after = storage.list_users()
    for user in users_after:
        print(user)

    print("\n[4] Audit logs :")
    logs = storage.list_audit_logs()
    for log in logs:
        print(log)


if __name__ == "__main__":
    main()
