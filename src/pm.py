import argparse
from getpass import getpass
import hashlib
import hmac
import pyperclip

from rich import print as printc

import utils.add
import utils.retrieve
import utils.generate
from utils.dbconfig import dbconfig

# PBKDF2 iteration count for the master-password verification hash. Must match
# the value used at setup time in config.py.
MASTER_HASH_ITERATIONS = 200000


def hashMasterPassword(mp, salt, iterations=MASTER_HASH_ITERATIONS):
    """Derive the salted, iterated (PBKDF2-HMAC-SHA256) verification hash of the
    master password. Returns a hex string. Kept in sync with config.py."""
    return hashlib.pbkdf2_hmac(
        "sha256", mp.encode(), salt, iterations
    ).hex()

parser = argparse.ArgumentParser(description='Description')

parser.add_argument('option', help='(a)dd / (e)xtract / (g)enerate')
parser.add_argument("-s", "--name", help="Site name")
parser.add_argument("-u", "--url", help="Site URL")
parser.add_argument("-e", "--email", help="Email")
parser.add_argument("-l", "--login", help="Username")
parser.add_argument("--length", help="Length of the password to generate",type=int)
parser.add_argument("-c", "--copy", action='store_true', help='Copy password to clipboard')


args = parser.parse_args()


def inputAndValidateMasterPassword():
	mp = getpass("MASTER PASSWORD: ")

	db = dbconfig()
	cursor = db.cursor()
	query = "SELECT * FROM pm.secret"
	cursor.execute(query)
	result = cursor.fetchall()[0]

	# result: (masterkey_hash, device_secret, salt)
	stored_hash = result[0]
	device_secret = result[1]
	salt = bytes.fromhex(result[2])

	# Recompute the salted, iterated PBKDF2 hash and compare in constant time
	# (hmac.compare_digest) to avoid timing side channels.
	computed_hash = hashMasterPassword(mp, salt)
	if not hmac.compare_digest(computed_hash, stored_hash):
		printc("[red][!] WRONG! [/red]")
		return None

	return [mp, device_secret]


def main():
	if args.option in ["add","a"]:
		if args.name == None or args.url == None or args.login == None:
			if args.name == None:
				printc("[red][!][/red] Site Name (-s) required ")
			if args.url == None:
				printc("[red][!][/red] Site URL (-u) required ")
			if args.login == None:
				printc("[red][!][/red] Site Login (-l) required ")
			return

		if args.email == None:
			args.email = ""

		res = inputAndValidateMasterPassword()
		if res is not None:
			utils.add.addEntry(res[0],res[1],args.name,args.url,args.email,args.login)


	if args.option in ["extract","e"]:
		# if args.name == None and args.url == None and args.email == None and args.login == None:
		# 	# retrieve all
		# 	printc("[red][!][/red] Please enter at least one search field (sitename/url/email/username)")
		# 	return
		res = inputAndValidateMasterPassword()

		search = {}
		if args.name is not None:
			search["sitename"] = args.name
		if args.url is not None:
			search["siteurl"] = args.url
		if args.email is not None:
			search["email"] = args.email
		if args.login is not None:
			search["username"] = args.login

		if res is not None:
			utils.retrieve.retrieveEntries(res[0],res[1],search,decryptPassword = args.copy)


	if args.option in ["generate","g"]:
		if args.length == None:
			printc("[red][+][/red] Specify length of the password to generate (--length)")
			return
		password = utils.generate.generatePassword(args.length)
		pyperclip.copy(password)
		printc("[green][+][/green] Password generated and copied to clipboard")



main()
