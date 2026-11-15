# Running and hosting MindOrbit

## Live app

https://mindorbit.streamlit.app/ (hosted on Streamlit Community Cloud from this code).

## Run locally

Requires Python 3.11+.

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens in English; use the **Language** selector at the top to switch to Portuguese. Every time the app starts, the demo begins at **mission day 1**.

Run the tests:

```bash
python -m pytest -q
```

## How the hosted demo works

- With the environment variable `MINDORBIT_PER_SESSION=1`, **each visitor gets a private database** that starts at day 1. Nobody changes another visitor's demo.
- Reloading the browser page starts a new session, so it goes back to day 1.
- The databases are temporary files; the ones older than 12 hours are deleted. Nothing needs to be saved.
- Without that variable (local use), the app uses a single local database and resets it when the server starts.

## Host it yourself on Streamlit Community Cloud

1. Put the project in a GitHub repository whose root contains `app.py` and `requirements.txt`.
2. Go to https://share.streamlit.io, sign in with GitHub and choose **Create app → Deploy a public app from GitHub**.
3. Repository: your repo · Branch: `main` · Main file path: `app.py`.
4. In **Advanced settings**: Python version **3.11**, and add this secret:
   ```toml
   MINDORBIT_PER_SESSION = "1"
   ```
5. Click **Deploy**. The first launch takes a few minutes while packages install.
6. If the repository is private, set the app's **Sharing** to public so anyone with the link can open it without logging in.

The app goes to sleep after some days without visits; the first visit afterwards wakes it up in a few seconds.

Any server that can run `pip install -r requirements.txt` and `streamlit run app.py` works too, with `MINDORBIT_PER_SESSION=1` set.
