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
    <iframe id="template_preview" title="Template preview" style="width:100%;height:500px;border:1px solid #ddd;border-radius:6px;"></iframe>
  </section>

  <section>
    <h2>2) Fill Selected Template</h2>
    <input id="patient_json_upload" type="file" accept=".json,application/json" />
    <button onclick="loadPatientJson()">Load Patient JSON</button>
    <input id="full_name" placeholder="Full name" />
    <input id="email" placeholder="Email" />
    <input id="patient_last_name" placeholder="Patient last name" />
    <input id="patient_first_name" placeholder="Patient first name" />
    <input id="health_number" placeholder="Insurance/health number" />
    <input id="health_version" placeholder="Health version (2 letters)" />
    <select id="sex">
      <option value="">Sex (optional)</option>
      <option value="M">M</option>
      <option value="F">F</option>
    </select>
    <input id="province" placeholder="Province (e.g. ON)" />
    <input id="other_provincial_registration_number" placeholder="Other provincial reg number (optional)" />
    <input id="date_of_birth" placeholder="Date of birth (YYYY-MM-DD)" />
    <input id="service_date" placeholder="Service date (YYYY-MM-DD)" />
    <input id="phone_number" placeholder="Phone number (optional)" />
    <input id="address" placeholder="Address (optional)" />
    <select id="template_name"></select>
    <button onclick="generate()">Fill Template PDF</button>
    <pre id="generate_result"></pre>
  </section>

  <section>
    <h2>3) Stored Filled Forms</h2>
    <input id="history_email" placeholder="Email for history lookup" />
    <button onclick="loadHistory()">Load Form History</button>
    <pre id="history"></pre>
  </section>

  <p>API docs: <a href="/docs" target="_blank">/docs</a></p>

  <script>
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
        row.innerHTML = `<strong>${t.name}</strong><br/><a href="${t.preview_url}" target="_blank">Open Preview PDF</a> <button data-name="${t.name}">Delete</button>`;
        row.onclick = () => {
          document.getElementById('template_preview').src = t.preview_url;
          document.getElementById('template_name').value = t.name;
        };
        row.querySelector('button').onclick = async (event) => {
          event.stopPropagation();
          const name = event.target.getAttribute('data-name');
          await fetch(`/api/template-files/${encodeURIComponent(name)}`, { method: 'DELETE' });
          await loadTemplates();
        };
        wrap.appendChild(row);
        if (i === 0) {
          document.getElementById('template_preview').src = t.preview_url;
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

    async function loadPatientJson() {
      const input = document.getElementById('patient_json_upload');
      if (!input.files || !input.files[0]) return;
      const text = await input.files[0].text();
      let data = {};
      try {
        data = JSON.parse(text);
      } catch (e) {
        document.getElementById('generate_result').textContent = 'Invalid JSON file.';
        return;
      }

      document.getElementById('patient_last_name').value = _valueFrom(data, ['patient_last_name', 'last_name', 'lastName']);
      document.getElementById('patient_first_name').value = _valueFrom(
        data,
        ['patient_first_name', 'patient_first_and_middle_names', 'first_and_middle_names', 'first_name', 'firstName']
      );
      document.getElementById('health_number').value = _valueFrom(data, ['health_number', 'healthNumber', 'insurance_number']);
      document.getElementById('health_version').value = _valueFrom(data, ['health_version', 'healthVersion']);
      document.getElementById('sex').value = _valueFrom(data, ['sex', 'gender']).toUpperCase();
      document.getElementById('province').value = _valueFrom(data, ['province'], 'ON').toUpperCase();
      document.getElementById('other_provincial_registration_number').value = _valueFrom(
        data,
        ['other_provincial_registration_number', 'otherProvincialRegistrationNumber']
      );
      document.getElementById('date_of_birth').value = _valueFrom(data, ['date_of_birth', 'dob', 'dateOfBirth']);
      document.getElementById('phone_number').value = _valueFrom(data, ['phone_number', 'phone', 'patients_telephone_contact_number']);
      document.getElementById('address').value = _valueFrom(data, ['address', 'patients_address']);

      if (data.full_name || data.email) {
        document.getElementById('full_name').value = _valueFrom(data, ['full_name', 'fullName']);
        document.getElementById('email').value = _valueFrom(data, ['email']);
      }

      document.getElementById('generate_result').textContent = 'Loaded patient JSON into form.';
      input.value = '';
    }

    async function generate() {
      const profile_patch = {
        patient_last_name: document.getElementById('patient_last_name').value,
        patient_first_name: document.getElementById('patient_first_name').value,
        health_number: document.getElementById('health_number').value,
        date_of_birth: document.getElementById('date_of_birth').value,
        service_date: document.getElementById('service_date').value
      };
      const body = {
        full_name: document.getElementById('full_name').value,
        email: document.getElementById('email').value,
        template_name: document.getElementById('template_name').value,
        patient_last_name: profile_patch.patient_last_name,
        patient_first_name: profile_patch.patient_first_name,
        health_number: profile_patch.health_number,
        health_version: document.getElementById('health_version').value,
        sex: document.getElementById('sex').value,
        province: document.getElementById('province').value || 'ON',
        other_provincial_registration_number: document.getElementById('other_provincial_registration_number').value,
        date_of_birth: profile_patch.date_of_birth,
        service_date: profile_patch.service_date,
        phone_number: document.getElementById('phone_number').value,
        address: document.getElementById('address').value
      };
      const res = await fetch('/api/forms/fill-template', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      document.getElementById('generate_result').textContent = JSON.stringify(await res.json(), null, 2);
      document.getElementById('history_email').value = body.email;
    }

    async function loadHistory() {
      const email = encodeURIComponent(document.getElementById('history_email').value);
      const res = await fetch(`/api/forms/history/${email}`);
      document.getElementById('history').textContent = JSON.stringify(await res.json(), null, 2);
    }
  </script>
</body>
</html>
"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

