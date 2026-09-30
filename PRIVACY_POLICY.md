# Privacy Policy – SecurePrint

## 1. Introduction

SecurePrint is a biometric authentication system designed to process fingerprint data securely. This system follows privacy-by-design and data minimization principles in accordance with GDPR and ISO/IEC 27018 guidelines.

## 2. Data Collected

The system processes the following data:

* Fingerprint images (temporary, not stored permanently)
* Biometric templates (feature vectors)
* User identifiers (username)
* Audit logs (authentication, enrollment, deletion events)

## 3. Data Processing

Fingerprint images are:

* Loaded from user-selected locations
* Processed in memory only
* Not stored permanently on disk

Biometric templates are:

* Generated from extracted minutiae
* Converted into numerical feature vectors
* Encrypted before storage

## 4. Data Storage

Only the following data is stored:

* Encrypted biometric templates (in SQLite database)
* Usernames
* Audit logs

No raw biometric images are stored.

## 5. Data Security

The system implements:

* Encryption of biometric templates using symmetric cryptography
* Key derivation from a user-provided password
* Separation between stored data and encryption secrets
* No plaintext storage of sensitive biometric data

## 6. Key Management

Encryption keys are not stored in plaintext.
Instead:

* A master password is required
* A cryptographic key is derived from this password
* Without the password, stored data cannot be decrypted

## 7. User Rights

Users have the right to:

* Access their data
* Delete their data (right to erasure)
* Refuse biometric enrollment

## 8. Data Retention

* Biometric templates are stored until deletion
* Audit logs are kept for traceability
* No raw images are retained

## 9. Secure Deletion

The system uses:

* SQLite secure deletion mechanisms
* Database cleanup (VACUUM)

to ensure that deleted data cannot be recovered.

## 10. Logging and Auditing

All operations are logged:

* Enrollment attempts
* Authentication attempts
* Deletion events

This ensures accountability and traceability.

## 11. Compliance

This system is designed to align with:

* GDPR (General Data Protection Regulation)
* ISO/IEC 27018 (Protection of Personally Identifiable Information)

## 12. Disclaimer

This system is a prototype for academic purposes. For production deployment, additional security measures are recommended.
