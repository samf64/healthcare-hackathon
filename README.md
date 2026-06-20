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
2. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update `.env` with your private values (especially `TOKEN_SECRET`, SMTP creds, and PDF path)

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
