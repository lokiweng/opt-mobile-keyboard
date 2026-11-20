# Keyform keyboard playground

From the repository root, run the following commands in a Python environment. The HTML app has been tested with Python 3.12.

```sh
python -m pip install -r requirements.txt
python web_app.py
```

Open the [local playground](http://127.0.0.1:8765). On the first prediction, the server downloads the OPT-125M base weights from Hugging Face. The LoRA variants use the adapter included in the repository. To choose a different local port, run `python web_app.py --port 9000`.

Type into the composer or load a sample prompt. Select a suggestion to complete a word, press Space to request the next word, and press Enter to send. In two-person chat the model uses the last two messages as context. Engine settings let you switch models, adjust personalization, and inspect the current typist’s learned vocabulary. Messages and vocabulary last until you reload or close the page.

For a quick design preview, open `web/index.html` directly in a browser. It uses a small example word list. The Python server provides model predictions, confidence scores, and spelling corrections.

To launch the original Streamlit interface, use `streamlit run app.py` from the repository root.

## Render deployment

Use a Python **Web Service** for the HTML interface and its prediction API. Set the branch to `codex/html-keyboard` and leave **Root Directory** empty.

| Setting | Value |
| --- | --- |
| Build Command | `python -m pip install torch --index-url https://download.pytorch.org/whl/cpu && python -m pip install -r requirements.txt` |
| Start Command | `python web_app.py` |
| Health Check Path | `/` |

After deploying, open the service's public URL at `/`. The server reads Render's assigned port and serves the keyboard there. Its startup log includes `Keyboard Lab is running at http://0.0.0.0:` followed by the port. The first prediction loads the model after the page opens.
