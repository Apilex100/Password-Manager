# Python Password Manager

> A local, command-line password manager that encrypts credentials with **AES-256-GCM** authenticated encryption, deriving the key on demand from a master password via **PBKDF2** and storing the ciphertext in a MariaDB/MySQL database.

## Overview

This project is a self-hosted password manager built in Python. Credentials are encrypted with **AES-256-GCM** — an authenticated (AEAD) cipher that provides both **confidentiality and integrity/tamper-detection** — before they ever touch storage, and the encryption key is never stored on disk. It is re-derived on every operation from a user-supplied **master password** combined with a randomly generated, per-install **device secret** using **PBKDF2**. The tool exposes a small, argparse-driven CLI for adding entries, searching/retrieving them, and generating random passwords, with an optional clipboard copy so plaintext secrets are never printed to the terminal.

The master password itself is never persisted. Only a **salted, iterated PBKDF2-HMAC-SHA256 hash** of it is stored (with a random per-install salt), and it is used solely to authenticate the user before an operation runs; verification is done with a **constant-time comparison** to avoid timing side channels. The actual encryption key material lives only in memory for the duration of a command.

## Features

- **AES-256-GCM authenticated encryption of every stored password** — an AEAD mode that provides confidentiality *and* integrity, so tampered ciphertext is rejected on decryption instead of silently mis-decrypting. A fresh random nonce is used per entry; the blob is `nonce || tag || ciphertext`, base64-encoded — `src/utils/aesutils.py`.
- **PBKDF2 key derivation** from the master password + device secret (256-bit key, HMAC-SHA512, 1,000,000 iterations) — `computeMasterKey()` in `src/utils/add.py`.
- **Per-install device secret** as a cryptographic salt, generated once at configuration time using the CSPRNG `secrets` module — `generateDeviceSecret()` in `src/config.py`.
- **Master-password authentication** via a **salted, iterated PBKDF2-HMAC-SHA256 hash** (200,000 iterations, random per-install salt), verified in **constant time** with `hmac.compare_digest` before any read/write — `inputAndValidateMasterPassword()` in `src/pm.py`.
- **Add credentials** (site name, URL, email, username, password) — `addEntry()` in `src/utils/add.py`.
- **Search & retrieve** entries by any combination of site name, URL, email, or username using **parameterized queries with a column whitelist** (SQL-injection-safe); results render in a formatted table with passwords hidden — `retrieveEntries()` in `src/utils/retrieve.py`.
- **Environment-variable-based database configuration** — connection credentials are read from `os.environ` (no hardcoded secrets); a missing `DB_PASSWORD` fails fast — `dbconfig()` in `src/utils/dbconfig.py`.
- **Clipboard copy of decrypted passwords** so plaintext never appears on screen — via `pyperclip`.
- **Cryptographically secure random password generator** of configurable length using letters, digits, and punctuation, backed by the `secrets` module — `generatePassword()` in `src/utils/generate.py`.
- **Rich terminal output** with colored status messages and tables via the `rich` library.

## Tech Stack

