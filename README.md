# Lab Requisition Reminder + Auto-Fill

FastAPI backend that:
- stores patient profile data,
- sends scheduled lab requisition reminder emails every 6/12 months,
- generates pre-filled Ontario requisition PDFs for user review and manual submission.

## Setup

1. Create venv and install dependencies:
   - `python -m venv .venv`
   - `.venv\Scripts\Activate.ps1`
   - `pip install -r requirements.txt`
2. Configure `.env` (example):

```env
DATABASE_URL=sqlite:///./app.db
TOKEN_SECRET=replace-with-strong-secret
TOKEN_SALT=review-link
TOKEN_EXPIRY_SECONDS=604800
BASE_REVIEW_URL=http://localhost:8000/api/review
REQUISITION_PDF_PATH=C:\Users\Sambo\OneDrive\Desktop\Ontario Laboratory Requisition Form.pdf
GENERATED_PDF_DIR=generated_forms

# Optional SMTP (leave blank for dry-run console email)
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=true
FROM_EMAIL=noreply@example.com
```

## Run

`uvicorn app.main:app --reload`

## Core Endpoints

- `POST /api/users` create patient profile and cadence.
- `PATCH /api/users/{user_id}` update profile fields.
- `POST /api/jobs/run-reminders` execute reminder scan immediately.
- `GET /api/review/{token}` open secure review link data.
- `POST /api/users/{user_id}/forms` prefill and generate PDF.
- `POST /api/users/{user_id}/mark-complete` set completion date after manual submit.
- `GET /api/pdf/inspect` inspect whether template is fillable and list field names.

## Notes

- If the source PDF is non-fillable, the app writes text via coordinate overlay.
- Overlay coordinates may need one-time tuning against your exact form revision.

# healthcare-hackathon

Basic speech-to-text starter for a healthcare mail assistant demo.

## Setup

1. Create and activate a virtual environment:
   - Windows PowerShell:
     - `python -m venv .venv`
     - `.venv\Scripts\Activate.ps1`
2. Install dependencies:
   - `pip install -r requirements.txt`

## Run

### Microphone mode
`python mail_assistant_stt.py`

### WAV file mode
`python mail_assistant_stt.py --audio-file sample.wav`

## What it does

- Converts speech to text using Python `SpeechRecognition`.
- Applies simple rules to infer an action:
  - `draft_email`
  - `send_email`
  - `schedule_follow_up`
- Detects high-priority language (`urgent`, `asap`, `critical`).
- Extracts a recipient if an email address is spoken.

## Example spoken command

"Send email to care.team@hospital.org with urgent discharge update for patient room 214."

The script prints:
- The raw transcript
- A JSON object with inferred action, priority, recipient, and timestamp
