# Cloud Demo Deployment

This setup runs the FastAPI backend on Render, uses Supabase for PostgreSQL and
incident snapshots, and keeps Firebase Cloud Messaging enabled for closed-app
push notifications.

## Render service

Use these settings:

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

Required Render environment variables:

```text
DATABASE_URL=postgresql+asyncpg://...
DATABASE_URL_SYNC=postgresql://...
SECRET_KEY=change-this
DETECTOR_API_KEY=shared-secret-with-detector
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_STORAGE_BUCKET=incident-snapshots
FIREBASE_CREDENTIALS_JSON_BASE64=base64-encoded-service-account-json
```

## Supabase

Create a public Storage bucket named `incident-snapshots`.

The detector uploads each snapshot to `POST /snapshots/upload`. The backend
then uploads the file to Supabase Storage and returns a public URL. The incident
stores that Supabase URL, so Render does not need persistent file storage.

## Firebase

Create a Firebase service account JSON in Firebase Console, then base64-encode
the whole JSON file and set it as `FIREBASE_CREDENTIALS_JSON_BASE64`.

The backend still supports `FIREBASE_CREDENTIALS_PATH` for local development,
but cloud deployments should use the base64 env variable so credentials are not
committed to the repository.

## Client config

Detector:

```text
BACKEND_BASE_URL=https://your-render-app.onrender.com
DETECTOR_API_KEY=shared-secret-with-detector
```

Mobile:

```bash
flutter run --dart-define=FLAMESCOPE_API_BASE_URL=https://your-render-app.onrender.com
```
