"""Configured FrameOps accounts and server-side sessions."""
import hashlib
import hmac
import json
import os
import secrets
import time
from http.cookies import SimpleCookie, CookieError

SESSION_SECONDS = 8 * 3600
ACCOUNTS = json.loads(os.getenv('FRAMEOPS_ACCOUNTS', '{}'))
DEMO = os.getenv('PUBLIC_DEMO', '0') == '1' and not ACCOUNTS


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                            n=16384, r=8, p=1).hex()
    return f'{salt}:{digest}'


def initialize_accounts(con, roles):
    for account in ACCOUNTS.values():
        if account['role'] not in roles or (account['role'] == 'Homeowner' and not account.get('job_id')):
            raise ValueError('Each account requires a valid role and homeowner accounts require a job_id')
    con.execute('''CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires_at INTEGER NOT NULL)''')


def session_key(cookie_header):
    try:
        cookie = SimpleCookie(cookie_header).get('frameops_session')
    except CookieError:
        return None
    return hashlib.sha256(cookie.value.encode()).hexdigest() if cookie else None


def identity(con, cookie_header):
    key = session_key(cookie_header)
    if not key:
        return None
    row = con.execute('SELECT username FROM sessions WHERE token_hash=? AND expires_at>?',
                      (key, int(time.time()))).fetchone()
    return ACCOUNTS.get(row['username']) if row else None


def sign_in(con, username, password):
    account = ACCOUNTS.get(username)
    expected = account['password_hash'] if account else '0' * 32 + ':' + '0' * 128
    if len(password) > 256 or not hmac.compare_digest(password_hash(password, expected.split(':')[0]), expected) or not account:
        return None
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    con.execute('DELETE FROM sessions WHERE expires_at<=?', (now,))
    con.execute('INSERT INTO sessions VALUES(?,?,?)',
                (hashlib.sha256(token.encode()).hexdigest(), username, now + SESSION_SECONDS))
    return token
