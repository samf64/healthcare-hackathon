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
  <h1>Lab Requisition Assistant</h1>
  <p>Choose a template, enter patient info, generate PDF, and optionally enable reminders.</p>

  <section>
    <h2>1) Available Templates</h2>
    <button onclick="loadTemplates()">Load Templates</button>
    <pre id="templates"></pre>
  </section>

  <section>
    <h2>2) Generate Lab Requisition</h2>
    <input id="full_name" placeholder="Full name" />
    <input id="email" placeholder="Email" />
    <input id="patient_last_name" placeholder="Patient last name" />
    <input id="patient_first_name" placeholder="Patient first name" />
    <input id="health_number" placeholder="Insurance/health number" />
    <input id="date_of_birth" placeholder="Date of birth (YYYY-MM-DD)" />
    <input id="service_date" placeholder="Service date (YYYY-MM-DD)" />
    <select id="template_key">
      <option value="diabetes_blood_test">Diabetes Blood Test</option>
      <option value="general_annual_lab">General Annual Lab Requisition</option>
      <option value="thyroid_monitoring">Thyroid Monitoring</option>
    </select>
    <label><input id="reminder_enabled" type="checkbox" /> Enable reminders</label>
    <select id="cadence">
      <option value="12_months">Remind every 12 months</option>
      <option value="6_months">Remind every 6 months</option>
    </select>
    <button onclick="generate()">Generate PDF Request</button>
    <pre id="generate_result"></pre>
  </section>

  <section>
    <h2>3) Stored Filled Forms</h2>
    <input id="history_email" placeholder="Email for history lookup" />
    <button onclick="loadHistory()">Load Form History</button>
    <pre id="history"></pre>
  </section>

  <p>Advanced API testing: <a href="/docs" target="_blank">/docs</a></p>

  <script>
    async function loadTemplates() {
      const res = await fetch('/api/templates');
      document.getElementById('templates').textContent = JSON.stringify(await res.json(), null, 2);
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
        template_key: document.getElementById('template_key').value,
        reminder_enabled: document.getElementById('reminder_enabled').checked,
        cadence: document.getElementById('cadence').value,
        profile_patch
      };
      const res = await fetch('/api/forms/generate', {
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

