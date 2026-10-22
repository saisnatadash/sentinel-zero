# Step-by-step: GitHub upload and live hosting

You need a GitHub account, and a Render account (or a Hugging Face account). Both can sign in with GitHub.

---

## Part A: Put the code on GitHub

### Option 1: Upload from the browser (no tools needed)

1. Go to <https://github.com/new>.
2. Repository name: `sentinel-zero`. Visibility: **Public**.
3. **Do not** tick "Add a README", ".gitignore" or "license". The zip already contains them.
4. Click **Create repository**.
5. On the empty repository page, click **uploading an existing file**.
6. Unzip `sentinel-zero.zip` on your computer. Open the `sentinel-zero` folder.
7. Select **everything inside** the folder (including `app`, `frontend`, `tests`, `docs`, `demo`, `data`,
   `Dockerfile`, `README.md`, `LICENSE`, `requirements.txt`, `pytest.ini`, `.gitignore`) and drag it into the browser.
   - GitHub accepts up to 100 files per upload. If it refuses, upload the folders in two batches.
   - Hidden files such as `.gitignore` may not show in Finder or Explorer. Turn on "show hidden files" first.
8. Commit message: `Initial prototype`. Click **Commit changes**.

### Option 2: Use the terminal (recommended)

Install Git from <https://git-scm.com> if you don't have it. Then, inside the unzipped `sentinel-zero` folder:

```bash
git init -b main
git add .
git commit -m "Initial prototype"
git remote add origin https://github.com/YOUR-USERNAME/sentinel-zero.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username. Git will ask you to sign in; use a personal access token
(GitHub → Settings → Developer settings → Personal access tokens) as the password.

**Check:** open `https://github.com/YOUR-USERNAME/sentinel-zero`. You should see `app`, `frontend`, `tests`,
`README.md` and `LICENSE`.

---

## Part B: Run it on your computer first

```bash
cd sentinel-zero
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q              # expect: 8 passed
uvicorn app.main:app --port 8000
```

Open <http://localhost:8000>. Click each scenario button. If this works, the hosted version will work too.

---

## Part C: Host it live on Render (recommended)

Render builds the `Dockerfile` in your repository and gives you a public `https://...onrender.com` address.

1. Sign up at <https://render.com> with your GitHub account.
2. Click **New +** → **Web Service**.
3. Choose **Build and deploy from a Git repository** → **Connect** your `sentinel-zero` repository.
   If it doesn't appear, click **Configure account** and allow access to that repository.
4. Fill in the form:
   - **Name:** `sentinel-zero`
   - **Region:** Singapore or the closest option
   - **Branch:** `main`
   - **Runtime:** Docker (Render detects the `Dockerfile` automatically)
   - **Root Directory:** `sentinel-zero-FIXED` (the `Dockerfile` is inside this folder, not at the repository root)
   - **Instance type:** Free
5. Click **Create Web Service**. The first build takes a few minutes. Watch the logs; you should see
   `Application startup complete` followed by `Uvicorn running`.
6. Open the link at the top of the page, for example `https://sentinel-zero.onrender.com`.
7. Test it: `https://sentinel-zero.onrender.com/api/health` should return `{"status":"ok", ...}`.

**Notes**

- Free services sleep after a period without traffic. The first visit after a sleep can take up to a minute.
  Open the link a few minutes before any judging or recording session.
- Every `git push` to `main` redeploys automatically.
- Render's free plan terms can change. Check the pricing page before relying on it.

---

## Part D: Host it live on Hugging Face Spaces (alternative)

1. Sign up at <https://huggingface.co> and create a **New Space**.
   - **Space name:** `sentinel-zero`
   - **SDK:** Docker → **Blank**
   - **Hardware:** CPU basic (free)
2. Hugging Face needs a small header at the top of the Space's README. Add this as the first lines of the
   README **in the Space** (you can keep it only on Hugging Face, and leave GitHub's README unchanged):

   ```yaml
   ---
   title: SENTINEL ZERO
   emoji: 🛡️
   colorFrom: blue
   colorTo: green
   sdk: docker
   app_port: 7860
   pinned: false
   ---
   ```

3. Push the code to the Space, using the URL Hugging Face shows you:

   ```bash
   git remote add space https://huggingface.co/spaces/YOUR-USERNAME/sentinel-zero
   git push space main
   ```

   Use a Hugging Face access token as the password (Settings → Access Tokens, with write permission).
4. Wait for the build to finish. The app appears at `https://YOUR-USERNAME-sentinel-zero.hf.space`.

---

## Part E: Use the links in your submission

- **Repository URL field:** `https://github.com/YOUR-USERNAME/sentinel-zero`
- **Demo video:** record it using `demo/README.md`, then upload the MP4 (720p or higher, under 80 MB).
- **Live prototype:** add the Render or Hugging Face link to the README and to slide 3 of your PDF.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python -m pytest` cannot find `app` | Run it from the folder that contains `app/` and `pytest.ini`. |
| Map is blank | Leaflet and map tiles load from the internet. Check your connection. |
| Render build fails on `scikit-learn` | Check the build log. The Dockerfile uses Python 3.12, which these packages support. |
| Live site shows "Application failed to respond" | Check the logs. Confirm the start command uses `${PORT}`. Render sets PORT automatically. |
| Hugging Face shows a blank page | Confirm `app_port: 7860` is in the Space's README header. |
