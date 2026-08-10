# Deploy

## GitHub

Create an empty repository, then from this folder:

```bash
git init
git add .
git commit -m "Initial Volapuk Accuracy-First MT"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

## Render

Connect the GitHub repository to Render as a Web Service.

The included `render.yaml` configures:

- Python 3.11.11
- `bash build.sh`
- Gunicorn
- `/healthz`
- Japanese -> English Argos model at build time

GitHub Pages alone cannot run the Flask/Python backend.

## Persistent full dictionary

For testing, the free service can run the application, but its local SQLite
database is temporary.

For a persistent imported full dictionary, attach a paid persistent disk at
`/var/data` and set:

```text
VOLAPUK_DB_PATH=/var/data/volapuk.sqlite3
VOLAPUK_UPLOAD_DIR=/var/data/uploads
```
