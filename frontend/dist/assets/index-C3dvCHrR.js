(function(){const o=document.createElement("link").relList;if(o&&o.supports&&o.supports("modulepreload"))return;for(const n of document.querySelectorAll('link[rel="modulepreload"]'))d(n);new MutationObserver(n=>{for(const a of n)if(a.type==="childList")for(const s of a.addedNodes)s.tagName==="LINK"&&s.rel==="modulepreload"&&d(s)}).observe(document,{childList:!0,subtree:!0});function u(n){const a={};return n.integrity&&(a.integrity=n.integrity),n.referrerPolicy&&(a.referrerPolicy=n.referrerPolicy),n.crossOrigin==="use-credentials"?a.credentials="include":n.crossOrigin==="anonymous"?a.credentials="omit":a.credentials="same-origin",a}function d(n){if(n.ep)return;n.ep=!0;const a=u(n);fetch(n.href,a)}})();const p="",l={templates:[],patientPresets:[],selectedTemplate:"",selectedPresetId:""},I=document.getElementById("app");function c(m,o,u=""){for(const d of o){const n=m==null?void 0:m[d];if(n!=null&&String(n).trim()!=="")return String(n).trim()}return u}function L(){I.innerHTML=`
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
  `;const m=document.getElementById("templatesList"),o=document.getElementById("templateSelect"),u=document.getElementById("templatePreview"),d=document.getElementById("resultOutput"),n=document.getElementById("historyOutput"),a=document.getElementById("patientPresetSelect"),s=document.getElementById("fillForm");document.getElementById("loadTemplatesBtn").addEventListener("click",h),document.getElementById("loadPatientPresetsBtn").addEventListener("click",f),document.getElementById("uploadTemplateBtn").addEventListener("click",b),document.getElementById("uploadPatientPresetBtn").addEventListener("click",P),document.getElementById("deletePatientPresetBtn").addEventListener("click",E),document.getElementById("historyBtn").addEventListener("click",w),a.addEventListener("change",async()=>{const t=a.value;t&&(l.selectedPresetId=t,await g(t))}),s.addEventListener("submit",async t=>{t.preventDefault();const e=new FormData(s),i={full_name:e.get("full_name"),email:e.get("email"),template_name:e.get("template_name"),patient_last_name:e.get("patient_last_name"),patient_first_name:e.get("patient_first_name"),health_number:e.get("health_number"),date_of_birth:e.get("date_of_birth"),service_date:e.get("service_date"),phone_number:e.get("phone_number"),address:e.get("address")},B=await(await fetch(`${p}/api/forms/fill-template`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(i)})).json();d.textContent=JSON.stringify(B,null,2),document.getElementById("historyEmail").value=i.email});function y(){o.innerHTML="",l.templates.forEach(t=>{const e=document.createElement("option");e.value=t.name,e.textContent=t.name,o.appendChild(e)}),l.templates.length>0&&(l.selectedTemplate=l.templates[0].name,o.value=l.selectedTemplate,u.src=l.templates[0].preview_url)}function v(){m.innerHTML="",l.templates.forEach(t=>{const e=document.createElement("button");e.type="button",e.className="template-card",e.innerHTML=`
        <strong>${t.name}</strong>
        <span>Open preview</span>
      `,e.addEventListener("click",()=>{l.selectedTemplate=t.name,o.value=t.name,u.src=t.preview_url}),m.appendChild(e)})}function _(){a.innerHTML="";const t=document.createElement("option");t.value="",t.textContent="Select patient preset",a.appendChild(t),l.patientPresets.forEach(e=>{const i=document.createElement("option");i.value=String(e.id),i.textContent=`${e.name} (#${e.id})`,a.appendChild(i)}),l.selectedPresetId&&(a.value=String(l.selectedPresetId))}async function f(){const e=await(await fetch(`${p}/api/patient-json-files`)).json();l.patientPresets=e,_()}async function g(t){const r=(await(await fetch(`${p}/api/patient-json-files/${encodeURIComponent(t)}`)).json()).data||{};s.elements.full_name.value=c(r,["full_name","fullName"],""),s.elements.email.value=c(r,["email"],""),s.elements.patient_last_name.value=c(r,["patient_last_name","last_name","lastName"],""),s.elements.patient_first_name.value=c(r,["patient_first_name","patient_first_and_middle_names","first_and_middle_names","first_name","firstName"],""),s.elements.health_number.value=c(r,["health_number","healthNumber","insurance_number"],""),s.elements.date_of_birth.value=c(r,["date_of_birth","dob","dateOfBirth"],""),s.elements.service_date.value=c(r,["service_date"],""),s.elements.phone_number.value=c(r,["phone_number","phone","patients_telephone_contact_number"],""),s.elements.address.value=c(r,["address","patients_address"],"")}async function b(){const t=document.getElementById("templateUpload");if(!t.files||!t.files[0])return;const e=new FormData;e.append("file",t.files[0]);const i=await fetch(`${p}/api/template-files/upload`,{method:"POST",body:e});d.textContent=JSON.stringify(await i.json(),null,2),t.value="",await h()}async function P(){const t=document.getElementById("patientPresetUpload");if(!t.files||!t.files[0])return;const e=new FormData;e.append("file",t.files[0]);const i=await fetch(`${p}/api/patient-json-files/upload`,{method:"POST",body:e});d.textContent=JSON.stringify(await i.json(),null,2),t.value="",await f()}async function E(){const t=a.value;t&&(await fetch(`${p}/api/patient-json-files/${encodeURIComponent(t)}`,{method:"DELETE"}),l.selectedPresetId="",await f(),d.textContent="Deleted selected patient preset.")}async function h(){const e=await(await fetch(`${p}/api/template-files`)).json();l.templates=e,y(),v()}async function w(){const t=document.getElementById("historyEmail").value,e=await fetch(`${p}/api/forms/history/${encodeURIComponent(t)}`);n.textContent=JSON.stringify(await e.json(),null,2)}}L();loadTemplates();loadPatientPresets();
