"""One-time interactive script to authenticate with Monarch Money and save the session."""

import asyncio
import getpass
import os
import stat
import sys

from dotenv import load_dotenv
from monarchmoney import MonarchMoney, RequireMFAException

load_dotenv()


def _secure_session_path(session_file: str) -> None:
    """Pre-create the session file owner-only, before any secret is written to it.

    The saved session is a bearer token for the Monarch account: anyone who can read it can
    read your full financial history without your password or MFA. Creating the file 0600
    first (rather than chmod-ing afterwards) closes the window where it briefly exists as
    world-readable. Opening an existing file for writing preserves its mode, so the library's
    own save lands in an already-locked-down file.
    """
    parent = os.path.dirname(os.path.abspath(session_file))
    os.makedirs(parent, exist_ok=True)
    fd = os.open(session_file, os.O_WRONLY | os.O_CREAT, 0o600)
    os.close(fd)
    os.chmod(session_file, 0o600)


def _verify_session_perms(session_file: str) -> None:
    mode = stat.S_IMODE(os.stat(session_file).st_mode)
    if mode & 0o077:
        os.chmod(session_file, 0o600)
        print(f"Warning: {session_file} was group/world readable; tightened to 0600.")


async def main():
    if os.environ.get("DEMO_MODE", "").strip().lower() == "true":
        sys.exit("Refusing to log in: DEMO_MODE is enabled (this instance is demo-only).")

    session_file = os.environ.get("MONARCH_SESSION_FILE", ".monarch_session")

    mm = MonarchMoney()

    print("=== Monarch Money Login ===")
    email = input("Email: ")
    # getpass, not input: input() echoes the password to the terminal, where it lands in
    # screen-shares, recordings, and scrollback.
    password = getpass.getpass("Password: ")

    # The MFA call is nested inside the outer try, not placed beside it as a sibling handler.
    # An exception raised *inside* an except block is not caught by the following except
    # clauses, so a wrong or expired MFA code used to escape as a raw traceback.
    try:
        try:
            await mm.login(email, password)
        except RequireMFAException:
            print("\nMFA required. Check your authenticator app or email.")
            mfa_code = input("MFA code: ")
            await mm.multi_factor_authenticate(email, password, mfa_code)
    except Exception as e:
        print(f"Login failed: {e}", file=sys.stderr)
        sys.exit(1)

    _secure_session_path(session_file)
    mm.save_session(session_file)
    _verify_session_perms(session_file)
    print(f"\nSession saved to {session_file} (permissions 0600, owner-only)")

    # Verify by fetching accounts. The session is already saved and usable at this point, so a
    # failure here is a warning rather than a fatal error.
    try:
        accounts = await mm.get_accounts()
    except Exception as e:
        print(f"Warning: session saved, but the verification call failed: {e}", file=sys.stderr)
        return
    count = len(accounts.get("accounts", []))
    print(f"Verified: found {count} accounts")


if __name__ == "__main__":
    asyncio.run(main())
