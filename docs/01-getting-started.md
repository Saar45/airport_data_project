# 1. Getting started

## The tool: `uv`

In R you install packages with `install.packages()`, and they go into one library shared by every project. Python works differently: each project usually gets its own isolated folder of libraries, called a **virtual environment**. Here that folder is `.venv/`.

**`uv`** is the tool that manages it for you. It:
- downloads the right Python version (3.12, set in `.python-version`). Your Mac's default Python is 3.15, which is too new for some data libraries;
- installs the libraries listed in `pyproject.toml` into `.venv/`;
- runs commands inside that environment when you write `uv run ...`.

You never need to "activate" anything. Just put `uv run` in front of your command.

The short setup guide is the `README.md` at the project root. This page explains the same steps in more detail.

## Run the app

From the project folder (`Airport_project/`):

```bash
uv sync                                    # 1. install / update libraries (only needed once, or after pyproject.toml changes)
uv run shiny run app/app.py --reload       # 2. start the app
```

Then open **http://127.0.0.1:8000** in your browser.

- `--reload` restarts the app automatically every time you save a `.py` file. That's useful while editing.
- To **stop** the app, go back to the terminal and press **Ctrl + C**.
- To use another port: `--port 8765`.

## Choose the data source

The app reads its settings from the `.env` file at the project root:

| Setting | Meaning |
|---|---|
| `DATA_SOURCE=local` | Use the `nycflights13` data bundled with the Python libraries. Works offline. |
| `DATA_SOURCE=supabase` | Use the team's Supabase database (see [08-supabase.md](08-supabase.md)). |
| `REFRESH_CACHE=true` | Re-read the data instead of using the saved cache. |

You can override a setting for one run without editing `.env`:

```bash
DATA_SOURCE=local uv run shiny run app/app.py --reload
```

## About the cache

Reading and preparing all the data, and training the model, happens **once**. The result is saved to `app/cache/local.pkl` or `app/cache/supabase.pkl`. The next start reads that file and takes under a second.

So, **if you change the data-preparation or model code, or the database content changes**, you must rebuild the cache:
- run once with `REFRESH_CACHE=true`, **or**
- simply delete the `app/cache/` folder.

Then put `REFRESH_CACHE` back to `false`. Otherwise the app reloads everything at every start, which is slow on the day of the presentation.

## Common errors

| Message | Cause / fix |
|---|---|
| `command not found: uv` | Install it: `brew install uv`. |
| `Variables d'environnement manquantes : ...` | `DATA_SOURCE=supabase` but `.env` is incomplete. Fill it in, or switch to `local`. |
| `Tables vides côté supabase : ...` | The database tables are empty, or Row Level Security hides them. See [08-supabase.md](08-supabase.md). |
| `password authentication failed for user "..."` | The wrong user/password pair. The user must match the password's role (e.g. `shiny_reader.<project-ref>`). |
| `failed to resolve host 'db.xxx.supabase.co'` | That's the direct host, which is IPv6 only. Use the **Session pooler** host. |
| `Address already in use` | The app is already running (maybe in another terminal). Stop it, or use `--port 8765`. |
| Charts show old numbers after a code change | The cache is stale. Delete `app/cache/`. |
