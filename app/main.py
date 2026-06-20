from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.routes import router as api_router
from app.config import settings
from app.database import Base, engine
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Lab Reminder App</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; max-width: 820px; }
    section { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
    input, select, textarea, button { width: 100%; margin-top: 8px; margin-bottom: 8px; padding: 8px; }
    button { cursor: pointer; }
    pre { background: #f7f7f7; padding: 12px; border-radius: 6px; overflow-x: auto; }
  </style>
</head>
<body>
  <h1>Lab Template Filler</h1>
  <p>Templates are stored in the database. Upload/delete them from here, then fill patient info.</p>

  <section>
    <h2>1) Template Files</h2>
    <input id="template_upload" type="file" accept=".pdf,application/pdf" />
    <button onclick="uploadTemplate()">Upload Template to DB</button>
    <button onclick="loadTemplates()">Load Templates</button>
    <div id="templates"></div>
    <details id="template_preview_panel" style="margin-top:10px;">
      <summary>Template Preview (open/close)</summary>
      <iframe id="template_preview" title="Template preview" style="width:100%;height:500px;border:1px solid #ddd;border-radius:6px;"></iframe>
    </details>
  </section>

  <section>
    <h2>2) Fill Selected Template</h2>
    <input id="patient_json_db_upload" type="file" accept=".json,application/json" />
    <button onclick="uploadPatientJsonToDb()">Upload Patient JSON to DB</button>
    <button onclick="refreshPatientJsonDb()">Refresh Saved Patient Files</button>
    <select id="patient_json_db_select"></select>
    <button onclick="deleteSelectedPatientJsonDb()">Delete Selected Patient File</button>
    <select id="template_name"></select>
    <button onclick="generate()">Fill Template PDF</button>
    <pre id="generate_result"></pre>
  </section>

  <p>API docs: <a href="/docs" target="_blank">/docs</a></p>

  <script>
    function previewTemplate(name, previewUrl) {
      document.getElementById('template_preview').src = previewUrl;
      document.getElementById('template_name').value = name;
      document.getElementById('template_preview_panel').open = true;
    }

    async function loadTemplates() {
      const res = await fetch('/api/template-files');
      const templates = await res.json();
      const wrap = document.getElementById('templates');
      const select = document.getElementById('template_name');
      wrap.innerHTML = '';
      select.innerHTML = '';
      templates.forEach((t, i) => {
        const opt = document.createElement('option');
        opt.value = t.name;
        opt.textContent = t.name;
        select.appendChild(opt);

        const row = document.createElement('div');
        row.style.marginBottom = '10px';
        row.innerHTML = `<strong>${t.name}</strong><br/><button data-action="preview" data-name="${t.name}">Preview</button> <a href="${t.preview_url}" target="_blank">Open in new tab</a> <button data-action="delete" data-name="${t.name}">Delete</button>`;
        row.querySelector('[data-action="preview"]').onclick = (event) => {
          event.stopPropagation();
          const name = event.target.getAttribute('data-name');
          previewTemplate(name, t.preview_url);
        };
        row.querySelector('[data-action="delete"]').onclick = async (event) => {
          event.stopPropagation();
          const name = event.target.getAttribute('data-name');
          await fetch(`/api/template-files/${encodeURIComponent(name)}`, { method: 'DELETE' });
          await loadTemplates();
        };
        wrap.appendChild(row);
        if (i === 0) {
          previewTemplate(t.name, t.preview_url);
        }
      });
    }

    async function uploadTemplate() {
      const input = document.getElementById('template_upload');
      if (!input.files || !input.files[0]) return;
      const form = new FormData();
      form.append('file', input.files[0]);
      const res = await fetch('/api/template-files/upload', { method: 'POST', body: form });
      document.getElementById('generate_result').textContent = JSON.stringify(await res.json(), null, 2);
      input.value = '';
      await loadTemplates();
    }

    function _valueFrom(obj, keys, fallback = '') {
      for (const key of keys) {
        if (obj[key] !== undefined && obj[key] !== null && String(obj[key]).trim() !== '') {
          return String(obj[key]).trim();
        }
      }
      return fallback;
    }

    async function refreshPatientJsonDb() {
      const res = await fetch('/api/patient-json-files');
      const files = await res.json();
      const select = document.getElementById('patient_json_db_select');
      select.innerHTML = '';
      files.forEach((f) => {
        const opt = document.createElement('option');
        opt.value = f.id;
        opt.textContent = `${f.name} (#${f.id})`;
        select.appendChild(opt);
      });
    }

    async function uploadPatientJsonToDb() {
      const input = document.getElementById('patient_json_db_upload');
      if (!input.files || !input.files[0]) return;
      const form = new FormData();
      form.append('file', input.files[0]);
      const res = await fetch('/api/patient-json-files/upload', { method: 'POST', body: form });
      document.getElementById('generate_result').textContent = JSON.stringify(await res.json(), null, 2);
      input.value = '';
      await refreshPatientJsonDb();
    }

    async function deleteSelectedPatientJsonDb() {
      const select = document.getElementById('patient_json_db_select');
      if (!select.value) return;
      await fetch(`/api/patient-json-files/${encodeURIComponent(select.value)}`, { method: 'DELETE' });
      await refreshPatientJsonDb();
      document.getElementById('generate_result').textContent = 'Deleted selected patient JSON file.';
    }

    async function generate() {
      const patientSelect = document.getElementById('patient_json_db_select');
      if (!patientSelect.value) {
        document.getElementById('generate_result').textContent = 'Select a saved patient JSON file first.';
        return;
      }
      const patientRes = await fetch(`/api/patient-json-files/${encodeURIComponent(patientSelect.value)}`);
      const patientPayload = await patientRes.json();
      const data = patientPayload.data || {};
      const body = {
        full_name: _valueFrom(data, ['full_name', 'fullName'], 'Patient'),
        email: _valueFrom(data, ['email']),
        template_name: document.getElementById('template_name').value,
        patient_last_name: _valueFrom(data, ['patient_last_name', 'last_name', 'lastName']),
        patient_first_name: _valueFrom(
          data,
          ['patient_first_name', 'patient_first_and_middle_names', 'first_and_middle_names', 'first_name', 'firstName']
        ),
        health_number: _valueFrom(data, ['health_number', 'healthNumber', 'insurance_number']),
        health_version: _valueFrom(data, ['health_version', 'healthVersion']),
        sex: _valueFrom(data, ['sex', 'gender']).toUpperCase(),
        province: _valueFrom(data, ['province'], 'ON').toUpperCase(),
        other_provincial_registration_number: _valueFrom(
          data,
          ['other_provincial_registration_number', 'otherProvincialRegistrationNumber']
        ),
        date_of_birth: _valueFrom(data, ['date_of_birth', 'dob', 'dateOfBirth']),
        phone_number: _valueFrom(data, ['phone_number', 'phone', 'patients_telephone_contact_number']),
        address: _valueFrom(data, ['address', 'patients_address'])
      };
      if (!body.email) {
        document.getElementById('generate_result').textContent = 'Selected patient JSON is missing `email`.';
        return;
      }
      const res = await fetch('/api/forms/fill-template', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      document.getElementById('generate_result').textContent = JSON.stringify(await res.json(), null, 2);
    }

    loadTemplates();
    refreshPatientJsonDb();
  </script>
</body>
</html>
"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

