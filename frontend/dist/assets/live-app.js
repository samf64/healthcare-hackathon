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
          <details id="templatePreviewPanel">
            <summary>Template Preview (open/close)</summary>
            <iframe id="templatePreview" class="preview-frame" title="Template preview"></iframe>
          </details>
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
          <div class="form-grid">
            <select name="template_name" id="templateSelect"></select>
            <button id="fillFromPresetBtn" type="button" class="primary-btn wide">Fill Template PDF</button>
          </div>
          <div class="form-grid" style="margin-top: 12px;">
            <select id="reminderMode">
              <option value="instant">Instant email</option>
              <option value="months">After number of months</option>
            </select>
            <input id="reminderRecipient" type="email" placeholder="Reminder recipient email (optional)" />
            <input id="reminderMonths" type="number" min="1" max="24" value="6" placeholder="Months (1-24)" />
            <button id="setReminderBtn" type="button" class="secondary-btn wide">Set Reminder</button>
          </div>
          <pre id="resultOutput" class="result-output"></pre>
        </section>
      </main>
    </div>
  `

  const templatesList = document.getElementById('templatesList')
  const templateSelect = document.getElementById('templateSelect')
  const templatePreview = document.getElementById('templatePreview')
  const templatePreviewPanel = document.getElementById('templatePreviewPanel')
  const resultOutput = document.getElementById('resultOutput')
  const patientPresetSelect = document.getElementById('patientPresetSelect')
  const reminderMode = document.getElementById('reminderMode')
  const reminderRecipient = document.getElementById('reminderRecipient')
  const reminderMonths = document.getElementById('reminderMonths')

  function setResult(message, isError = false) {
    resultOutput.textContent = isError ? `Error: ${message}` : message
  }

  async function parseApiResponse(response) {
    let data = {}
    try {
      data = await response.json()
    } catch (_err) {
      data = {}
    }
    if (!response.ok) {
      throw new Error(data.detail || 'Request failed.')
    }
    return data
  }

  document.getElementById('loadTemplatesBtn').addEventListener('click', loadTemplates)
  document.getElementById('loadPatientPresetsBtn').addEventListener('click', loadPatientPresets)
  document.getElementById('uploadTemplateBtn').addEventListener('click', uploadTemplate)
  document.getElementById('uploadPatientPresetBtn').addEventListener('click', uploadPatientPreset)
  document.getElementById('deletePatientPresetBtn').addEventListener('click', deletePatientPreset)
  document.getElementById('fillFromPresetBtn').addEventListener('click', fillTemplateFromPreset)
  document.getElementById('setReminderBtn').addEventListener('click', setReminder)
  function updateReminderModeUI() {
    const isMonths = reminderMode.value === 'months'
    reminderMonths.disabled = !isMonths
    reminderMonths.style.display = isMonths ? '' : 'none'
  }

  reminderMode.addEventListener('change', updateReminderModeUI)
  patientPresetSelect.addEventListener('change', () => {
    state.selectedPresetId = patientPresetSelect.value
  })

  function showTemplatePreview(template) {
    if (!template) return
    state.selectedTemplate = template.name
    templateSelect.value = template.name
    templatePreview.src = template.preview_url
    templatePreviewPanel.open = true
  }

  function populateTemplateOptions() {
    templateSelect.innerHTML = ''
    state.templates.forEach((template) => {
      const option = document.createElement('option')
      option.value = template.name
      option.textContent = template.name
      templateSelect.appendChild(option)
    })

    if (state.templates.length > 0) {
      showTemplatePreview(state.templates[0])
    }
  }

  function renderTemplates() {
    templatesList.innerHTML = ''
    state.templates.forEach((template) => {
      const item = document.createElement('div')
      item.className = 'template-card'
      item.innerHTML = `
        <strong>${template.name}</strong>
        <span>
          <button type="button" class="secondary-btn" data-action="preview">Preview</button>
          <button type="button" class="secondary-btn" data-action="delete">Delete</button>
        </span>
      `
      item.querySelector('[data-action="preview"]').addEventListener('click', () => {
        showTemplatePreview(template)
      })
      item.querySelector('[data-action="delete"]').addEventListener('click', async () => {
        try {
          const response = await fetch(`${API_BASE}/api/template-files/${encodeURIComponent(template.name)}`, {
            method: 'DELETE',
          })
          await parseApiResponse(response)
          await loadTemplates()
          setResult(`Template "${template.name}" deleted.`)
        } catch (error) {
          setResult(error.message, true)
        }
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
    try {
      const response = await fetch(`${API_BASE}/api/patient-json-files`)
      const presets = await parseApiResponse(response)
      state.patientPresets = presets
      populatePatientPresetOptions()
    } catch (error) {
      setResult(error.message, true)
    }
  }

  async function uploadTemplate() {
    const input = document.getElementById('templateUpload')
    if (!input.files || !input.files[0]) return
    const form = new FormData()
    form.append('file', input.files[0])
    try {
      const response = await fetch(`${API_BASE}/api/template-files/upload`, {
        method: 'POST',
        body: form,
      })
      const data = await parseApiResponse(response)
      input.value = ''
      await loadTemplates()
      setResult(`Template "${data.name || 'PDF'}" uploaded successfully.`)
    } catch (error) {
      setResult(error.message, true)
    }
  }

  async function uploadPatientPreset() {
    const input = document.getElementById('patientPresetUpload')
    if (!input.files || !input.files[0]) return
    const form = new FormData()
    form.append('file', input.files[0])
    try {
      const response = await fetch(`${API_BASE}/api/patient-json-files/upload`, {
        method: 'POST',
        body: form,
      })
      const data = await parseApiResponse(response)
      input.value = ''
      await loadPatientPresets()
      setResult(`Patient file "${data.name || 'JSON'}" saved successfully.`)
    } catch (error) {
      setResult(error.message, true)
    }
  }

  async function deletePatientPreset() {
    const presetId = patientPresetSelect.value
    if (!presetId) return
    try {
      const response = await fetch(`${API_BASE}/api/patient-json-files/${encodeURIComponent(presetId)}`, {
        method: 'DELETE',
      })
      const data = await parseApiResponse(response)
      state.selectedPresetId = ''
      await loadPatientPresets()
      setResult(`Patient file "${data.deleted || ''}" deleted.`)
    } catch (error) {
      setResult(error.message, true)
    }
  }

  async function loadTemplates() {
    try {
      const response = await fetch(`${API_BASE}/api/template-files`)
      const templates = await parseApiResponse(response)
      state.templates = templates
      populateTemplateOptions()
      renderTemplates()
    } catch (error) {
      setResult(error.message, true)
    }
  }

  async function fillTemplateFromPreset() {
    if (!state.selectedPresetId) {
      resultOutput.textContent = 'Select a patient JSON file first.'
      return
    }

    const response = await fetch(`${API_BASE}/api/patient-json-files/${encodeURIComponent(state.selectedPresetId)}`)
    const preset = await parseApiResponse(response)
    const data = preset.data || {}
    const payload = {
      full_name: valueFrom(data, ['full_name', 'fullName'], 'Patient'),
      email: valueFrom(data, ['email']),
      template_name: templateSelect.value,
      patient_last_name: valueFrom(data, ['patient_last_name', 'last_name', 'lastName']),
      patient_first_name: valueFrom(
        data,
        ['patient_first_name', 'patient_first_and_middle_names', 'first_and_middle_names', 'first_name', 'firstName']
      ),
      health_number: valueFrom(data, ['health_number', 'healthNumber', 'insurance_number']),
      health_version: valueFrom(data, ['health_version', 'healthVersion']),
      sex: valueFrom(data, ['sex', 'gender']).toUpperCase(),
      province: valueFrom(data, ['province'], 'ON').toUpperCase(),
      other_provincial_registration_number: valueFrom(
        data,
        ['other_provincial_registration_number', 'otherProvincialRegistrationNumber']
      ),
      date_of_birth: valueFrom(data, ['date_of_birth', 'dob', 'dateOfBirth']),
      phone_number: valueFrom(data, ['phone_number', 'phone', 'patients_telephone_contact_number']),
      address: valueFrom(data, ['address', 'patients_address']),
    }
    if (!payload.email) {
      setResult('Selected patient JSON is missing email.', true)
      return
    }
    try {
      const fillResponse = await fetch(`${API_BASE}/api/forms/fill-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const dataOut = await parseApiResponse(fillResponse)
      setResult(`Template filled successfully. Generated file: ${dataOut.generated_file || 'created'}.`)
    } catch (error) {
      setResult(error.message, true)
    }
  }

  async function setReminder() {
    if (!state.selectedPresetId) {
      resultOutput.textContent = 'Select a patient JSON file first.'
      return
    }
    if (!templateSelect.value) {
      resultOutput.textContent = 'Select a template first.'
      return
    }
    const mode = reminderMode.value
    const months = Number(reminderMonths.value || 0)
    const payload = {
      patient_json_file_id: Number(state.selectedPresetId),
      template_name: templateSelect.value,
      mode,
      months: mode === 'months' ? months : null,
      recipient_email: reminderRecipient.value.trim() || null,
    }
    try {
      const response = await fetch(`${API_BASE}/api/reminders/patient-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await parseApiResponse(response)
      if (data.mode === 'instant') {
        setResult(data.sent_now ? 'Reminder email sent successfully.' : `Reminder email failed: ${data.detail}`)
      } else {
        setResult(`Reminder scheduled successfully. Next email date: ${data.next_send_on || 'set'}.`)
      }
    } catch (error) {
      setResult(error.message, true)
    }
  }

  let isRefreshing = false
  async function refreshAllData() {
    if (isRefreshing) return
    isRefreshing = true
    try {
      await Promise.all([loadTemplates(), loadPatientPresets()])
    } finally {
      isRefreshing = false
    }
  }

  window.addEventListener('pageshow', refreshAllData)
  window.addEventListener('focus', refreshAllData)
  updateReminderModeUI()
  refreshAllData()
}

render()
