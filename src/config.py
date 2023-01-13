from utils.dbconfig import dbconfig

import sys
import string
import random
import hashlib
from getpass import getpass

from rich import print as printc
from rich.console import Console

console = Console()

def generateDeviceSecret(length = 15):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k = length))


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
    query = "CREATE TABLE pm.secret (masterkey_hash TEXT NOT NULL, device_secret TEXT NOT NULL)"
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
    
    # Hash the MASTER PASSWORD
    hashed_mp = hashlib.sha256(mp.encode()).hexdigest()
    printc("[green][+][/green] Generated hash of MASTER PASSWORD")

    # Generate a Device Secret
    ds = generateDeviceSecret()
    printc("[green][+][/green] Device secret generated ")

    #Add them to db
    query = "INSERT INTO pm.secret (masterkey_hash,device_secret) values (%s, %s)"
    val = (hashed_mp,ds)
    cursor.execute(query,val)
    db.commit()

    printc("[green][+][/green] Added to the database")
    printc("[green][+] Configuration done! [/green] ")

    db.close()



config()