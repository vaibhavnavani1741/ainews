# Daily Industry News

Auto (+components) and Electrical Equipment/Electronics news, India vs Global. Free stack: RSS + Google News RSS,
Gemini free tier for classification, GitHub Actions + Pages for hosting.

## Run locally
```
pip install -r requirements.txt
echo GEMINI_API_KEY=your_key > .env     # optional; without it keyword classification is used
python collect.py && python process.py && python build.py
```
Open `docs/index.html`.

## Deploy
1. Repo Settings → Secrets → Actions → add `GEMINI_API_KEY`.
2. Settings → Pages → Deploy from branch `main`, folder `/docs`.
3. The workflow in `.github/workflows/daily.yml` runs daily at 07:00 IST (also runnable manually).

## Tune
- `sources.yaml`: add/remove feeds and Google News queries (dead feeds are skipped with a log line).
- `keywords.yaml`: prefilter keywords. `process.py`: `TOP_N`, `BATCH`, `GEMINI_MODEL`.
