# Civic AI — From Complaints to Action

AI-assisted civic complaint management prototype for Mangaluru, Karnataka.

## Stack
- React + Vite + Tailwind CSS
- FastAPI (Python 3.12)
- Firebase Authentication, Firestore and Storage
- Gemini API (server-side only)
- Sentence Transformers duplicate similarity (optional model download)
- Leaflet + OpenStreetMap
- Recharts

## Important honesty notes
- The included 50-record dataset is synthetic and intended for demos only.
- Gemini analysis requires a valid `GEMINI_API_KEY`. Without it, the API uses a transparent rule-based fallback and labels the result accordingly.
- Duplicate detection uses sentence-transformers when enabled and falls back to token similarity if the model is unavailable.
- Hotspots are computed from report coordinates using a simple distance-based clustering approach; this is not a municipal GIS integration.
- Email/Google authentication is provided by Firebase client SDK. Backend routes verify Firebase ID tokens.
- Demo accounts are created only when you explicitly run the secure local setup script with credentials supplied through environment variables. No default passwords are shipped.
- Public tracking exposes only complaint ID, category, status, priority, public summary and status timeline. It never returns names, emails, phone numbers or image URLs.
- Map tiles require internet access. Browser geolocation requires user permission and a secure context (localhost is allowed).

## Prerequisites
- Node.js 20+
- Python 3.12 (64-bit recommended)
- A Firebase project with Firestore, Authentication (Email/Password and Google), and Storage enabled
- A Gemini API key (optional for fallback demo mode)

## 1. Firebase setup
1. Open Firebase Console and select your existing `civic-complaints-ai` project.
2. Enable Authentication providers: Email/Password and Google.
3. Create Firestore database.
4. Enable Firebase Storage.
5. In Project settings > General > Your apps, copy the Web app config into `frontend/.env`.
6. In Project settings > Service accounts, generate a private key and save it **outside source control** as `backend/service-account.json`.
7. In Authentication > Settings > Authorized domains, add your deployed frontend domain when deploying.

Never commit `service-account.json`, `.env`, or real API keys.

## 2. Configure frontend
```powershell
cd frontend
Copy-Item .env.example .env
npm install
```
Edit `.env` with Firebase web config and backend URL:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=civic-complaints-ai
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
```

## 3. Configure backend (Windows PowerShell)
```powershell
cd ..\backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```
Edit `backend/.env`:
```env
FIREBASE_PROJECT_ID=civic-complaints-ai
FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
FIREBASE_SERVICE_ACCOUNT_PATH=service-account.json
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
FRONTEND_ORIGINS=http://localhost:5173
ALLOW_DEMO_FALLBACK=true
```
Place your downloaded Firebase service account JSON at `backend/service-account.json`.

## 4. Optional demo accounts
Set these variables in `backend/.env`:
```env
DEMO_CITIZEN_EMAIL=demo.citizen@example.com
DEMO_CITIZEN_PASSWORD=ChooseAStrongPassword!
DEMO_ADMIN_EMAIL=demo.admin@example.com
DEMO_ADMIN_PASSWORD=ChooseAnotherStrongPassword!
DEMO_OFFICER_EMAIL=demo.officer@example.com
DEMO_OFFICER_PASSWORD=ChooseAnotherStrongPassword!
```
Then run:
```powershell
.\.venv\Scripts\python.exe scripts\setup_demo_accounts.py
```
The script creates Firebase Auth users and role documents. It does not contain hardcoded passwords.

## 5. Run locally
Terminal 1:
```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```
Terminal 2:
```powershell
cd frontend
npm run dev
```
Open http://localhost:5173. API docs: http://127.0.0.1:8000/docs

## 6. Load synthetic dataset
With backend running and an admin Firebase token available, use the Admin > Seed demo data button in the UI. Alternatively, the JSON is in `dataset/complaints.json`; never load it into a real production database without reviewing it.

## Deployment
### Backend on Render
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set environment variables from `backend/.env.example` in Render.
- Store service-account JSON as a secret file and set `FIREBASE_SERVICE_ACCOUNT_PATH` to its mounted path.
- Set `FRONTEND_ORIGINS` to your Vercel domain.

### Frontend on Vercel
- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Add all `VITE_FIREBASE_*` variables and `VITE_API_BASE_URL` pointing to Render.
- Add Vercel domain to Firebase Authentication authorized domains.

## Security checklist before public deployment
- Replace broad development rules with the rules in `firestore.rules` and `storage.rules`, then test them in Firebase Emulator Suite.
- Assign roles only through trusted admin tooling. Never trust role claims supplied by the browser.
- Restrict CORS to your real frontend domain.
- Add Firebase App Check, rate limiting, request size limits, moderation and abuse reporting.
- Review privacy notice, retention policy and applicable local data-protection requirements.
- Configure billing alerts and API quotas.
- Do not use synthetic records as real civic reports.

## Project layout
```text
civic-ai/
├── frontend/
├── backend/
├── dataset/complaints.json
├── firestore.rules
├── storage.rules
└── README.md
```
