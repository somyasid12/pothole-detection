// assets/js/script.js
// Dashboard script: sidebar nav, theme toggle, drag/drop upload, detect,
// in-memory result rendering, complaint generation, PDF download, email send.

// --------- CONFIG ---------
const BACKEND = ""; 
// When deploying behind a proxy or different domain, set BACKEND="https://your-backend-url"

// --------- ELEMENTS ---------
const sidebar = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebarToggle");
const themeToggle = document.getElementById("themeToggle");
const navButtons = Array.from(document.querySelectorAll(".side-link"));

const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const detectBtn = document.getElementById("detectBtn");
const clearBtn = document.getElementById("clearBtn") || null;

const loader = document.getElementById("loader");
const loaderText = document.getElementById("loaderText") || null;

const resultsSection = document.getElementById("results");
const resultsGrid = document.getElementById("resultsGrid");
const totalCountEl = document.getElementById("totalCount") || null;

const openCarouselBtn = document.getElementById("openCarouselBtn") || null;
const carouselModal = document.getElementById("carouselModal");
const carouselImg = document.getElementById("carouselImg");
const closeCarousel = document.getElementById("closeCarousel");
const prevImg = document.getElementById("prevImg");
const nextImg = document.getElementById("nextImg");

const genComplaintBtn = document.getElementById("genComplaintBtn");
const complaintText = document.getElementById("complaintText");
const downloadPdfBtn = document.getElementById("downloadPdfBtn");

const sendEmailBtn = document.getElementById("sendEmailBtn");
const emailStatus = document.getElementById("emailStatus");

const roadNameInput = document.getElementById("roadName");
const areaInput = document.getElementById("area");
const cityInput = document.getElementById("city");
const potholeCountInput = document.getElementById("potholeCount");
const extraDetailsInput = document.getElementById("extraDetails");

const emailToInput = document.getElementById("emailTo");
const emailSubjectInput = document.getElementById("emailSubject");
const emailBodyInput = document.getElementById("emailBody");

const panels = {
  upload: document.getElementById("upload"),
  results: document.getElementById("results"),
  complaint: document.getElementById("complaint"),
  email: document.getElementById("email"),
  settings: document.getElementById("settings"),
};

// --------- STATE ---------
let selectedFiles = [];
let lastResults = []; 
// Now contains: result_image_data_uri instead of result_image_url
let carouselIndex = 0;

// --------- THEME ---------
function setTheme(isDark) {
  if (isDark) document.documentElement.classList.add("dark");
  else document.documentElement.classList.remove("dark");
  localStorage.setItem("theme", isDark ? "dark" : "light");
}
const savedTheme = localStorage.getItem("theme");
if (savedTheme === "dark") setTheme(true);
else if (savedTheme === "light") setTheme(false);
else {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  setTheme(prefersDark);
}

themeToggle?.addEventListener("click", () => {
  const isDark = !document.documentElement.classList.contains("dark");
  setTheme(isDark);
});

// --------- NAV ---------
navButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    navButtons.forEach((b) => b.classList.remove("side-active"));
    btn.classList.add("side-active");
    const section = btn.dataset.section;
    Object.values(panels).forEach((p) => p?.classList.add("hidden"));
    panels[section]?.classList.remove("hidden");
  });
});
document.querySelector('.side-link[data-section="upload"]')?.click();

sidebarToggle?.addEventListener("click", () => sidebar.classList.toggle("hidden"));

