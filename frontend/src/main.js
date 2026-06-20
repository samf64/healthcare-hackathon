import './style.css'

const API_BASE = ''

const state = {
  templates: [],
  selectedTemplate: '',
}

const app = document.getElementById('app')

function render() {
  app.innerHTML = `
    <div class="page-shell">
      <header class="top-bar">
        <div class="brand">
          <img src="/logo-placeholder.jpg" alt="Logo placeholder" class="brand-logo" />
          <div>
            <p class="eyebrow">Lab Workflow</p>
            <h1>Requisition Filler</h1>
          </div>
        </div>
        <button id="loadTemplatesBtn" class="primary-btn">Load Templates</button>
      </header>

      <main class="content-grid">
        <section class="panel panel--left">
          <div class="panel-header">
            <h2>Available Templates</h2>
          </div>
          <div id="templatesList" class="template-list"></div>
          <iframe id="templatePreview" class="preview-frame" title="Template preview"></iframe>
        </section>

        <section class="panel panel--right">
          <div class="panel-header">
            <h2>Patient Details</h2>
          </div>
          <form id="fillForm" class="form-grid">
            <input name="full_name" placeholder="Full name" />
            <input name="email" placeholder="Email" />
            <input name="patient_last_name" placeholder="Patient last name" />
            <input name="patient_first_name" placeholder="Patient first name" />
            <input name="health_number" placeholder="Health number" />
            <input name="date_of_birth" placeholder="Date of birth (YYYY-MM-DD)" />
            <input name="service_date" placeholder="Service date (YYYY-MM-DD)" />
            <input name="phone_number" placeholder="Phone number (optional)" />
            <input name="address" placeholder="Address (optional)" />
            <select name="template_name" id="templateSelect"></select>
            <button type="submit" class="primary-btn wide">Fill Template PDF</button>
          </form>
          <pre id="resultOutput" class="result-output"></pre>
        </section>
      </main>

      <section class="panel history-panel">
        <div class="panel-header">
          <h2>Stored Forms</h2>
        </div>
        <div class="history-controls">
          <input id="historyEmail" placeholder="Email for history lookup" />
          <button id="historyBtn" class="secondary-btn">Load History</button>
        </div>
        <pre id="historyOutput" class="result-output"></pre>
      </section>
    </div>
  `

  const templatesList = document.getElementById('templatesList')
  const templateSelect = document.getElementById('templateSelect')
  const templatePreview = document.getElementById('templatePreview')
  const resultOutput = document.getElementById('resultOutput')
  const historyOutput = document.getElementById('historyOutput')

  document.getElementById('loadTemplatesBtn').addEventListener('click', loadTemplates)
  document.getElementById('historyBtn').addEventListener('click', loadHistory)
  document.getElementById('fillForm').addEventListener('submit', async (event) => {
    event.preventDefault()
    const formData = new FormData(event.target)

    const payload = {
      full_name: formData.get('full_name'),
      email: formData.get('email'),
      template_name: formData.get('template_name'),
      patient_last_name: formData.get('patient_last_name'),
      patient_first_name: formData.get('patient_first_name'),
      health_number: formData.get('health_number'),
      date_of_birth: formData.get('date_of_birth'),
      service_date: formData.get('service_date'),
      phone_number: formData.get('phone_number'),
      address: formData.get('address'),
    }

    const response = await fetch(`${API_BASE}/api/forms/fill-template`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    resultOutput.textContent = JSON.stringify(await response.json(), null, 2)
    document.getElementById('historyEmail').value = payload.email
  })

  function populateTemplateOptions() {
    templateSelect.innerHTML = ''
    state.templates.forEach((template) => {
      const option = document.createElement('option')
      option.value = template.name
      option.textContent = template.name
      templateSelect.appendChild(option)
    })

    if (state.templates.length > 0) {
      state.selectedTemplate = state.templates[0].name
      templateSelect.value = state.selectedTemplate
      templatePreview.src = state.templates[0].preview_url
    }
  }

  function renderTemplates() {
    templatesList.innerHTML = ''
    state.templates.forEach((template) => {
      const item = document.createElement('button')
      item.type = 'button'
      item.className = 'template-card'
      item.innerHTML = `
        <strong>${template.name}</strong>
        <span>Open preview</span>
      `
      item.addEventListener('click', () => {
        state.selectedTemplate = template.name
        templateSelect.value = template.name
        templatePreview.src = template.preview_url
      })
      templatesList.appendChild(item)
    })
  }

  async function loadTemplates() {
    const response = await fetch(`${API_BASE}/api/template-files`)
    const templates = await response.json()
    state.templates = templates
    populateTemplateOptions()
    renderTemplates()
  }

  async function loadHistory() {
    const email = document.getElementById('historyEmail').value
    const response = await fetch(`${API_BASE}/api/forms/history/${encodeURIComponent(email)}`)
    historyOutput.textContent = JSON.stringify(await response.json(), null, 2)
  }
}

render()
