"""Generate a login entry for the MEE Reflex Trainer.

You control who can sign in. Run this to create the secrets block for one user,
then paste the output into .streamlit/secrets.toml (locally) or into the
Streamlit Cloud "Secrets" box (when deployed).

Usage:
    python scripts/make_user.py <username> "<Display Name>" "<password>"

Example:
    python scripts/make_user.py alice "Alice Smith" "her-temporary-password"

To revoke access, delete that user's block from secrets and save.
"""

import sys

try:
    import bcrypt
except ImportError:
    print("bcrypt is required. Install it with:  pip install bcrypt")
    sys.exit(1)


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    username = sys.argv[1].strip().lower()
    name = sys.argv[2].strip()
    password = sys.argv[3]

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    print()
    print("Paste this under [auth] in your secrets:")
    print("-" * 52)
    print(f'[auth.users.{username}]')
    print(f'name = "{name}"')
    print(f'password = "{hashed}"')
    print("-" * 52)
    print("(The password itself is NOT stored - only this hash.)")


if __name__ == "__main__":
    main()
