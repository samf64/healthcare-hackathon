import './style.css'

const API_BASE = ''

const state = {
  templates: [],
  patientPresets: [],
  selectedTemplate: '',
  selectedPresetId: '',
}

const app = document.getElementById('app')

function valueFrom(obj, keys, fallback = '') {
  for (const key of keys) {
    const value = obj?.[key]
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      return String(value).trim()
    }
  }
  return fallback
}

function render() {
  app.innerHTML = `
    <div class="page-shell">
      <header class="top-bar">
        <div class="brand">
          <img src="/LABRAT_LOGO.png" alt="LabRat Logo" class="brand-logo" />
          <div>
            <p class="eyebrow">Lab Workflow</p>
            <h1>Requisition Filler</h1>
          </div>
        </div>
        <div class="top-actions">
          <button id="loadTemplatesBtn" class="primary-btn">Load Templates</button>
          <button id="loadPatientPresetsBtn" class="secondary-btn">Refresh Patients</button>
        </div>
      </header>

      <main class="content-grid">
        <section class="panel panel--left">
          <div class="panel-header">
            <h2>Available Templates</h2>
          </div>
          <div class="upload-row">
            <input id="templateUpload" type="file" accept=".pdf,application/pdf" />
            <button id="uploadTemplateBtn" class="secondary-btn">Upload PDF</button>
          </div>
          <div id="templatesList" class="template-list"></div>
          <iframe id="templatePreview" class="preview-frame" title="Template preview"></iframe>
        </section>

        <section class="panel panel--right">
          <div class="panel-header">
            <h2>Patient Presets</h2>
          </div>
          <div class="upload-row">
            <input id="patientPresetUpload" type="file" accept=".json,application/json" />
            <button id="uploadPatientPresetBtn" class="secondary-btn">Save JSON</button>
          </div>
          <div class="preset-controls">
            <select id="patientPresetSelect"></select>
            <button id="deletePatientPresetBtn" class="secondary-btn">Delete</button>
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
  const patientPresetSelect = document.getElementById('patientPresetSelect')
  const fillForm = document.getElementById('fillForm')

  document.getElementById('loadTemplatesBtn').addEventListener('click', loadTemplates)
  document.getElementById('loadPatientPresetsBtn').addEventListener('click', loadPatientPresets)
  document.getElementById('uploadTemplateBtn').addEventListener('click', uploadTemplate)
  document.getElementById('uploadPatientPresetBtn').addEventListener('click', uploadPatientPreset)
  document.getElementById('deletePatientPresetBtn').addEventListener('click', deletePatientPreset)
  document.getElementById('historyBtn').addEventListener('click', loadHistory)
  patientPresetSelect.addEventListener('change', async () => {
    const selectedId = patientPresetSelect.value
    if (!selectedId) return
    state.selectedPresetId = selectedId
    await loadSelectedPreset(selectedId)
  })

  fillForm.addEventListener('submit', async (event) => {
    event.preventDefault()
    const formData = new FormData(fillForm)

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

    const json = await response.json()
    resultOutput.textContent = JSON.stringify(json, null, 2)
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

  function populatePatientPresetOptions() {
    patientPresetSelect.innerHTML = ''
    const emptyOption = document.createElement('option')
    emptyOption.value = ''
    emptyOption.textContent = 'Select patient preset'
    patientPresetSelect.appendChild(emptyOption)

    state.patientPresets.forEach((preset) => {
      const option = document.createElement('option')
      option.value = String(preset.id)
      option.textContent = `${preset.name} (#${preset.id})`
      patientPresetSelect.appendChild(option)
    })

    if (state.selectedPresetId) {
      patientPresetSelect.value = String(state.selectedPresetId)
    }
  }

  async function loadPatientPresets() {
    const response = await fetch(`${API_BASE}/api/patient-json-files`)
    const presets = await response.json()
    state.patientPresets = presets
    populatePatientPresetOptions()
  }

  async function loadSelectedPreset(presetId) {
    const response = await fetch(`${API_BASE}/api/patient-json-files/${encodeURIComponent(presetId)}`)
    const data = await response.json()
    const payload = data.data || {}

    fillForm.elements.full_name.value = valueFrom(payload, ['full_name', 'fullName'], '')
    fillForm.elements.email.value = valueFrom(payload, ['email'], '')
    fillForm.elements.patient_last_name.value = valueFrom(payload, ['patient_last_name', 'last_name', 'lastName'], '')
    fillForm.elements.patient_first_name.value = valueFrom(
      payload,
      ['patient_first_name', 'patient_first_and_middle_names', 'first_and_middle_names', 'first_name', 'firstName'],
      ''
    )
    fillForm.elements.health_number.value = valueFrom(payload, ['health_number', 'healthNumber', 'insurance_number'], '')
    fillForm.elements.date_of_birth.value = valueFrom(payload, ['date_of_birth', 'dob', 'dateOfBirth'], '')
    fillForm.elements.service_date.value = valueFrom(payload, ['service_date'], '')
    fillForm.elements.phone_number.value = valueFrom(payload, ['phone_number', 'phone', 'patients_telephone_contact_number'], '')
    fillForm.elements.address.value = valueFrom(payload, ['address', 'patients_address'], '')
  }

  async function uploadTemplate() {
    const input = document.getElementById('templateUpload')
    if (!input.files || !input.files[0]) return
    const form = new FormData()
    form.append('file', input.files[0])
    const response = await fetch(`${API_BASE}/api/template-files/upload`, {
      method: 'POST',
      body: form,
    })
    resultOutput.textContent = JSON.stringify(await response.json(), null, 2)
    input.value = ''
    await loadTemplates()
  }

  async function uploadPatientPreset() {
    const input = document.getElementById('patientPresetUpload')
    if (!input.files || !input.files[0]) return
    const form = new FormData()
    form.append('file', input.files[0])
    const response = await fetch(`${API_BASE}/api/patient-json-files/upload`, {
      method: 'POST',
      body: form,
    })
    resultOutput.textContent = JSON.stringify(await response.json(), null, 2)
    input.value = ''
    await loadPatientPresets()
  }

  async function deletePatientPreset() {
    const presetId = patientPresetSelect.value
    if (!presetId) return
    await fetch(`${API_BASE}/api/patient-json-files/${encodeURIComponent(presetId)}`, {
      method: 'DELETE',
    })
    state.selectedPresetId = ''
    await loadPatientPresets()
    resultOutput.textContent = 'Deleted selected patient preset.'
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
loadTemplates()
loadPatientPresets()
