"""Quick and dirty script to create env variable script used for development."""

import sys
import os
import socket

SECRETS = 'deploy/viewmaster-secrets.env'
PYTHONPATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'movie_library')


def main():
	"""Generate bash script that can be sourced for development."""
	if not os.path.exists(SECRETS):
		print(f"ERROR! Unable to find secrets at {SECRETS}\n\n")
		sys.exit(1)
	
	if len(sys.argv) != 2:
		print("ERROR! You must provide the externally visible IP of Postgres server\n\n")
		sys.exit(1)

	DB_HOST = sys.argv[1]
	with open('movie_library/dev-setup.bash', 'w') as out_file:
		general_lines = [
			"export DEBUG=1\n",
			"export ALLOWED_HOSTS=127.0.0.1\n",
			"export TEST_LOG_ROOT=\".\"\n",
			f"export HOSTNAME={socket.gethostname()}\n",
			f"export PYTHONPATH={PYTHONPATH}\n",  # do we need to quote?
		]
		out_file.writelines(general_lines)
		
		with open(SECRETS, 'r') as in_file:
			secrets = in_file.readlines()
		for secret in secrets:
			if "'" in secret:
			    # Must quote, as secret will include the single quotes
				key, _, value = secret.partition("=")
				value = value.replace("$", "\\$")  # Must escape for shell use
				secret = f'{key}="{value[:-1]}"{value[-1]}'
			if secret.startswith("DB_HOST="):
				secret = f"DB_HOST={DB_HOST}\n"
			out_file.write(f"export {secret}")


if __name__ == "__main__":
	main()