// --------- FILE INPUT ---------
dropZone?.addEventListener("click", () => fileInput?.click());
fileInput?.addEventListener("change", (e) => {
  selectedFiles = Array.from(e.target.files || []);
  updateDropZoneText();
});
function updateDropZoneText() {
  const lines = [];
  if (!selectedFiles.length) {
    lines.push("Drag & Drop Images Here");
    lines.push("or click to select");
  } else {
    lines.push(`${selectedFiles.length} file(s) selected`);
    lines.push(selectedFiles.map(f => f.name).join(", "));
  }
  const ps = dropZone.querySelectorAll("p");
  ps.forEach((p, i) => p.textContent = lines[i] || "");
}
dropZone?.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("ring-2", "ring-blue-400");
});
dropZone?.addEventListener("dragleave", () => {
  dropZone.classList.remove("ring-2", "ring-blue-400");
});
dropZone?.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("ring-2", "ring-blue-400");
  const dtFiles = Array.from(e.dataTransfer.files || []);
  selectedFiles = selectedFiles.concat(dtFiles);
  updateDropZoneText();
});

// --------- LOADER ---------
function showLoader(text="Processing...") {
  loader?.classList.remove("hidden");
  if (loaderText) loaderText.textContent = text;
}
function hideLoader() {
  loader?.classList.add("hidden");
}

// --------- CLEAR ---------
clearBtn?.addEventListener("click", () => {
  selectedFiles = [];
  lastResults = [];
  resultsGrid.innerHTML = "";
  resultsSection.classList.add("hidden");
  if (totalCountEl) totalCountEl.textContent = "0";
  updateDropZoneText();
  potholeCountInput.value = "0";
  complaintText.textContent = "";
  emailStatus.textContent = "";
});

// --------- DETECTION ---------
detectBtn?.addEventListener("click", async () => {
  if (!selectedFiles.length) return alert("Please select some images first.");

  const form = new FormData();
  selectedFiles.forEach((f) => form.append("images", f));

  showLoader("Detecting potholes...");
  detectBtn.disabled = true;

  try {
    const resp = await fetch(`${BACKEND}/api/predict`, { method: "POST", body: form });
    const data = await resp.json();
    lastResults = data.results || [];
    renderResults(lastResults);

    const total = lastResults.reduce((s, r) => s + (r.count || 0), 0);
    totalCountEl.textContent = total;
    potholeCountInput.value = total;

    document.querySelector('.side-link[data-section="results"]')?.click();
  } catch (err) {
    console.error("Detection error:", err);
    alert("Detection failed: " + err);
  } finally {
    hideLoader();
    detectBtn.disabled = false;
  }
});


// --------- RENDER RESULTS (using base64 images now) ---------
function renderResults(results) {
  resultsGrid.innerHTML = "";

  if (!results?.length) {
    resultsGrid.innerHTML = `<div class="p-4 text-gray-500">No detections found.</div>`;
    return;
  }

  results.forEach((r, idx) => {
    const card = document.createElement("div");
    card.className = "rounded overflow-hidden shadow card";

    // *** IMPORTANT CHANGE ***
    // r.result_image_data_uri is now used instead of r.result_image_url
    card.innerHTML = `
      <img src="${r.result_image_data_uri}" class="w-full h-48 object-cover">
      <div class="p-3">
        <div class="font-semibold text-sm">${r.original_filename}</div>
        <div class="text-xs text-gray-500 mt-1">${r.count} potholes</div>
        <div class="mt-3 flex gap-2">
          <button data-idx="${idx}" class="view-btn btn-secondary small">View</button>
          <button data-idx="${idx}" class="download-btn btn-secondary small">Download</button>
        </div>
      </div>
    `;
    resultsGrid.appendChild(card);
  });

  Array.from(resultsGrid.querySelectorAll(".view-btn")).forEach((b) =>
    b.addEventListener("click", (e) => openCarousel(Number(e.currentTarget.dataset.idx)))
  );

  Array.from(resultsGrid.querySelectorAll(".download-btn")).forEach((b) =>
    b.addEventListener("click", (e) => {
      const idx = Number(e.currentTarget.dataset.idx);
      const dataUri = lastResults[idx].result_image_data_uri;
      downloadDataURI(dataUri, "pothole_result.jpg");
    })
  );

  resultsSection.classList.remove("hidden");
}

