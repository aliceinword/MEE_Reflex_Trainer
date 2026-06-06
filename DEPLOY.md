# Deploying online with a private login

This app has a built-in login gate that **you** control — there is no public
sign-up. People can only get in with credentials you create for them.

## How the login works

- Your **admin** account is seeded from **`st.secrets`** (never in the code/repo).
- Once an admin exists, every visitor must sign in (by email or username).
- The admin signs in and creates/removes everyone else from the in-app
  **"Manage Users"** page — no file editing per user.
- Passwords are stored only as **bcrypt hashes** — never in plain text.
- If the `[auth]` section is absent, the app runs open (handy for local use).

## 1. Create your admin block

```bash
python make_user.py <username> "<Display Name>" "<password>"
```

Take the printed hash and put it in an `[auth.admin]` block:

```toml
[auth.admin]
username = "olesialek"
email = "olesialek@gmail.com"
name = "Olesia"
password = "$2b$12$....bcrypt-hash...."
```

## 2. Deploy to Streamlit Community Cloud (free)

1. Push this repo to GitHub (private is fine).
2. Go to https://share.streamlit.io → **Create app** → pick your repo, branch,
   and `app.py`.
3. **Advanced settings → Secrets** — paste your `[auth.admin]` block.
4. Deploy. The app shows a sign-in page; sign in with your admin email/username.
5. Open **Manage Users** (admin-only, in the sidebar) to add everyone else —
   set each person a username, email, and a temporary password, then share it.
   Remove a user there to revoke access. Change your own password there too.

## 3. The database (important)

Streamlit Community Cloud has an **ephemeral disk** — the local `mee_reflex.db`
is *not* in the repo and would start empty (and reset on every redeploy). This
also affects accounts: your **admin** always returns (it's re-seeded from
secrets), but users you add in-app live in the database, so for durable
multi-user access use a hosted database. Pick one:

- **Ship a seed database:** commit a `mee_reflex.db` into your **private** deploy
  repo so the app launches with your content already loaded. (Keep this repo
  private — see the copyright note below.)
- **Use a hosted database:** point `database.py` at a managed Postgres
  (e.g. Supabase/Neon) for content that persists and is shared across users.
  More setup, but proper multi-user persistence.
- **Let users build their own:** deploy code only; each user imports their own
  materials. (Per-user data still needs a hosted DB to persist.)

## Content note

All of the content here is the author's own work: an original rules outline,
Plug & Play templates, MBE trap cards, and question write-ups that have been
rewritten/paraphrased in the author's own words (copyright protects specific
expression, not facts or legal doctrines). It is intended to be shared with
invited users. If you later add third-party material verbatim, review its terms
before including it in a shared deployment.

## Running locally with the login enabled (optional)

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, paste your
user blocks, and run `streamlit run app.py`. Without that file, local runs stay
open (no login).
