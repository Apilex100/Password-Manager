# This is a useful utility script that can be used to encrypt/decrypt with AES-256 using pycryptodome library
# You obviously need to install pycryptodome before you can use this: pip install pycryptodome
#
# NOTE: This module uses AES-256-GCM (an authenticated AEAD mode). GCM provides
# both confidentiality and integrity, so tampered ciphertext is rejected on
# decryption instead of being silently (and malleably) decrypted like plain
# AES-CBC. The stored blob layout is:  nonce(16) || tag(16) || ciphertext,
# base64-encoded. This format is NOT compatible with any data that was
# previously encrypted with the old AES-256-CBC scheme (IV || ciphertext); a
# fresh database is required after this change.

'''
Usage:
python aesutil.py <encrypt/decrypt> <message/cipher> <key> <keytype>

Encrypt a message:
python aesutil.py encrypt "Hello world" "9f735e0df9a1ddc702bf0a1a7b83033f9f7153a00c29de82cedadc9957289b05" "hex"
or
python aesutil.py encrypt "Hello world" "testpassword" "ascii"

Decrypt a message:
python aesutil.py decrypt "KnJxqDY0D5zWgycuvxZdTKm2520qI2DRCItSMyJtdxA=" "9f735e0df9a1ddc702bf0a1a7b83033f9f7153a00c29de82cedadc9957289b05" "hex"
or
python aesutil.py decrypt "KnJxqDY0D5zWgycuvxZdTKm2520qI2DRCItSMyJtdxA=" "testpassword" "ascii"
'''

import base64
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random
import sys
import string

# Size (in bytes) of the GCM nonce and authentication tag prepended to the
# ciphertext. 16 bytes is a fine, unambiguous nonce length for GCM.
NONCE_SIZE = 16
TAG_SIZE = 16


def normalizeKey(key, keyType):
	'''
	Turn the caller-supplied key into a 32-byte AES-256 key.

	- keyType == "hex":   key is a hex string -> raw bytes (expected 32 bytes).
	- keyType == "bytes": key is ALREADY a proper 32-byte key (e.g. the PBKDF2
	                      output from add.computeMasterKey). Use it directly.
	                      We deliberately do NOT hash it again: running SHA-256
	                      over an already-strong 32-byte PBKDF2 key adds no
	                      security and only obscures the key handling.
	- otherwise ("ascii"): key is a passphrase string -> SHA-256 to a 32-byte key.
	'''
	if keyType == "hex":
		return bytes(bytearray.fromhex(key))
	if keyType == "bytes":
		return key
	# ascii / passphrase: derive a proper-sized AES key from the string.
	return SHA256.new(key.encode()).digest()


def encrypt(key, source, encode=True, keyType = 'hex'):
	'''
	Parameters:
	key - The key with which you want to encrypt. You can give a key in hex representation (which will then be converted to bytes), an already-derived 32-byte key ("bytes"), or a passphrase string ("ascii").
	source - the message to encrypt
	encode - whether to encode the output in base64. Default is true
	keyType - specify the type of key passed

	Returns:
	Base64 encoded blob: nonce || tag || ciphertext
	'''

	source = source.encode()
	key = normalizeKey(key, keyType)

	nonce = Random.new().read(NONCE_SIZE)  # generate a fresh random nonce per message
	cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
	ciphertext, tag = cipher.encrypt_and_digest(source)
	data = nonce + tag + ciphertext  # store nonce + auth tag ahead of the ciphertext
	return base64.b64encode(data).decode() if encode else data


def decrypt(key, source, decode=True,keyType="hex"):
	'''
	Parameters:
	key - key to decrypt with (see encrypt() for the accepted keyType values).
	source - the cipher (or encrypted message) to decrypt
	decode - whether to first base64 decode the cipher before trying to decrypt with the key. Default is true
	keyType - specify the type of key passed

	Returns:
	The decrypted data. Raises ValueError if the authentication tag does not
	verify (i.e. the ciphertext was tampered with or the key is wrong).
	'''

	source = source.encode()
	if decode:
		source = base64.b64decode(source)

	key = normalizeKey(key, keyType)

	nonce = source[:NONCE_SIZE]  # extract the nonce from the beginning
	tag = source[NONCE_SIZE:NONCE_SIZE + TAG_SIZE]  # then the authentication tag
	ciphertext = source[NONCE_SIZE + TAG_SIZE:]
	cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
	# decrypt_and_verify raises ValueError on a bad tag (tampering / wrong key).
	return cipher.decrypt_and_verify(ciphertext, tag)



if __name__ == "__main__":
	op = sys.argv[1]
	if op=="encrypt" or op==1:
		msg = sys.argv[2]
		key = sys.argv[3]
		keyType = sys.argv[4]
		cipher = encrypt(key,msg,keyType=keyType)
		print(cipher)
	elif op=="decrypt" or op==2:
		cipher = sys.argv[2]
		key = sys.argv[3]
		keyType = sys.argv[4]
		msg = decrypt(key,cipher,keyType=keyType)
		print(msg)
