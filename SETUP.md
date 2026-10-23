# MemoMate setup (Milestone 1)

## 1. MongoDB Atlas (free cluster)

1. Go to https://www.mongodb.com/cloud/atlas/register and sign up (Google login works).
2. Create a cluster: choose **M0 (Free)**, any cloud provider, the region closest to you. Name it e.g. `memomate-cluster`. Click **Create Deployment**.
3. **Database user**: the pop-up asks you to create one. Pick a username and a password.
   Use letters and numbers only in the password (symbols like `@ : / ?` break the URI). Save it.
4. **Network access**: left menu → **Network Access** → **Add IP Address** → **Add Current IP Address**.
   (For a hackathon you can use **Allow Access from Anywhere** `0.0.0.0/0`, but it's less safe.)
5. **Get the URI**: left menu → **Database / Clusters** → **Connect** → **Drivers** → Driver: **Python**.
   Copy the string that looks like:
   `mongodb+srv://myuser:<db_password>@memomate-cluster.abcde.mongodb.net/?retryWrites=true&w=majority&appName=memomate-cluster`
6. Replace `<db_password>` with your real password (remove the `< >` too).

You don't need to create the `memomate` database by hand; the app creates it on the first save.

## 2. API keys

- **Anthropic**: https://console.anthropic.com → **API Keys** → **Create Key**. Starts with `sk-ant-`.
- **Voyage AI**: https://dash.voyageai.com → **API Keys** → **Create new secret key**. Starts with `pa-`.
  (Voyage needs a payment method added to lift its very low rate limits; the free token allowance still applies.)

## 3. Install and run (Windows PowerShell, in this folder)

```powershell
py -3.12 -m venv venv   # use 3.12: Python 3.15 alpha breaks the Anthropic SDK
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env        # paste your 3 keys, save, close
python brain.py     # should print: brain.py self-check passed
streamlit run app.py
```

If `Activate.ps1` is blocked, run this once, then try again:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Next time you only need: `.\venv\Scripts\Activate.ps1` then `streamlit run app.py`.