// Download base64 data URI as file
function downloadDataURI(dataUri, filename) {
  const a = document.createElement("a");
  a.href = dataUri;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// --------- CAROUSEL (uses base64 images now) ---------
function openCarousel(index = 0) {
  carouselIndex = index;
  carouselImg.src = lastResults[carouselIndex].result_image_data_uri;
  carouselModal.classList.remove("hidden");
}
closeCarousel?.addEventListener("click", () => carouselModal.classList.add("hidden"));
prevImg?.addEventListener("click", () => {
  carouselIndex = (carouselIndex - 1 + lastResults.length) % lastResults.length;
  carouselImg.src = lastResults[carouselIndex].result_image_data_uri;
});
nextImg?.addEventListener("click", () => {
  carouselIndex = (carouselIndex + 1) % lastResults.length;
  carouselImg.src = lastResults[carouselIndex].result_image_data_uri;
});
document.addEventListener("keydown", (e) => e.key === "Escape" && carouselModal.classList.add("hidden"));


// --------- COMPLAINT ---------
genComplaintBtn?.addEventListener("click", async () => {
  const payload = {
    pothole_count: Number(potholeCountInput.value || 0),
    road_name: roadNameInput.value || "",
    area: areaInput.value || "",
    city: cityInput.value || "",
    user_name: "Concerned Citizen",
    authority_name: "Municipal Commissioner",
    extra_details: extraDetailsInput.value || "",
  };

  showLoader("Generating complaint...");
  try {
    const resp = await fetch(`${BACKEND}/api/generate_complaint`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await resp.json();
    complaintText.textContent = data.complaint_text;

    emailSubjectInput.value = `Pothole complaint - ${roadNameInput.value || ""}`;
    emailBodyInput.value = data.complaint_text;
  } catch (err) {
    console.error(err);
    complaintText.textContent = "Error generating complaint.";
  } finally {
    hideLoader();
  }
});


// --------- PDF DOWNLOAD (uses pdf_data_uri now) ---------
downloadPdfBtn?.addEventListener("click", async () => {
  const text = complaintText.textContent;
  if (!text) return alert("Generate complaint first.");

  showLoader("Generating PDF...");
  try {
    const resp = await fetch(`${BACKEND}/api/generate_pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ complaint_text: text }),
    });
    const data = await resp.json();

    // *** IMPORTANT CHANGE ***
    downloadDataURI(data.pdf_data_uri, "complaint.pdf");
  } catch (err) {
    console.error("PDF error:", err);
    alert("PDF failed: " + err);
  } finally {
    hideLoader();
  }
});


// --------- EMAIL (now sends base64 images instead of disk URLs) ---------
sendEmailBtn?.addEventListener("click", async () => {
  if (!emailToInput.value) {
    emailStatus.textContent = "Enter recipient email.";
    return;
  }

  const payload = {
    to_email: emailToInput.value,
    subject: emailSubjectInput.value || "Pothole Complaint",
    body: emailBodyInput.value || complaintText.textContent || "",
    
    // *** IMPORTANT CHANGE ***
    // Send base64 images to backend instead of /static paths
    image_data_b64: lastResults.map(r => r.result_image_data_uri),

    // Keep legacy array empty (backend ignores if empty)
    image_urls: []
  };

  showLoader("Sending Email...");
  try {
    const resp = await fetch(`${BACKEND}/api/send_email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();

    emailStatus.textContent =
      data.status === "sent"
        ? "Email sent successfully ✅"
        : "Email error: " + (data.error || JSON.stringify(data));
  } catch (err) {
    console.error("Email error:", err);
    emailStatus.textContent = "Email failed: " + err.message;
  } finally {
    hideLoader();
  }
});


// --------- BACKEND HEALTH CHECK ---------
async function checkBackend() {
  try {
    await fetch(`${BACKEND}/`);
  } catch (err) {
    console.warn("Backend not reachable:", BACKEND || location.origin);
  }
}
checkBackend();

