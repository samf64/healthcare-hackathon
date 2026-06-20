(function(){const s=document.createElement("link").relList;if(s&&s.supports&&s.supports("modulepreload"))return;for(const t of document.querySelectorAll('link[rel="modulepreload"]'))r(t);new MutationObserver(t=>{for(const n of t)if(n.type==="childList")for(const i of n.addedNodes)i.tagName==="LINK"&&i.rel==="modulepreload"&&r(i)}).observe(document,{childList:!0,subtree:!0});function o(t){const n={};return t.integrity&&(n.integrity=t.integrity),t.referrerPolicy&&(n.referrerPolicy=t.referrerPolicy),t.crossOrigin==="use-credentials"?n.credentials="include":t.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function r(t){if(t.ep)return;t.ep=!0;const n=o(t);fetch(t.href,n)}})();const c="",l={templates:[],selectedTemplate:""},f=document.getElementById("app");function y(){f.innerHTML=`
    <div class="page-shell">
      <header class="top-bar">
        <div class="brand">
          <img src="/LABRAT_LOGO.png" alt="LabRat Logo" class="brand-logo" />
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
  `;const p=document.getElementById("templatesList"),s=document.getElementById("templateSelect"),o=document.getElementById("templatePreview"),r=document.getElementById("resultOutput"),t=document.getElementById("historyOutput");document.getElementById("loadTemplatesBtn").addEventListener("click",d),document.getElementById("historyBtn").addEventListener("click",u),document.getElementById("fillForm").addEventListener("submit",async a=>{a.preventDefault();const e=new FormData(a.target),m={full_name:e.get("full_name"),email:e.get("email"),template_name:e.get("template_name"),patient_last_name:e.get("patient_last_name"),patient_first_name:e.get("patient_first_name"),health_number:e.get("health_number"),date_of_birth:e.get("date_of_birth"),service_date:e.get("service_date"),phone_number:e.get("phone_number"),address:e.get("address")},h=await fetch(`${c}/api/forms/fill-template`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(m)});r.textContent=JSON.stringify(await h.json(),null,2),document.getElementById("historyEmail").value=m.email});function n(){s.innerHTML="",l.templates.forEach(a=>{const e=document.createElement("option");e.value=a.name,e.textContent=a.name,s.appendChild(e)}),l.templates.length>0&&(l.selectedTemplate=l.templates[0].name,s.value=l.selectedTemplate,o.src=l.templates[0].preview_url)}function i(){p.innerHTML="",l.templates.forEach(a=>{const e=document.createElement("button");e.type="button",e.className="template-card",e.innerHTML=`
        <strong>${a.name}</strong>
        <span>Open preview</span>
      `,e.addEventListener("click",()=>{l.selectedTemplate=a.name,s.value=a.name,o.src=a.preview_url}),p.appendChild(e)})}async function d(){const e=await(await fetch(`${c}/api/template-files`)).json();l.templates=e,n(),i()}async function u(){const a=document.getElementById("historyEmail").value,e=await fetch(`${c}/api/forms/history/${encodeURIComponent(a)}`);t.textContent=JSON.stringify(await e.json(),null,2)}}y();
