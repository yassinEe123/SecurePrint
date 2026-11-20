# SecurePrint -- Secure Fingerprint Authentication System

## Overview

SecurePrint is a prototype biometric authentication system that
processes fingerprint images, extracts biometric features, generates a
secure template, encrypts it, and stores it in a local SQLite database.

The system demonstrates secure storage and authentication of biometric
data while respecting privacy principles such as encryption and the
right to erasure.

------------------------------------------------------------------------

## Features

-   Fingerprint image preprocessing
-   Minutiae extraction
-   Biometric template generation
-   Template encryption using Fernet
-   Secure storage in SQLite database
-   Authentication based on template comparison
-   Audit logging of system events
-   User deletion (GDPR right to erasure)

------------------------------------------------------------------------

## System Pipeline

Image\
↓\
Preprocessing\
↓\
Minutiae Extraction\
↓\
Template Generation\
↓\
Encryption\
↓\
SQLite Storage\
↓\
Authentication

------------------------------------------------------------------------

## Project Structure

secureprint/ │ ├── main.py ├── config.py ├── requirements.txt ├──
README.md │ ├── modules/ │ ├── **init**.py │ ├── preprocessor.py │ ├──
minutiae.py │ ├── template.py │ ├── encryption.py │ ├── storage.py │ └──
matcher.py │ ├── data/ │ ├── raw/ │ │ ├── fingerprint.BMP │ │ └──
fingerprint_other.BMP │ │ │ └── processed/ │ ├── database/ │ ├──
secureprint.db │ └── secret.key │ ├── tests/ │ └── test_delete.py │ └──
utils/

------------------------------------------------------------------------

## Installation

Create a virtual environment:

``` bash
python3 -m venv secureprint_env
source secureprint_env/bin/activate
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## Running the System

Run the main pipeline:

``` bash
python main.py
```

The system will:

1.  Process the fingerprint image
2.  Extract minutiae features
3.  Generate a biometric template
4.  Encrypt the template
5.  Store it in SQLite
6.  Perform authentication

------------------------------------------------------------------------

## Testing User Deletion

``` bash
python tests/test_delete.py
```

This test verifies that a user and their biometric template can be
removed from the database.

------------------------------------------------------------------------

## Security Considerations

-   Biometric templates are encrypted before storage
-   Encryption key stored separately
-   Audit logs track system activity
-   User data can be deleted to respect privacy regulations

------------------------------------------------------------------------

## Technologies Used

-   Python
-   OpenCV
-   NumPy
-   Scikit-image
-   Cryptography (Fernet)
-   SQLite

------------------------------------------------------------------------

## Author

Yassine Allani – Cybersecurity Engineering student, TEK-UP University (Tunis)
[LinkedIn](https://www.linkedin.com/in/yassine-allani-327b8a203)

------------------------------------------------------------------------

## License

Copyright © 2026 Yassine Allani. **All rights reserved.**

This code is public for viewing and evaluation only – no reuse, copy, modification or redistribution without written permission. See [LICENSE](LICENSE).
