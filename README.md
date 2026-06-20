# Lab Template Filler

Simple workflow:
- Put lab-test PDF templates in `template_library/`
- Choose a template in the app
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
   - Set `TEMPLATE_LIBRARY_DIR` and `GENERATED_PDF_DIR` as needed

## Run

`uvicorn app.main:app --reload`

## Use

1. Place template PDFs inside `template_library/`
2. Open `http://127.0.0.1:8000/`
3. Click **Load Templates**
4. Pick a template and fill patient fields
5. Click **Fill Template PDF**

## Main Endpoints

- `GET /api/template-files` list template PDFs from folder
- `GET /api/template-files/preview?name=<template.pdf>` preview selected template
- `POST /api/forms/fill-template` fill selected template with patient information
- `GET /api/forms/history/{email}` list generated forms by user email
