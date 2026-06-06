# Deploying online with a private login

This app has a built-in login gate that **you** control — there is no public
sign-up. People can only get in with credentials you create for them.

## How the login works

- Credentials live in **`st.secrets`** (never in the code or the repo).
- If no users are configured, the app runs open (convenient for local use).
- As soon as you add one or more users, every visitor must sign in.
- Passwords are stored only as **bcrypt hashes** — never in plain text.

## 1. Create your login(s)

For each person who should have access (including yourself):

```bash
python make_user.py <username> "<Display Name>" "<password>"
```

It prints a small block like:

```toml
[auth.users.alice]
name = "Alice Smith"
password = "$2b$12$....bcrypt-hash...."
```

Collect one block per user.

## 2. Deploy to Streamlit Community Cloud (free)

1. Push this repo to GitHub (private is fine).
2. Go to https://share.streamlit.io → **Create app** → pick your repo, branch,
   and `app.py`.
3. **Advanced settings → Secrets** — paste your auth blocks under one `[auth]`
   section, for example:

   ```toml
   [auth.users.owner]
   name = "Owner"
   password = "$2b$12$....hash...."

   [auth.users.alice]
   name = "Alice Smith"
   password = "$2b$12$....hash...."
   ```

4. Deploy. The app will now show a sign-in page; only those users get in.

To **add a user** later: edit the app's Secrets and add another `[auth.users.x]`
block. To **revoke** someone: delete their block and save. (Both take effect on
the next load.)

## 3. The database (important)

Streamlit Community Cloud has an **ephemeral disk** — the local `mee_reflex.db`
is *not* in the repo and would start empty (and reset on every redeploy). Pick
one:

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