- **Language:** Python 3
- **Cryptography:** [`pycryptodome`](https://pypi.org/project/pycryptodome/) — `Crypto.Protocol.KDF.PBKDF2`, `Crypto.Cipher.AES` (GCM/AEAD mode), `Crypto.Hash.SHA256`/`SHA512`
- **Database:** MariaDB / MySQL via [`mysql-connector-python`](https://pypi.org/project/mysql-connector-python/)
- **CLI:** Python standard library `argparse`
- **Terminal UI:** [`rich`](https://pypi.org/project/rich/) (colored output + tables)
- **Clipboard:** [`pyperclip`](https://pypi.org/project/pyperclip/)
- **Standard library:** `hashlib` (PBKDF2), `hmac` (constant-time compare), `secrets` (CSPRNG for the device secret + generated passwords), `os` (env vars + `urandom` salt), `getpass`, `string`, `base64`

## How It Works

### 1. One-time configuration (`src/config.py`)

Running the config step creates the `pm` database and two tables:

- `secret(masterkey_hash TEXT, device_secret TEXT, salt TEXT)`
- `entries(sitename, siteurl, email, username, password)`

You are prompted to choose a **master password**. The program then:

1. Generates a random 16-byte salt (`os.urandom`) and stores `pbkdf2_hmac('sha256', master_password, salt, 200000)` (hex digest) in `secret.masterkey_hash`, with the salt in `secret.salt` — used only to verify you later, never for encryption.
2. Generates a random 15-character alphanumeric **device secret** (via the CSPRNG `secrets` module) and stores it in `secret.device_secret`. This value acts as the PBKDF2 **salt** for the AES key derivation.

### 2. Authentication (`inputAndValidateMasterPassword()` in `src/pm.py`)

On every `add` or `extract` command you are prompted for the master password. The stored salt is loaded, the master password is re-hashed with **PBKDF2-HMAC-SHA256 (200,000 iterations)**, and the result is compared against the stored hash using **`hmac.compare_digest` (constant-time comparison)** to defeat timing attacks. On mismatch the operation aborts. On success, the plaintext master password and the stored device secret are handed to the crypto layer.

### 3. Key derivation (`computeMasterKey()` in `src/utils/add.py`)

```python
key = PBKDF2(master_password, device_secret, 32, count=1000000, hmac_hash_module=SHA512)
```

The 256-bit key is derived fresh each time from the master password (input) and the device secret (salt). Nothing about this key is stored.

### 4. Encryption / decryption (`src/utils/aesutils.py`)

- **Encrypt:** a fresh random nonce is generated per entry, the plaintext is encrypted with **AES-256-GCM** via `encrypt_and_digest()`, and the layout `nonce (16 bytes) || authentication tag (16 bytes) || ciphertext` is base64-encoded and stored in the `password` column.
- **Decrypt:** the base64 blob is decoded, the nonce and tag are split off the front, and `decrypt_and_verify()` decrypts the remainder. If the authentication tag does not verify — because the ciphertext was tampered with or the key is wrong — it raises `ValueError` rather than returning garbage plaintext.

> Note: the crypto layer is called with `keyType="bytes"`, so the already-strong 32-byte PBKDF2 key is used directly as the AES-256 key. It is **not** hashed again — running SHA-256 over an existing 256-bit PBKDF2 output would add no security and only obscure key handling.

> ⚠️ **Not backward-compatible:** the AES-256-GCM blob format (`nonce || tag || ciphertext`) is incompatible with any data previously encrypted under the old AES-256-CBC scheme (`IV || ciphertext`). A **fresh database is required** after upgrading to GCM — old CBC-encrypted rows cannot be decrypted by this code.

### 5. Storage format

Encrypted passwords are stored as base64 strings in the MariaDB `pm.entries` table alongside the (plaintext) site metadata. Decryption only happens on demand, and the decrypted password is written to the clipboard rather than printed. All lookups issued against the database use **parameterized queries** (driver `%s` placeholders with a params tuple), so user-supplied search values can never alter the query structure — the search is **safe against SQL injection**.

## Getting Started

### Prerequisites

- Python 3
- MariaDB or MySQL server running locally

### Configure the database connection (environment variables)

Database credentials are **not** hardcoded. `src/utils/dbconfig.py` reads them from environment variables:

| Variable      | Required | Default     | Description                                             |
| ------------- | -------- | ----------- | ------------------------------------------------------- |
| `DB_HOST`     | no       | `localhost` | Database server host                                    |
| `DB_PORT`     | no       | `3306`      | Database server port                                    |
| `DB_USER`     | no       | `root`      | Database user                                           |
| `DB_NAME`     | no       | *(unset)*   | Optional default schema (tables are fully qualified)    |
| `DB_PASSWORD` | **yes**  | *(none)*    | Database password — the app refuses to start if unset   |

Copy the template and set your own values (never commit real secrets):

```bash
cp .env.example .env      # then edit .env
# export them into your shell before running, e.g.:
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD='your-db-password'
```

See [`.env.example`](.env.example) for the full list. There is intentionally **no default password**: if `DB_PASSWORD` is unset the program exits with a clear message rather than connecting insecurely.

### Install dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` pins: `mysql-connector-python`, `pycryptodome`, `pyperclip`, `rich`, `commonmark`, `Pygments`, `protobuf`.

### Configure (run once)

From the `src/` directory, create the database, tables, and master password:

```bash
cd src
python config.py
```

You will be asked to choose and confirm a master password. A device secret is generated automatically.

> **Upgrading from an older CBC build?** The AES-256-GCM ciphertext format is not backward-compatible with the previous AES-256-CBC format, so there is no in-place migration. Start from a fresh `pm` database and re-add your entries.

### Run

```bash
python pm.py -h
```

```
usage: pm.py [-h] [-s NAME] [-u URL] [-e EMAIL] [-l LOGIN] [--length LENGTH] [-c] option

positional arguments:
  option                (a)dd / (e)xtract / (g)enerate

optional arguments:
  -h, --help            show this help message and exit
  -s NAME, --name NAME  Site name
  -u URL, --url URL     Site URL
  -e EMAIL, --email EMAIL
                        Email
  -l LOGIN, --login LOGIN
                        Username
  --length LENGTH       Length of the password to generate
  -c, --copy            Copy password to clipboard
```

## Usage / Examples

### Add an entry

```bash
python pm.py add -s mysite -u mysite.com -e hello@email.com -l myusername
```

You are prompted for the master password and then the password to store.

### Retrieve entries

```bash
# Retrieve all entries (passwords hidden in the table)
python pm.py extract

# Retrieve entries whose site name is "mysite"
python pm.py e -s mysite

# Retrieve the entry for a specific site + username
python pm.py e -s mysite -l myusername

# Copy the matching password to the clipboard (single match only)
python pm.py e -s mysite -l myusername --copy
```

### Generate a password

```bash
# Generate a 15-character random password and copy it to the clipboard
python pm.py g --length 15
```

## Project Structure

```
Password-Manager-master/
├── README.md
├── requirements.txt
├── .env.example              # Documents the DB_* environment variables (no secrets)
└── src/
    ├── config.py              # One-time setup: creates DB/tables, salted PBKDF2 master hash + device secret
    ├── pm.py                  # CLI entry point (argparse), constant-time master-password auth, command routing
    └── utils/
        ├── add.py             # PBKDF2 key derivation + encrypt & (parameterized) insert an entry
        ├── retrieve.py        # Parameterized/whitelisted search, render table, decrypt-to-clipboard
        ├── generate.py        # CSPRNG (`secrets`) random password generator
        ├── aesutils.py        # AES-256-GCM (AEAD) encrypt/decrypt helpers (pycryptodome)
        └── dbconfig.py        # MariaDB/MySQL connection factory (env-var credentials)
```

## Security Notes

This is a learning-oriented, local-first tool. Implemented protections and honest caveats:

- **Encryption is real and authenticated:** stored passwords are protected with **AES-256-GCM** (AEAD), which provides both confidentiality and integrity — tampered ciphertext fails verification instead of decrypting to attacker-influenced plaintext. The key is derived on demand via PBKDF2 (1,000,000 iterations, HMAC-SHA512) rather than being stored, and the master password is never persisted.
- **Master-password verification is salted and iterated.** The stored value is `PBKDF2-HMAC-SHA256` over the master password with a random per-install 16-byte salt (200,000 iterations), compared in **constant time** via `hmac.compare_digest`. This resists rainbow-table and fast offline brute-force attacks and defeats timing side channels. (This gates access only; it is separate from the AES key derivation.)
- **Randomness comes from a CSPRNG.** The per-install device secret and generated passwords use Python's `secrets` module, not the non-cryptographic `random` (Mersenne-Twister) generator.
- **Queries are parameterized.** All database lookups use the driver's `%s` placeholders with a params tuple, and column names are drawn from a fixed internal whitelist, so search inputs cannot be used for **SQL injection**.
- **No hardcoded credentials.** Database connection settings are read from environment variables (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_NAME`, `DB_PASSWORD`); a missing `DB_PASSWORD` causes a fast, explicit failure instead of an insecure default. See `.env.example`.
- **The device secret (AES-key PBKDF2 salt) is stored in the same database** as the encrypted data. If an attacker obtains the database, security rests entirely on the strength of the master password.
- **The GCM ciphertext format is not backward-compatible** with the previous AES-256-CBC scheme; a fresh database is required after the upgrade (no in-place migration path).
- **The threat model is local storage at rest**, not a hardened multi-user or networked deployment. Treat this as a personal/educational project, not audited security software.

## Author

**Aviral Kumar Singh** — [https://github.com/Apilex100](https://github.com/Apilex100)
