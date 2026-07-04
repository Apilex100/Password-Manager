from utils.dbconfig import dbconfig

import sys
import string
import random
import hashlib
import os
from getpass import getpass

from rich import print as printc
from rich.console import Console

console = Console()

# Number of PBKDF2 iterations used to derive the stored master-password
# verification hash. This is deliberately high to slow down offline brute-force
# attempts against a stolen database. (This is separate from, and in addition
# to, the AES key-derivation done in add.py.)
MASTER_HASH_ITERATIONS = 200000


def generateDeviceSecret(length = 15):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k = length))


def hashMasterPassword(mp, salt, iterations=MASTER_HASH_ITERATIONS):
    """Derive a salted, iterated verification hash of the master password.

    Uses PBKDF2-HMAC-SHA256 with a random per-install salt so the stored value
    resists precomputation/rainbow-table and fast offline brute-force attacks.
    Returns a hex string.
    """
    return hashlib.pbkdf2_hmac(
        "sha256", mp.encode(), salt, iterations
    ).hex()



def config():
    #  Create Database
    db = dbconfig()
    cursor = db.cursor()

    try:
        cursor.execute("CREATE DATABASE pm")
    except Exception as e:
        printc("[red][!] An error occured while trying to create db.")
        console.print_exception(show_locals=True)
        sys.exit(0)
    printc("[green][+][/green] Database 'pm' created")

    # Create Tables
    # `salt` stores the random per-install salt used for the PBKDF2 master-key
    # verification hash (stored as hex).
    query = "CREATE TABLE pm.secret (masterkey_hash TEXT NOT NULL, device_secret TEXT NOT NULL, salt TEXT NOT NULL)"
    res = cursor.execute(query)
    printc("[green][+][/green] Table 'secret' created")

    query = "CREATE TABLE pm.entries (sitename TEXT NOT NULL, siteurl TEXT NOT NULL, email TEXT, username TEXT, password TEXT NOT NULL)"
    res = cursor.execute(query)
    printc("[green][+][/green] Table 'entries' created")

    mp = ""
    while 1:
        mp = getpass("Enter the Master Password: ")
        if mp == getpass("Re-type: ") and mp != "":
            break
        printc("[yellow][-] Please try again. [/yellow]")
    
    # Hash the MASTER PASSWORD with a random per-install salt using
    # PBKDF2-HMAC-SHA256 (salted + iterated) so the stored verification hash
    # resists offline brute-force and rainbow-table attacks.
    salt = os.urandom(16)
    hashed_mp = hashMasterPassword(mp, salt)
    salt_hex = salt.hex()
    printc("[green][+][/green] Generated salted PBKDF2 hash of MASTER PASSWORD")

    # Generate a Device Secret
    ds = generateDeviceSecret()
    printc("[green][+][/green] Device secret generated ")

    #Add them to db
    query = "INSERT INTO pm.secret (masterkey_hash,device_secret,salt) values (%s, %s, %s)"
    val = (hashed_mp,ds,salt_hex)
    cursor.execute(query,val)
    db.commit()

    printc("[green][+][/green] Added to the database")
    printc("[green][+] Configuration done! [/green] ")

    db.close()



config()
