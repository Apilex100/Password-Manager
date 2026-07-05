import secrets
import string

def generatePassword(length):
	# Use the `secrets` module (CSPRNG) instead of `random` (Mersenne-Twister)
	# because generated passwords are security-sensitive values.
	alphabet = string.ascii_letters + string.digits + string.punctuation
	return ''.join([secrets.choice(alphabet) for n in range(length)])
