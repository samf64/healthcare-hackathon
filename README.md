# Lab Template Filler

Simple workflow:
- Upload lab-test PDF templates from the frontend (stored in database)
- Choose template in app
- Enter patient information
- Generate a filled PDF in `generated_forms/`

## Setup

1. Create and activate virtual environment:
   - `python -m venv .venv`
   - `.venv\Scripts\Activate.ps1`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Configure env:
   - Copy `.env.example` to `.env`
   - Set `TEMPLATE_LIBRARY_DIR` (optional auto-import source) and `GENERATED_PDF_DIR` as needed

## Run

`uvicorn app.main:app --reload`

## Use

1. Place template PDFs inside `template_library/`
2. Open `http://127.0.0.1:8000/`
3. Upload templates using **Upload Template to DB**
4. Click **Load Templates**
5. Pick a template and fill patient fields
6. Click **Fill Template PDF**

## Main Endpoints

- `GET /api/template-files` list template PDFs from database
- `POST /api/template-files/upload` upload template into database
- `DELETE /api/template-files/{name}` delete template from database
- `GET /api/template-files/preview?name=<template.pdf>` preview selected template
- `POST /api/forms/fill-template` fill selected template with patient information
- `GET /api/forms/history/{email}` list generated forms by user email

## Mapping Behavior

- The app uses one global field mapping for all templates (based on the Ontario Laboratory Requisition form).
- No per-template remapping is required.
- Templates must be fillable AcroForm PDFs for strict mapping to work.
