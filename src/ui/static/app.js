// app.js
const formSeg = document.getElementById("formSeg");
const btnSeg = document.getElementById("btnSeg");
const statusSeg = document.getElementById("statusSeg");
const segResults = document.getElementById("segResults");
const exportBenchmarkSection = document.getElementById("exportBenchmarkSection");
const btnExportBenchmark = document.getElementById("btnExportBenchmark");
const exportBenchmarkOut = document.getElementById("exportBenchmarkOut");
const globalBestSection = document.getElementById("globalBestSection");
const globalBestOut = document.getElementById("globalBestOut");

const chkSegGWO = document.getElementById("chkSegGWO");
const chkSegWOA = document.getElementById("chkSegWOA");
const chkSegPSO = document.getElementById("chkSegPSO");
const chkSegOTSU = document.getElementById("chkSegOTSU");
const chkSegPA5 = document.getElementById("chkSegPA5");
const chkSegPA6 = document.getElementById("chkSegPA6");
const segK = document.getElementById("segK");
const segNAgents = document.getElementById("segNAgents");
const segNIters = document.getElementById("segNIters");
const segSeed = document.getElementById("segSeed");
const evalK = document.getElementById("evalK");
const evalSeedStart = document.getElementById("evalSeedStart");
const evalSeedCount = document.getElementById("evalSeedCount");
const evalNAgents = document.getElementById("evalNAgents");
const evalNIters = document.getElementById("evalNIters");

// BDS500 elements
const uploadSection = document.getElementById("uploadSection");
const bds500Section = document.getElementById("bds500Section");
const bds500Info = document.getElementById("bds500Info");
const imageFile = document.getElementById("imageFile");
const btnLoadBDS500 = document.getElementById("btnLoadBDS500");
const btnRandomBDS500 = document.getElementById("btnRandomBDS500");
const bds500List = document.getElementById("bds500List");
const bds500Split = document.getElementById("bds500Split");
const selectedImagePath = document.getElementById("selectedImagePath");
const selectedGTPath = document.getElementById("selectedGTPath");

// Benchmark Viewer elements
const benchmarkViewer = document.getElementById("benchmarkViewer");
const benchmarkViewerContent = document.getElementById("benchmarkViewerContent");
const btnCloseBenchmarkViewer = document.getElementById("btnCloseBenchmarkViewer");
const formBDS500Eval = document.getElementById('formBDS500Eval');
const btnEvalBDS500 = document.getElementById('btnEvalBDS500');
const evalProgress = document.getElementById('evalProgress');
const evalProgressText = document.getElementById('evalProgressText');
const evalProgressBar = document.getElementById('evalProgressBar');
const evalLogs = document.getElementById('evalLogs');
const evalResults = document.getElementById('evalResults');
const evalImagePath = document.getElementById('evalImagePath');
const evalGTPath = document.getElementById('evalGTPath');
const evalSelectedImageName = document.getElementById('evalSelectedImageName');
const evalSelectedImagePathDisplay = document.getElementById('evalSelectedImagePathDisplay');
const btnSyncEvalImage = document.getElementById('btnSyncEvalImage');
const formCXR = document.getElementById('formCXR');
const btnRunCXR = document.getElementById('btnRunCXR');
const statusCXR = document.getElementById('statusCXR');
const cxrResults = document.getElementById('cxrResults');
const cxrUploadSection = document.getElementById('cxrUploadSection');
const cxrDatasetSection = document.getElementById('cxrDatasetSection');
const cxrImageFile = document.getElementById('cxrImageFile');
const cxrSourceFilter = document.getElementById('cxrSourceFilter');
const cxrCaseSelect = document.getElementById('cxrCaseSelect');
const btnLoadCXR = document.getElementById('btnLoadCXR');
const cxrDatasetInfo = document.getElementById('cxrDatasetInfo');
const cxrPreset = document.getElementById('cxrPreset');
const cxrK = document.getElementById('cxrK');
const cxrSeed = document.getElementById('cxrSeed');
const cxrNAgents = document.getElementById('cxrNAgents');
const cxrNIters = document.getElementById('cxrNIters');
const btnDownloadCXRMask = document.getElementById('btnDownloadCXRMask');
const btnDownloadCXROverlay = document.getElementById('btnDownloadCXROverlay');
const btnSaveCXRHistory = document.getElementById('btnSaveCXRHistory');
const cxrGTSection = document.getElementById('cxrGTSection');
const cxrGTMaskFile = document.getElementById('cxrGTMaskFile');
const cxrGTHelpText = document.getElementById('cxrGTHelpText');
const cxrGTAutoStatus = document.getElementById('cxrGTAutoStatus');

let bds500Images = [];
let BENCHMARK_CHARTS = [];
let SEG_CONVERGENCE_CHART = null;
let CXR_CONVERGENCE_CHART = null;
let LAST_CXR_RESPONSE = null;
const HIDDEN_ALGOS = new Set(["OTSU"]);

function isVisibleAlgo(algo) {
  return !HIDDEN_ALGOS.has(String(algo || "").toUpperCase());
}

function visibleAlgoEntries(entries) {
  return entries.filter(([algo]) => isVisibleAlgo(algo));
}

// Histogram variables
let HIST_CHART = null;
let HIST_VISIBLE = {};       // { "GWO": true, "WOA": true, ... }
let HIST_THRESHOLDS = {};    // { "GWO": [..], "WOA": [..] }
let HIST_COLORS = {          // màu cố định, dễ phân biệt
  "HYBRID-PA5": "#16a34a",
  "HYBRID-PA6": "#0f766e",
  "GWO": "#2563eb",
  "WOA": "#7c3aed",
  "PSO": "#dc2626",
  "OTSU": "#f59e0b"
};

// Plugin vẽ vạch ngưỡng trên histogram
const thresholdLinesPlugin = {
  id: "thresholdLinesPlugin",
  afterDatasetsDraw(chart, args, pluginOptions) {
    if (!HIST_THRESHOLDS) return;
    const ctx = chart.ctx;
    const xScale = chart.scales.x;
    const yScale = chart.scales.y;
    if (!xScale || !yScale) return;

    Object.keys(HIST_THRESHOLDS).forEach(algo => {
      if (!HIST_VISIBLE[algo]) return;
      const thr = HIST_THRESHOLDS[algo] || [];
      const color = HIST_COLORS[algo] || "#0f172a";

      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;

      thr.forEach(v => {
        const x = xScale.getPixelForValue(v);
        if (!Number.isFinite(x)) return;
        ctx.beginPath();
        ctx.moveTo(x, yScale.top);
        ctx.lineTo(x, yScale.bottom);
        ctx.stroke();
      });

      ctx.restore();
    });
  }
};

function destroyBenchmarkCharts() {
  try {
    BENCHMARK_CHARTS.forEach(ch => {
      try { ch.destroy(); } catch (e) { }
    });
  } finally {
    BENCHMARK_CHARTS = [];
  }
}

function destroySegConvergenceChart() {
  if (SEG_CONVERGENCE_CHART) {
    try { SEG_CONVERGENCE_CHART.destroy(); } catch (e) { }
    SEG_CONVERGENCE_CHART = null;
  }
}

function openBenchmarkViewer() {
  console.log('openBenchmarkViewer called');
  console.log('benchmarkViewer:', benchmarkViewer);
  console.log('benchmarkViewerContent:', benchmarkViewerContent);

  if (!benchmarkViewer) {
    console.error('benchmarkViewer element not found!');
    return;
  }
  benchmarkViewer.classList.add("active");
  document.body.classList.add("no-scroll");
  console.log('Viewer opened, classes:', benchmarkViewer.className);
}

function closeBenchmarkViewer() {
  console.log('closeBenchmarkViewer called');
  destroyBenchmarkCharts();
  if (benchmarkViewerContent) benchmarkViewerContent.innerHTML = "";
  if (benchmarkViewer) benchmarkViewer.classList.remove("active");
  document.body.classList.remove("no-scroll");
}

if (btnCloseBenchmarkViewer) {
  btnCloseBenchmarkViewer.addEventListener("click", closeBenchmarkViewer);
}

let selectedBDS500Image = null;
let LAST_SEG_RESPONSE = null;
let CXR_CASES = [];

function sortSingleResults(entries) {
  return [...entries].sort((a, b) => Number(a[1]?.best_f ?? Infinity) - Number(b[1]?.best_f ?? Infinity));
}

function sortEvalSummaryRows(entries) {
  return [...entries].sort((a, b) => {
    const sa = a[1] || {};
    const sb = b[1] || {};
    return (
      Number(sb.fe_mean ?? Number.NEGATIVE_INFINITY) - Number(sa.fe_mean ?? Number.NEGATIVE_INFINITY) ||
      Number(sa.fe_sd ?? Number.POSITIVE_INFINITY) - Number(sb.fe_sd ?? Number.POSITIVE_INFINITY) ||
      Number(sb.boundary_dsc_mean ?? Number.NEGATIVE_INFINITY) - Number(sa.boundary_dsc_mean ?? Number.NEGATIVE_INFINITY) ||
      Number(sa.boundary_dsc_sd ?? Number.POSITIVE_INFINITY) - Number(sb.boundary_dsc_sd ?? Number.POSITIVE_INFINITY) ||
      Number(sb.ssim_mean ?? Number.NEGATIVE_INFINITY) - Number(sa.ssim_mean ?? Number.NEGATIVE_INFINITY) ||
      Number(sa.time_mean ?? Number.POSITIVE_INFINITY) - Number(sb.time_mean ?? Number.POSITIVE_INFINITY)
    );
  });
}

function syncKBetweenViews() {
  if (!segK || !evalK) return;
  evalK.value = segK.value || evalK.value;
}

function syncEvalConfigFromSegment() {
  syncKBetweenViews();
  if (segNAgents && evalNAgents) evalNAgents.value = segNAgents.value || evalNAgents.value;
  if (segNIters && evalNIters) evalNIters.value = segNIters.value || evalNIters.value;
  if (segSeed && evalSeedStart) evalSeedStart.value = segSeed.value || evalSeedStart.value;
  if (evalSeedCount && !evalSeedCount.value) evalSeedCount.value = "1";

  const evalAlgoBoxes = Array.from(document.querySelectorAll('#formBDS500Eval input[name="algorithms"]'));
  const segFlags = {
    GWO: !!chkSegGWO?.checked,
    WOA: !!chkSegWOA?.checked,
    PSO: !!chkSegPSO?.checked,
    OTSU: false,
    PA5: !!chkSegPA5?.checked,
    PA6: !!chkSegPA6?.checked,
  };
  evalAlgoBoxes.forEach(box => {
    if (box.value in segFlags) box.checked = segFlags[box.value];
  });
}

function setStatus(el, t) {
  if (el) el.textContent = t || "";
}

function destroyCXRConvergenceChart() {
  if (CXR_CONVERGENCE_CHART) {
    try { CXR_CONVERGENCE_CHART.destroy(); } catch (e) { }
    CXR_CONVERGENCE_CHART = null;
  }
}

function applyCXRPreset() {
  if (!cxrPreset) return;
  if (cxrPreset.value === 'FULL') {
    if (cxrK) cxrK.value = '8';
    if (cxrSeed) cxrSeed.value = '42';
    if (cxrNAgents) cxrNAgents.value = '20';
    if (cxrNIters) cxrNIters.value = '60';
  } else {
    if (cxrK) cxrK.value = '6';
    if (cxrSeed) cxrSeed.value = '42';
    if (cxrNAgents) cxrNAgents.value = '10';
    if (cxrNIters) cxrNIters.value = '25';
  }
}

async function loadCXRCases() {
  if (!cxrCaseSelect || !cxrSourceFilter) return;
  const source = cxrSourceFilter.value || 'all';
  cxrCaseSelect.innerHTML = '<option value="">Dang tai...</option>';
  if (cxrDatasetInfo) cxrDatasetInfo.textContent = '';
  const res = await fetch(`/api/cxr/cases?source=${encodeURIComponent(source)}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Khong tai duoc dataset CXR');
  const cases = data.cases || [];
  CXR_CASES = cases;
  cxrCaseSelect.innerHTML = cases.map(item => {
    const suffix = item.has_mask ? 'GT' : 'no GT';
    return `<option value="${item.case_id}">${item.case_id} (${item.source_name}, ${suffix})</option>`;
  }).join('');
  if (!cases.length) cxrCaseSelect.innerHTML = '<option value="">Khong co case</option>';
  if (cxrDatasetInfo) cxrDatasetInfo.textContent = `${data.dataset_root} - ${cases.length} cases`;
  updateCXRGTState();
}

function updateCXRGTState() {
  const source = document.querySelector('input[name="cxr_source"]:checked')?.value || 'upload';
  const caseId = cxrCaseSelect?.value || '';
  const selectedCase = CXR_CASES.find(item => item.case_id === caseId);
  const hasDatasetGT = source === 'dataset' && !!selectedCase?.has_mask;

  if (cxrGTMaskFile) {
    cxrGTMaskFile.disabled = source === 'dataset';
    if (source === 'dataset') cxrGTMaskFile.value = '';
  }
  if (cxrGTAutoStatus) {
    if (source === 'dataset') {
      cxrGTAutoStatus.style.display = 'block';
      cxrGTAutoStatus.textContent = hasDatasetGT
        ? `GT duoc tu dong lay tu dataset cho case ${caseId}.`
        : `Case ${caseId || ''} khong co GT trong dataset.`;
    } else {
      cxrGTAutoStatus.style.display = 'none';
      cxrGTAutoStatus.textContent = '';
    }
  }
  if (cxrGTHelpText) {
    cxrGTHelpText.textContent = source === 'dataset'
      ? 'Khi chon Dataset local, he thong tu kiem tra va tu dong dung GT co san neu case do co mask.'
      : 'GT mask la mask chuan de doi chieu voi ket qua doan phoi. Co GT thi tinh duoc DSC va IoU, khong co GT van chay duoc nhung chi xem FE, PSNR, SSIM va QC.';
  }
}

function renderCXRResults(data) {
  if (!cxrResults) return;
  destroyCXRConvergenceChart();
  const thresholds = Array.isArray(data.thresholds) ? data.thresholds.join(', ') : 'N/A';
  const qc = data.qc_info || {};
  const notes = Array.isArray(qc.notes) && qc.notes.length ? qc.notes.join('; ') : 'OK';
  const hasGT = data.dsc !== null && data.dsc !== undefined && data.iou !== null && data.iou !== undefined;
  const objectiveName = qc.objective_name || data.config?.objective_name || 'CXR-FE-shape';
  cxrResults.innerHTML = `
    <div class="results-section">
      <div class="results-note" style="margin-bottom:12px;"><strong>CXR Demo</strong> dùng PA5, objective ${objectiveName}, share_interval=10.</div>
      <div class="detail-images-grid-large">
        <div class="detail-image-item-large"><div class="detail-image-label-large">Original</div><div id="cxrOriginalPreview"></div></div>
        <div class="detail-image-item-large"><div class="detail-image-label-large">Preprocessed</div><div id="cxrPreprocessedPreview"></div></div>
        <div class="detail-image-item-large"><div class="detail-image-label-large">PA5 raw mask</div><div id="cxrRawMaskPreview"></div></div>
        <div class="detail-image-item-large"><div class="detail-image-label-large">PA5 raw overlay</div><div id="cxrRawOverlayPreview"></div></div>
        <div class="detail-image-item-large"><div class="detail-image-label-large">Final mask</div><div id="cxrMaskPreview"></div></div>
        <div class="detail-image-item-large"><div class="detail-image-label-large">Final overlay</div><div id="cxrOverlayPreview"></div></div>
        ${hasGT ? '<div class="detail-image-item-large"><div class="detail-image-label-large">GT mask</div><div id="cxrGTMaskPreview"></div></div>' : ''}
        ${hasGT ? '<div class="detail-image-item-large"><div class="detail-image-label-large">GT overlay</div><div id="cxrGTOverlayPreview"></div></div>' : ''}
      </div>
      <div class="detail-section">
        <h4>Threshold list</h4>
        <div class="results-note">${thresholds}</div>
      </div>
      <div class="detail-section">
        <h4>Metrics</h4>
        <div class="cxr-metric-grid">
          <div class="cxr-metric-card"><span class="cxr-metric-label">FE</span><span class="cxr-metric-value">${formatValue(data.fe, 6)}</span></div>
          <div class="cxr-metric-card"><span class="cxr-metric-label">Objective</span><span class="cxr-metric-value">${formatValue(data.objective_score, 4)}</span></div>
          <div class="cxr-metric-card"><span class="cxr-metric-label">Shape</span><span class="cxr-metric-value">${formatValue(data.shape_score, 4)}</span></div>
          <div class="cxr-metric-card"><span class="cxr-metric-label">Raw DSC</span><span class="cxr-metric-value">${hasGT ? formatValue(data.raw_dsc, 4) : 'Khong co GT'}</span></div>
          <div class="cxr-metric-card"><span class="cxr-metric-label">Raw IoU</span><span class="cxr-metric-value">${hasGT ? formatValue(data.raw_iou, 4) : 'Khong co GT'}</span></div>
          <div class="cxr-metric-card"><span class="cxr-metric-label">DSC</span><span class="cxr-metric-value">${hasGT ? formatValue(data.dsc, 4) : 'Khong co GT'}</span></div>
          <div class="cxr-metric-card"><span class="cxr-metric-label">IoU</span><span class="cxr-metric-value">${hasGT ? formatValue(data.iou, 4) : 'Khong co GT'}</span></div>
          <div class="cxr-metric-card"><span class="cxr-metric-label">PSNR</span><span class="cxr-metric-value">${formatValue(data.psnr, 2)}</span></div>
          <div class="cxr-metric-card"><span class="cxr-metric-label">SSIM</span><span class="cxr-metric-value">${formatValue(data.ssim, 4)}</span></div>
          <div class="cxr-metric-card"><span class="cxr-metric-label">Time</span><span class="cxr-metric-value">${formatValue(data.time, 2, 's')}</span></div>
        </div>
      </div>
      <div class="detail-section">
        <h4>QC info</h4>
        <div class="cxr-metric-grid cxr-qc-grid">
          <div class="cxr-metric-card"><span class="cxr-metric-label">Components</span><span class="cxr-metric-value">${qc.num_components ?? 'N/A'}</span></div>
          <div class="cxr-metric-card"><span class="cxr-metric-label">Mask source</span><span class="cxr-metric-value">${qc.mask_source || 'N/A'}</span></div>
          <div class="cxr-metric-card"><span class="cxr-metric-label">Low confidence</span><span class="cxr-metric-value">${qc.low_confidence ? 'true' : 'false'}</span></div>
          <div class="cxr-metric-card cxr-span-all"><span class="cxr-metric-label">Areas</span><span class="cxr-metric-value cxr-wrap">${Array.isArray(qc.component_areas) ? qc.component_areas.join(', ') : 'N/A'}</span></div>
          <div class="cxr-metric-card cxr-span-all"><span class="cxr-metric-label">Notes</span><span class="cxr-metric-value cxr-wrap">${notes}</span></div>
        </div>
      </div>
      <div class="detail-section">
        <h4>Convergence curve</h4>
        <div class="detail-chart-container"><canvas id="cxrConvergenceChart"></canvas></div>
      </div>
    </div>
  `;
  if (btnDownloadCXRMask) {
    btnDownloadCXRMask.href = data.mask_url;
    btnDownloadCXRMask.style.display = 'inline-flex';
  }
  if (btnDownloadCXROverlay) {
    btnDownloadCXROverlay.href = data.overlay_url;
    btnDownloadCXROverlay.style.display = 'inline-flex';
  }
  [
    ['cxrOriginalPreview', data.original_url],
    ['cxrPreprocessedPreview', data.preprocessed_url],
    ['cxrRawMaskPreview', data.raw_mask_url],
    ['cxrRawOverlayPreview', data.raw_overlay_url],
    ['cxrMaskPreview', data.mask_url],
    ['cxrOverlayPreview', data.overlay_url],
    ['cxrGTMaskPreview', data.gt_mask_url],
    ['cxrGTOverlayPreview', data.gt_overlay_url],
  ].forEach(([id, url]) => {
    const el = document.getElementById(id);
    if (!el || !url) return;
    fetch(url).then(r => r.json()).then(payload => {
      const dataUrl = payload.data_url || '';
      el.innerHTML = dataUrl ? `<img src="${dataUrl}" alt="${id}" style="max-width:100%; height:auto;">` : 'Khong tai duoc anh';
      if (id === 'cxrMaskPreview' && btnDownloadCXRMask && dataUrl) btnDownloadCXRMask.href = dataUrl;
      if (id === 'cxrOverlayPreview' && btnDownloadCXROverlay && dataUrl) btnDownloadCXROverlay.href = dataUrl;
    }).catch(() => { el.textContent = 'Khong tai duoc anh'; });
  });
  const canvas = document.getElementById('cxrConvergenceChart');
  const points = data.convergence?.points || [];
  if (canvas && points.length) {
    CXR_CONVERGENCE_CHART = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: points.map(p => p.iter),
        datasets: [{
          label: 'FE',
          data: points.map(p => p.fe),
          borderColor: '#16a34a',
          backgroundColor: 'rgba(22,163,74,0.08)',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.15,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { title: { display: true, text: 'Iteration' } },
          y: { title: { display: true, text: 'FE' } }
        }
      }
    });
  }
}

// Clear logs button
const btnClearLogs = document.getElementById("btnClearLogs");
if (btnClearLogs) {
  btnClearLogs.addEventListener("click", () => {
    if (statusSeg) {
      statusSeg.textContent = "Sẵn sàng...";
    }
  });
}

// Handle image source selection
document.querySelectorAll('input[name="image_source"]').forEach(radio => {
  radio.addEventListener('change', (e) => {
    if (e.target.value === 'upload') {
      uploadSection.style.display = 'block';
      bds500Section.style.display = 'none';
      bds500Info.style.display = 'none';
      imageFile.required = true;
    } else {
      uploadSection.style.display = 'none';
      bds500Section.style.display = 'block';
      bds500Info.style.display = 'inline';
      imageFile.required = false;
    }
  });
});

document.querySelectorAll('input[name="cxr_source"]').forEach(radio => {
  radio.addEventListener('change', async (e) => {
    const isDataset = e.target.value === 'dataset';
    if (cxrUploadSection) cxrUploadSection.style.display = isDataset ? 'none' : 'block';
    if (cxrDatasetSection) cxrDatasetSection.style.display = isDataset ? 'block' : 'none';
    if (cxrImageFile) cxrImageFile.required = !isDataset;
    updateCXRGTState();
    if (isDataset && cxrCaseSelect && cxrCaseSelect.options.length === 0) {
      try { await loadCXRCases(); } catch (err) { if (statusCXR) statusCXR.textContent = err.message; }
    }
  });
});

if (cxrPreset) cxrPreset.addEventListener('change', applyCXRPreset);
if (btnLoadCXR) btnLoadCXR.addEventListener('click', async () => {
  try {
    btnLoadCXR.disabled = true;
    await loadCXRCases();
  } catch (err) {
    alert(err.message || err);
  } finally {
    btnLoadCXR.disabled = false;
  }
});
if (cxrSourceFilter) cxrSourceFilter.addEventListener('change', async () => {
  try { await loadCXRCases(); } catch (err) { if (statusCXR) statusCXR.textContent = err.message; }
});
if (cxrCaseSelect) cxrCaseSelect.addEventListener('change', updateCXRGTState);

if (formCXR) {
  formCXR.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (btnRunCXR) btnRunCXR.disabled = true;
    setStatus(statusCXR, 'Dang chay PA5 cho CXR...');
    try {
      const source = document.querySelector('input[name="cxr_source"]:checked')?.value || 'upload';
      const fd = new FormData(formCXR);
      if (source === 'upload') {
        fd.delete('case_id');
        if (!cxrImageFile?.files?.length) throw new Error('Vui long chon anh CXR');
      } else {
        fd.delete('image');
        const caseId = cxrCaseSelect?.value || '';
        if (!caseId) throw new Error('Vui long chon case_id');
        fd.set('case_id', caseId);
      }
      const res = await fetch('/api/cxr/segment', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'CXR segment failed');
      LAST_CXR_RESPONSE = data;
      renderCXRResults(data);
      setStatus(statusCXR, `Hoan thanh: ${data.run_name}`);
      loadHistory();
    } catch (err) {
      setStatus(statusCXR, `LOI: ${err.message || err}`);
    } finally {
      if (btnRunCXR) btnRunCXR.disabled = false;
    }
  });
}

if (btnSaveCXRHistory) {
  btnSaveCXRHistory.addEventListener('click', () => {
    if (LAST_CXR_RESPONSE?.run_name) {
      setStatus(statusCXR, `Da luu lich su: ${LAST_CXR_RESPONSE.run_name}`);
      loadHistory();
    } else {
      setStatus(statusCXR, 'Chua co ket qua CXR de luu.');
    }
  });
}

// Load BDS500 images
if (btnLoadBDS500) {
  btnLoadBDS500.addEventListener('click', async () => {
    const split = bds500Split.value;
    btnLoadBDS500.disabled = true;
    btnLoadBDS500.textContent = '⏳ Đang tải...';

    try {
      const res = await fetch(`/api/bds500/list?split=${split}`);
      const data = await res.json();

      if (!res.ok) throw new Error(data.error || 'Lỗi khi tải danh sách');

      bds500Images = data.images || [];
      displayBDS500List(bds500Images);
      btnLoadBDS500.textContent = `✓ Đã tải ${bds500Images.length} ảnh`;
    } catch (err) {
      alert(`Lỗi: ${err.message}`);
      btnLoadBDS500.textContent = '🔄 Tải danh sách';
    } finally {
      btnLoadBDS500.disabled = false;
    }
  });

  // Random select from BDS500
  btnRandomBDS500.addEventListener('click', async () => {
    const split = bds500Split.value;
    btnRandomBDS500.disabled = true;
    btnRandomBDS500.textContent = '⏳ Đang chọn...';

    try {
      const res = await fetch(`/api/bds500/list?split=${split}&limit=1&random=true`);
      const data = await res.json();

      if (!res.ok) throw new Error(data.error || 'Lỗi khi chọn ảnh');

      if (data.images && data.images.length > 0) {
        const img = data.images[0];
        selectBDS500Image(img);
        bds500Images = [img];
        displayBDS500List(bds500Images);

        // Mark as selected
        setTimeout(() => {
          const items = document.querySelectorAll('.bds500-item');
          if (items.length > 0) {
            items[0].classList.add('selected');
          }
        }, 100);

        btnRandomBDS500.textContent = `🎲 Đã chọn: ${img.name}`;
      }
    } catch (err) {
      alert(`Lỗi: ${err.message}`);
      btnRandomBDS500.textContent = '🎲 Chọn ngẫu nhiên';
    } finally {
      btnRandomBDS500.disabled = false;
    }
  });

  function displayBDS500List(images) {
    if (images.length === 0) {
      bds500List.innerHTML = '<div style="padding: 12px; text-align: center; color: #718096;">Không có ảnh</div>';
      return;
    }

    bds500List.innerHTML = images.map(img => `
    <div class="bds500-item" data-id="${img.id}" data-path="${img.path}" data-gt="${img.gt_path}">
      📷 ${img.name} ${img.has_gt ? '✓' : ''}
    </div>
  `).join('');

    // Add click handlers
    document.querySelectorAll('.bds500-item').forEach(item => {
      item.addEventListener('click', () => {
        const imgData = {
          id: item.dataset.id,
          name: item.textContent.trim(),
          path: item.dataset.path,
          gt_path: item.dataset.gt,
          has_gt: true
        };
        selectBDS500Image(imgData);

        // Update UI
        document.querySelectorAll('.bds500-item').forEach(i => i.classList.remove('selected'));
        item.classList.add('selected');
      });
    });
  }

  function selectBDS500Image(img) {
    selectedBDS500Image = img;
    selectedImagePath.value = img.path;
    selectedGTPath.value = img.gt_path || '';
    if (evalImagePath) evalImagePath.value = img.path || '';
    if (evalGTPath) evalGTPath.value = img.gt_path || '';
    if (evalSelectedImageName) evalSelectedImageName.value = img.name || img.id || '';
    if (evalSelectedImagePathDisplay) evalSelectedImagePathDisplay.value = img.path || '';

    // Show preview
    const preview = document.getElementById('bds500Preview');
    const previewImg = document.getElementById('bds500PreviewImg');
    const previewLabel = document.getElementById('bds500PreviewLabel');

    if (preview && previewImg && previewLabel) {
      // Load image via API
      fetch(`/api/image?path=${encodeURIComponent(img.path)}`)
        .then(res => res.json())
        .then(data => {
          if (data.data_url) {
            previewImg.src = data.data_url;
            previewLabel.textContent = img.name;
            preview.classList.add('show');
          }
        })
        .catch(err => {
          console.error('Error loading preview:', err);
        });
    }
  }
} // End if (btnLoadBDS500)

function syncEvalImageFromSegment() {
  const imagePath = (selectedImagePath?.value || '').trim();
  const gtPath = (selectedGTPath?.value || '').trim();
  const imageName = (selectedBDS500Image?.name || LAST_SEG_RESPONSE?.image_name || '').trim();

  if (!imagePath) {
    throw new Error('Chưa có ảnh BDS500 nào được chọn ở tab Phân đoạn');
  }
  if (!gtPath) {
    throw new Error('Ảnh hiện tại không có ground truth để đánh giá nhiều seed');
  }

  if (evalImagePath) evalImagePath.value = imagePath;
  if (evalGTPath) evalGTPath.value = gtPath;
  if (evalSelectedImageName) evalSelectedImageName.value = imageName || 'Ảnh đã chọn';
  if (evalSelectedImagePathDisplay) evalSelectedImagePathDisplay.value = imagePath;
}

if (btnSyncEvalImage) {
  btnSyncEvalImage.addEventListener('click', () => {
    try {
      syncEvalImageFromSegment();
      syncEvalConfigFromSegment();
      alert('Đã lấy ảnh và cấu hình từ tab Phân đoạn');
    } catch (err) {
      alert(err.message);
    }
  });
}

if (segK) {
  syncKBetweenViews();
  segK.addEventListener("input", syncKBetweenViews);
  segK.addEventListener("change", syncKBetweenViews);
}

[segK, segNAgents, segNIters, segSeed, chkSegGWO, chkSegWOA, chkSegPSO, chkSegPA5, chkSegPA6]
  .filter(Boolean)
  .forEach(el => {
    el.addEventListener("input", syncEvalConfigFromSegment);
    el.addEventListener("change", syncEvalConfigFromSegment);
  });


if (formSeg) {
  formSeg.addEventListener("submit", async (e) => {
    e.preventDefault();
    btnSeg.disabled = true;
    segResults.innerHTML = "";
    exportBenchmarkSection.style.display = "none";

    let logMessages = [];
    function addLog(msg, type = 'info') {
      const timestamp = new Date().toLocaleTimeString();
      const icon = type === 'error' ? '❌' : type === 'success' ? '✅' : type === 'warning' ? '⚠️' : '📋';
      logMessages.push(`[${timestamp}] ${icon} ${msg}`);
      setStatus(statusSeg, logMessages.join('\n'));
      statusSeg.scrollTop = statusSeg.scrollHeight;
    }

    addLog("Bắt đầu xử lý...");

    try {
      const imageSource = document.querySelector('input[name="image_source"]:checked').value;
      const fd = new FormData(formSeg);

      // Determine API endpoint
      let apiUrl = "/api/segment";

      if (imageSource === 'bds500') {
        if (!selectedBDS500Image) {
          throw new Error("Vui lòng chọn ảnh từ BDS500");
        }
        apiUrl = "/api/segment_bds500";
        addLog(`Ảnh từ BDS500: ${selectedBDS500Image.name}`);
        addLog(`Có ground truth - Boundary DSC sẽ được tính`, 'info');
      } else {
        const fileInput = document.getElementById('imageFile');
        if (!fileInput.files || fileInput.files.length === 0) {
          throw new Error("Vui lòng chọn ảnh");
        }
        addLog("Đang tải ảnh lên server...");
      }

      fd.set("run_gwo", chkSegGWO.checked ? "1" : "0");
      fd.set("run_woa", chkSegWOA.checked ? "1" : "0");
      fd.set("run_pso", chkSegPSO.checked ? "1" : "0");
      fd.set("run_otsu", "0");
      const hybridStrategies = [];
      if (chkSegPA5?.checked) hybridStrategies.push("PA5");
      if (chkSegPA6?.checked) hybridStrategies.push("PA6");
      fd.set("run_hybrid", hybridStrategies.length > 0 ? "1" : "0");
      fd.set("hybrid_strategies", hybridStrategies.join(","));
      fd.set("share_interval", "10");
      fd.set("k", segK?.value || "5");

      // Bỏ penalties
      fd.set("use_penalties", "0");
      fd.set("penalty_mode", "balanced");

      const algos = [];
      if (chkSegGWO.checked) algos.push("GWO");
      if (chkSegWOA.checked) algos.push("WOA");
      if (chkSegPSO.checked) algos.push("PSO");
      if (chkSegPA5?.checked) algos.push("HYBRID-PA5");
      if (chkSegPA6?.checked) algos.push("HYBRID-PA6");
      const segKValue = fd.get("k");

      addLog(`Thuật toán: ${algos.join(", ")}`);
      addLog(`Tham số: n_agents=${fd.get("n_agents")}, n_iters=${fd.get("n_iters")}, seed=${fd.get("seed")}`);
      addLog(`Cấu hình: HYBRID=[${hybridStrategies.join(", ")}], share_interval=${fd.get("share_interval")}, FE thuần + repair/sort`);

      addLog("Đang gửi request đến server...");
      const res = await fetch(apiUrl, { method: "POST", body: fd });

      addLog("Server đang xử lý...");
      addLog("⏳ Đang chạy thuật toán tối ưu...");

      const data = await res.json();
      if (!res.ok) throw new Error(data && data.error ? data.error : "error");

      LAST_SEG_RESPONSE = data;
      syncEvalConfigFromSegment();
      if (data?.config?.seed !== undefined && evalSeedStart) {
        evalSeedStart.value = String(data.config.seed);
      }

      addLog("Phân đoạn ảnh hoàn thành!", 'success');
      addLog(`Thời gian phân đoạn: ${data.segmentation_time.toFixed(2)}s`);
      addLog(`Thuật toán tốt nhất: ${data.best_overall_algo}`, 'success');
      addLog(`Entropy tốt nhất: ${(-data.best_overall_f).toFixed(6)}`);

      if (data.has_ground_truth) {
        addLog(`Ground truth có sẵn - Boundary DSC đã được tính`, 'info');
      }

      // Hiển thị kết quả từng thuật toán
      if (data.results) {
        addLog("--- Kết quả chi tiết ---");
        visibleAlgoEntries(Object.entries(data.results)).forEach(([algo, result]) => {
          const entropy = (-result.best_f).toFixed(6);
          const time = result.time.toFixed(2);
          addLog(`${algo}: Entropy=${entropy}, Time=${time}s`);
        });
      }

      displaySegmentationResults(data);

      // Hiển thị nút xuất benchmark
      exportBenchmarkSection.style.display = "block";

      if (data.benchmark && data.benchmark.length > 0) {
        addLog(`Benchmark đã chạy: ${data.benchmark.length} hàm, ${data.benchmark_time.toFixed(2)}s`, 'info');
      }

      addLog(`TẤT CẢ HOÀN THÀNH! Tổng thời gian: ${data.total_time.toFixed(2)}s`, 'success');
      loadHistory();
    } catch (err) {
      addLog(`LỖI: ${err.message || err}`, 'error');
    } finally {
      btnSeg.disabled = false;
    }
  });
} // End if (formSeg)

function displaySegmentationResults(data) {
  const results = data.results || {};
  const sortedResults = sortSingleResults(visibleAlgoEntries(Object.entries(results)));

  destroySegConvergenceChart();

  let html = '<div class="results-section">';
  html += `<div class="results-note" style="margin-bottom: 12px;"><strong>Phân đoạn đơn</strong> luôn xếp theo <strong>FE / Entropy</strong>. <strong>Boundary DSC</strong> ở đây là Dice trên biên BSDS500.</div>`;


  // Kết quả các thuật toán - GRID 4 COLUMNS với ảnh căn giữa
  html += '<div class="results-horizontal-container">';
  html += '<div class="results-horizontal-scroll">';

  sortedResults.forEach(([algo, result], index) => {
    const isBest = index === 0;

    const metrics = result.metrics || {};
    const hasMetrics = Object.keys(metrics).length > 0;
    const hasBoundaryDsc = metrics.boundary_dsc !== undefined;

    html += `
      <div class="result-card-horizontal ${isBest ? 'best-result' : ''}">
        ${isBest ? '<div class="best-badge">🏆 TỐT NHẤT</div>' : ''}
        <div class="result-header">
          <h3>${algo}</h3>
          <div class="rank">#${index + 1}</div>
        </div>
        <img src="${result.seg_data_url}" alt="${algo}" onclick="openImageModal(this.src)">
        <div class="result-metrics">
          <div class="metric">
            <span class="metric-label">Entropy:</span>
            <span class="metric-value">${(-result.best_f).toFixed(6)}</span>
          </div>
          <div class="metric">
            <span class="metric-label">Thời gian:</span>
            <span class="metric-value">${result.time.toFixed(2)}s</span>
          </div>
          ${hasMetrics && metrics.psnr !== undefined ? `
            <div class="metric">
              <span class="metric-label">PSNR:</span>
              <span class="metric-value">${metrics.psnr.toFixed(2)} dB</span>
            </div>
          ` : ''}
          ${hasMetrics && metrics.ssim !== undefined ? `
            <div class="metric">
              <span class="metric-label">SSIM:</span>
              <span class="metric-value">${metrics.ssim.toFixed(4)}</span>
            </div>
          ` : ''}
          ${hasBoundaryDsc ? `
            <div class="metric" style="grid-column: 1 / -1;">
              <span class="metric-label">Boundary DSC:</span>
              <span class="metric-value">${metrics.boundary_dsc.toFixed(4)}</span>
            </div>
          ` : ''}
          <div class="metric full-width">
            <span class="metric-label">Thresholds:</span>
            <span class="metric-value small">${result.thresholds.join(", ")}</span>
          </div>
        </div>
      </div>
    `;
  });

  html += '</div></div>';

  html += `
    <div class="algo-comparison-section" style="margin-top: 24px;">
      <h3>Bảng tổng hợp chỉ số</h3>
      <div class="algo-comparison-table-container">
        <table class="algo-comparison-table">
          <thead>
            <tr>
              <th>Thuật toán</th>
              <th>Entropy</th>
              <th>PSNR</th>
              <th>SSIM</th>
              <th>Boundary DSC</th>
              <th>Thời gian</th>
              <th>Ngưỡng</th>
            </tr>
          </thead>
          <tbody>
  `;

  sortedResults.forEach(([algo, result], index) => {
    const isBest = index === 0;
    const metrics = result.metrics || {};
    html += `
      <tr class="${isBest ? 'best-row' : ''}">
        <td class="algo-name-cell">${isBest ? '#1 ' : ''}${algo}</td>
        <td>${(-result.best_f).toFixed(6)}</td>
        <td>${metrics.psnr !== undefined ? metrics.psnr.toFixed(2) + ' dB' : 'N/A'}</td>
        <td>${metrics.ssim !== undefined ? metrics.ssim.toFixed(4) : 'N/A'}</td>
        <td>${metrics.boundary_dsc !== undefined ? metrics.boundary_dsc.toFixed(4) : 'N/A'}</td>
        <td>${result.time.toFixed(2)}s</td>
        <td>${Array.isArray(result.thresholds) ? result.thresholds.join(', ') : 'N/A'}</td>
      </tr>
    `;
  });

  html += `
          </tbody>
        </table>
      </div>
    </div>
  `;

  const hasHistorySeries = sortedResults.some(([, result]) => Array.isArray(result.best_series) && result.best_series.length > 0);
  if (hasHistorySeries) {
    html += `
      <div class="algo-comparison-section" style="margin-top: 24px;">
        <h3>Biểu đồ hội tụ của lần chạy hiện tại</h3>
        <div class="results-note" style="margin-bottom: 12px;">
          Phần này bổ sung theo thuyết minh để theo dõi quá trình hội tụ của từng thuật toán trong lần chạy đơn hiện tại.
        </div>
        <div class="chart-card" style="height: 360px;">
          <canvas id="segConvergenceChart"></canvas>
        </div>
      </div>
    `;
  }


  html += '</div>';
  segResults.innerHTML = html;

  if (hasHistorySeries) {
    const canvas = document.getElementById('segConvergenceChart');
    if (canvas) {
      SEG_CONVERGENCE_CHART = drawSegConvergenceChart(canvas, sortedResults);
    }
  }

  // Render histogram panel
  renderHistogramPanel(data);
}

// Modal để xem ảnh phóng to
function openImageModal(src) {
  const modal = document.createElement('div');
  modal.className = 'image-modal';
  modal.innerHTML = `
    <div class="image-modal-content">
      <span class="image-modal-close">&times;</span>
      <img src="${src}" alt="Zoomed image">
    </div>
  `;
  document.body.appendChild(modal);

  modal.onclick = function (e) {
    if (e.target === modal || e.target.className === 'image-modal-close') {
      document.body.removeChild(modal);
    }
  };
}

function drawSegConvergenceChart(canvas, sortedResults) {
  const ctx = canvas.getContext('2d');
  const colors = {
    'GWO': '#2563eb',
    'WOA': '#7c3aed',
    'PSO': '#dc2626',
    'OTSU': '#f59e0b',
    'HYBRID-PA5': '#16a34a',
    'PA5': '#16a34a',
  };

  const maxLen = sortedResults.reduce((m, [, r]) => Math.max(m, Array.isArray(r.best_series) ? r.best_series.length : 0), 0);
  const labels = Array.from({ length: maxLen }, (_, i) => i);
  const datasets = sortedResults
    .filter(([, r]) => Array.isArray(r.best_series) && r.best_series.length > 0)
    .map(([algo, r]) => ({
      label: algo,
      data: labels.map((_, i) => (i < r.best_series.length ? Number(-(r.best_series[i])) : null)),
      spanGaps: true,
      borderWidth: 2,
      pointRadius: 0,
      borderColor: colors[algo] || '#64748b',
      backgroundColor: 'transparent',
      tension: 0.15,
    }));

  if (!datasets.length) return null;

  return new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: true, position: 'top' },
        tooltip: {
          callbacks: {
            label: function (context) {
              return `${context.dataset.label}: Entropy ${Number(context.parsed.y).toFixed(6)}`;
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: 'Vòng lặp' }
        },
        y: {
          title: { display: true, text: 'Entropy tốt nhất' }
        }
      }
    }
  });
}

// Export benchmark handler
if (btnExportBenchmark) {
  btnExportBenchmark.addEventListener('click', async () => {
    try {
      btnExportBenchmark.disabled = true;
      btnExportBenchmark.textContent = '⏳ Đang xuất...';

      if (!LAST_SEG_RESPONSE || !LAST_SEG_RESPONSE.benchmark) {
        alert('Chưa có dữ liệu benchmark. Vui lòng chạy phân đoạn trước.');
        btnExportBenchmark.textContent = '📊 Xuất Benchmark';
        btnExportBenchmark.disabled = false;
        return;
      }

      const benchmarks = LAST_SEG_RESPONSE.benchmark;
      const results = LAST_SEG_RESPONSE.results;

      let html = '<div class="export-benchmark-content">';

      // Bảng 1: Kết quả Benchmark (hiển thị theo số hàm backend trả về)
      html += '<div class="export-section">';
      html += `<h3>📊 Bảng 1: Kết quả Benchmark (${benchmarks.length} hàm)</h3>`;
      html += '<div class="table-container">';
      html += '<table class="benchmark-table">';
      html += '<thead><tr><th>Hàm</th><th>Tên</th>';

      // Lấy danh sách thuật toán từ benchmark đầu tiên
      const firstBm = benchmarks.find(b => b.results && Object.keys(b.results).length > 0);
      const algoNames = firstBm ? Object.keys(firstBm.results) : [];

      algoNames.forEach(algo => {
        html += `<th>${algo}</th>`;
      });
      html += '</tr></thead><tbody>';

      benchmarks.forEach(bm => {
        if (bm.error) {
          html += `<tr><td><strong>F${bm.fun}</strong></td><td>${bm.fun_name}</td>`;
          html += `<td colspan="${algoNames.length}" class="error-cell">Error: ${bm.error}</td></tr>`;
        } else {
          html += `<tr><td><strong>F${bm.fun}</strong></td><td class="func-name">${bm.fun_name}</td>`;

          // Tìm giá trị tốt nhất
          const values = algoNames.map(algo => bm.results[algo]?.best_f || Infinity);
          const minValue = Math.min(...values);

          algoNames.forEach(algo => {
            const val = bm.results[algo]?.best_f;
            const isBest = val === minValue && val !== Infinity;
            const cellClass = isBest ? 'best-cell' : '';
            html += `<td class="${cellClass}">${val !== undefined ? val.toExponential(4) : 'N/A'}</td>`;
          });
          html += '</tr>';
        }
      });

      html += '</tbody></table></div>';
      html += '<div class="benchmark-info-text">';
      html += `<p><strong>Tổng số hàm:</strong> ${benchmarks.length}</p>`;
      html += `<p><strong>Dim:</strong> ${benchmarks[0]?.dim || 'N/A'}</p>`;
      html += `<p><strong>Thời gian benchmark:</strong> ${LAST_SEG_RESPONSE.benchmark_time?.toFixed(2) || 'N/A'}s</p>`;
      html += '</div>';
      html += '</div>';

      // Biểu đồ Convergence cho các hàm benchmark
      html += '<div class="export-section">';
      html += `<h3>📈 Biểu đồ Convergence (${benchmarks.length} hàm)</h3>`;
      html += '<div class="charts-grid">';

      benchmarks.forEach((bm, idx) => {
        if (!bm.error && bm.results) {
          html += `
            <div class="chart-card">
              <h4>F${bm.fun} - ${bm.fun_name}</h4>
              <canvas id="chartBm${idx}"></canvas>
            </div>
          `;
        }
      });

      html += '</div></div>';

      // Bảng 2 đã bị bỏ theo yêu cầu

      html += '</div>';

      // Mở viewer full-screen thay vì render trong trang cũ
      destroyBenchmarkCharts();
      if (benchmarkViewerContent) {
        benchmarkViewerContent.innerHTML = html;
      }
      openBenchmarkViewer();

      // Vẽ biểu đồ sau khi render HTML (large mode) - delay để DOM render xong
      setTimeout(() => {
        benchmarks.forEach((bm, idx) => {
          if (!bm.error && bm.results) {
            const canvas = document.getElementById(`chartBm${idx}`);
            if (canvas) {
              const chart = drawBenchmarkChart(canvas, bm, true);
              if (chart) BENCHMARK_CHARTS.push(chart);
            }
          }
        });
      }, 100);

      btnExportBenchmark.textContent = '✓ Đã xuất';
      setTimeout(() => {
        btnExportBenchmark.textContent = '📊 Xuất Benchmark';
        btnExportBenchmark.disabled = false;
      }, 2000);

    } catch (err) {
      console.error('Export benchmark error:', err);
      alert(`Lỗi: ${err.message}`);
      btnExportBenchmark.textContent = '📊 Xuất Benchmark';
      btnExportBenchmark.disabled = false;
    }
  });
}

// Function to draw benchmark chart
function drawBenchmarkChart(canvas, bm, large = false) {
  const ctx = canvas.getContext("2d");
  const results = bm.results;
  const keys = Object.keys(results).filter(isVisibleAlgo);

  // Tìm độ dài series lớn nhất
  const maxLen = keys.reduce((m, k) => Math.max(m, (results[k].series || []).length), 0);
  const labels = Array.from({ length: maxLen }, (_, i) => i);

  // Tạo datasets cho từng thuật toán
  const colors = {
    'GWO': '#f56565',
    'WOA': '#4299e1',
    'PSO': '#48bb78',
    'OTSU': '#ed8936',
    'HYBRID-PA5': '#9f7aea',
    'HYBRID-PA1': '#38b2ac',
    'HYBRID-PA2': '#ed64a6',
    'HYBRID-PA3': '#ecc94b',
    'HYBRID-PA4': '#667eea',
  };

  const EPS = 1e-12; // dùng cho log-scale (Chart.js không nhận y <= 0)

  const datasets = keys.map(k => {
    const s = results[k].series || [];
    const padded = labels.map((_, i) => {
      if (i >= s.length) return null;
      const v = s[i];
      if (v === null || v === undefined || Number.isNaN(v)) return null;
      // log-scale yêu cầu giá trị dương
      return (v > EPS) ? v : EPS;
    });

    return {
      label: k,
      data: padded,
      spanGaps: true,
      borderWidth: 2,
      pointRadius: 0,
      borderColor: colors[k] || '#718096',
      backgroundColor: 'transparent',
      tension: 0.1,
    };
  });

  return new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "nearest", intersect: false },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            boxWidth: large ? 14 : 12,
            font: { size: large ? 12 : 10 },
            padding: large ? 10 : 8,
          }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              if (context.parsed.y !== null) {
                label += context.parsed.y.toExponential(4);
              }
              return label;
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: "Iteration", font: { size: large ? 12 : 10 } },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: { font: { size: large ? 11 : 9 } }
        },
        y: {
          type: 'logarithmic',
          min: 1e-12, // khớp với EPS phía trên
          title: { display: true, text: "Best Fitness", font: { size: large ? 12 : 10 } },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            font: { size: large ? 11 : 9 },
            callback: function (value) {
              return Number(value).toExponential(2);
            }
          }
        }
      }
    }
  });
}


// ============================================================================
// TABS NAVIGATION
// ============================================================================

// Global function for inline onclick handlers
window.switchToTab = function (tabName) {
  console.log('Switching to tab:', tabName);

  // Update buttons
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const clickedBtn = document.querySelector(`[data-tab="${tabName}"]`);
  if (clickedBtn) {
    clickedBtn.classList.add('active');
  }

  // Update content
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  if (tabName === 'segment') {
    const tab = document.getElementById('tabSegment');
    if (tab) tab.classList.add('active');
  } else if (tabName === 'bds500eval') {
    const tab = document.getElementById('tabBDS500Eval');
    if (tab) tab.classList.add('active');
  } else if (tabName === 'cxr') {
    const tab = document.getElementById('tabCXR');
    if (tab) tab.classList.add('active');
  } else if (tabName === 'history') {
    const tab = document.getElementById('tabHistory');
    if (tab) tab.classList.add('active');
  }
};

// Also add event listeners (backup method)
const tabButtons = document.querySelectorAll('.tab-btn');
console.log('Found tab buttons:', tabButtons.length);

tabButtons.forEach(btn => {
  console.log('Adding click listener to tab:', btn.dataset.tab);
  btn.addEventListener('click', () => {
    const tabName = btn.dataset.tab;
    console.log('Tab clicked:', tabName);
    window.switchToTab(tabName);
  });
});

// ============================================================================
// BDS500 EVALUATION TAB
// ============================================================================

if (formBDS500Eval) {
  formBDS500Eval.addEventListener('submit', async (e) => {
    e.preventDefault();
    syncEvalConfigFromSegment();

    const selectedAlgos = Array.from(document.querySelectorAll('input[name="algorithms"]:checked'))
      .map(cb => cb.value)
      .filter(isVisibleAlgo);

    if (selectedAlgos.length === 0) {
      alert('Vui lòng chọn ít nhất 1 thuật toán');
      return;
    }

    btnEvalBDS500.disabled = true;
    evalProgress.style.display = 'block';
    evalResults.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">...</div>
      <div class="empty-text">Đang xử lý...</div>
    </div>
  `;

    let logMessages = [];
    function addEvalLog(msg) {
      logMessages.push(`[${new Date().toLocaleTimeString()}] ${msg}`);
      evalLogs.textContent = logMessages.join('\n');
      evalLogs.scrollTop = evalLogs.scrollHeight;
    }

    addEvalLog('Bắt đầu đánh giá 1 ảnh với nhiều seed...');

    try {
      syncEvalImageFromSegment();

      const fd = new FormData(formBDS500Eval);
      fd.set('algorithms', selectedAlgos.join(','));
      fd.set('image_path', evalImagePath?.value || '');
      fd.set('gt_path', evalGTPath?.value || '');
      fd.set('source_run_dir', LAST_SEG_RESPONSE?.run_dir || '');

      const k = fd.get('k');
      const seedStart = fd.get('seed_start');
      const seedCount = fd.get('seed_count');

      addEvalLog(`Ảnh đánh giá: ${evalSelectedImageName?.value || 'Ảnh đang chọn'}`);
      addEvalLog(`Thuật toán: ${selectedAlgos.join(', ')}`);
      addEvalLog(`Tham số: k=${k}, seed_bắt_đầu=${seedStart}, số_lượng_seed=${seedCount}, n_agents=${fd.get('n_agents')}, n_iters=${fd.get('n_iters')}`);
      addEvalLog('Đang gửi yêu cầu đến server...');

      evalProgressText.textContent = 'Đang xử lý trên server...';
      evalProgressBar.style.width = '30%';

      const res = await fetch('/api/eval_bds500', {
        method: 'POST',
        body: fd
      });

      addEvalLog('Đang nhận kết quả từ server...');
      evalProgressBar.style.width = '60%';

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Lỗi khi đánh giá');
      }

      addEvalLog('Đánh giá hoàn thành');
      addEvalLog(`Tổng thời gian: ${data.total_time.toFixed(2)}s`);
      addEvalLog(`Số seed: ${data.stats.n_seeds}`);
      addEvalLog(`Số lượt chạy thành công: ${data.stats.successful}`);
      addEvalLog(`Kết quả đã lưu tại: ${data.results_file}`);
      if (data.history_run_dir) {
        addEvalLog(`Đã thêm vào lịch sử chung: ${data.history_run_dir}`);
      }

      evalProgressText.textContent = 'Hoàn thành';
      evalProgressBar.style.width = '100%';
      displayBDS500Results(data);
      loadHistory();
    } catch (err) {
      addEvalLog(`LỖI: ${err.message}`);
      evalResults.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">X</div>
        <div class="empty-text">Lỗi: ${err.message}</div>
      </div>
    `;
    } finally {
      btnEvalBDS500.disabled = false;
    }
  });
} // End if (formBDS500Eval)

function displayBDS500Results(data) {
  const stats = data.stats || {};
  const summaryStats = data.summary_stats || {};
  const wilcoxonRows = (data.wilcoxon || []).filter(row => isVisibleAlgo(row.challenger) && isVisibleAlgo(row.base));
  const summaryEntries = visibleAlgoEntries(Object.entries(summaryStats));
  const sortedRows = sortEvalSummaryRows(summaryEntries);
  const wilcoxonBaseName = wilcoxonRows[0]?.base || 'PA5';

  const fmtP = (value) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
    return Number(value).toExponential(2);
  };

  const fmtDelta = (value) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
    const delta = Number(value);
    return `${delta >= 0 ? '+' : ''}${delta.toFixed(4)}`;
  };

  let html = '<div class="bds500-results-content">';

  if (LAST_SEG_RESPONSE && LAST_SEG_RESPONSE.results) {
    const singleRows = Object.entries(LAST_SEG_RESPONSE.results)
      .filter(([algo]) => isVisibleAlgo(algo))
      .sort((a, b) => a[1].best_f - b[1].best_f);

    html += `
      <div class="algo-comparison-section">
        <h3>KẾT QUẢ CHẠY ĐƠN</h3>
        <div class="algo-comparison-table-container">
          <table class="algo-comparison-table">
            <thead>
              <tr>
                <th>THUẬT TOÁN</th>
                <th>ENTROPY</th>
                <th>PSNR</th>
                <th>SSIM</th>
                <th>BOUNDARY DSC</th>
                <th>THỜI GIAN</th>
                <th>NGƯỠNG</th>
              </tr>
            </thead>
            <tbody>
    `;

    singleRows.forEach(([algo, result], index) => {
      const isBest = index === 0;
      const metrics = result.metrics || {};
      html += `
        <tr class="${isBest ? 'best-row' : ''}">
          <td class="algo-name-cell">${isBest ? '#1 ' : ''}${algo}</td>
          <td>${(-result.best_f).toFixed(6)}</td>
          <td>${metrics.psnr !== undefined ? metrics.psnr.toFixed(2) : 'N/A'}</td>
          <td>${metrics.ssim !== undefined ? metrics.ssim.toFixed(4) : 'N/A'}</td>
          <td>${metrics.boundary_dsc !== undefined ? metrics.boundary_dsc.toFixed(4) : 'N/A'}</td>
          <td>${result.time.toFixed(2)}s</td>
          <td>${Array.isArray(result.thresholds) ? result.thresholds.join(', ') : 'N/A'}</td>
        </tr>
      `;
    });

    html += `
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  html += `
    <div class="results-summary-section">
      <h3>Tom tat</h3>
      <div class="results-note" style="margin-bottom: 12px;">Phan tom tat nhanh tap trung vao <strong>Fuzzy Entropy (FE)</strong>, gom <strong>FE mean</strong> va <strong>FE SD</strong> tren nhieu seed.</div>
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-icon">ANH</div>
          <div class="summary-value">${stats.total_images || 0}</div>
          <div class="summary-label">Anh</div>
        </div>
        <div class="summary-card">
          <div class="summary-icon">SEED</div>
          <div class="summary-value">${stats.n_seeds || 0}</div>
          <div class="summary-label">Seed</div>
        </div>
        <div class="summary-card">
          <div class="summary-icon">RUN</div>
          <div class="summary-value">${stats.successful || 0}</div>
          <div class="summary-label">Luot chay thanh cong</div>
        </div>
        <div class="summary-card">
          <div class="summary-icon">TIME</div>
          <div class="summary-value">${data.total_time.toFixed(1)}s</div>
          <div class="summary-label">Tong thoi gian</div>
        </div>
      </div>
    </div>
  `;

  if (sortedRows.length > 0) {
    const bestFeMean = [...summaryEntries].sort((a, b) => b[1].fe_mean - a[1].fe_mean)[0];
    const bestFeSd = [...summaryEntries].sort((a, b) => a[1].fe_sd - b[1].fe_sd)[0];

    html += `
      <div class="results-summary-section">
        <h3>KẾT LUẬN NHANH</h3>
        <div class="summary-grid">
          <div class="summary-card">
            <div class="summary-icon">FE MEAN</div>
            <div class="summary-value" style="font-size: 1.45rem;">${bestFeMean?.[0] || 'N/A'}</div>
            <div class="summary-label">FE mean cao nhat: ${bestFeMean ? bestFeMean[1].fe_mean.toFixed(6) : 'N/A'}</div>
          </div>
          <div class="summary-card">
            <div class="summary-icon">FE SD</div>
            <div class="summary-value" style="font-size: 1.45rem;">${bestFeSd?.[0] || 'N/A'}</div>
            <div class="summary-label">FE SD thap nhat: ${bestFeSd ? bestFeSd[1].fe_sd.toFixed(6) : 'N/A'}</div>
          </div>
        </div>
        <div class="results-note" style="margin-top: 12px;">
          <strong>Cách đọc:</strong> <strong>FE mean</strong> càng cao càng tốt, còn <strong>FE SD</strong> càng thấp càng ổn định trên nhiều seed.
        </div>
      </div>
    `;

    html += `
      <div class="algo-comparison-section">
        <h3>Bang tong hop chinh (mean +/- SD)</h3>
        <div class="algo-comparison-table-container">
          <table class="algo-comparison-table">
            <thead>
              <tr>
                <th>THUẬT TOÁN</th>
                <th>FE</th>
                <th>BOUNDARY DSC</th>
                <th>PSNR</th>
                <th>SSIM</th>
                <th>THỜI GIAN</th>
                <th>SỐ LẦN CHẠY</th>
              </tr>
            </thead>
            <tbody>
    `;
    sortedRows.forEach(([algo, stat], index) => {
      const isBest = index === 0;
      html += `
        <tr class="${isBest ? 'best-row' : ''}">
          <td class="algo-name-cell">${isBest ? '#1 ' : ''}${algo}</td>
          <td><strong>${stat.fe_mean.toFixed(6)}</strong> +/- ${stat.fe_sd.toFixed(6)}</td>
          <td>${stat.boundary_dsc_mean.toFixed(4)} +/- ${stat.boundary_dsc_sd.toFixed(4)}</td>
          <td>${stat.psnr_mean.toFixed(2)} +/- ${stat.psnr_sd.toFixed(2)}</td>
          <td>${stat.ssim_mean.toFixed(4)} +/- ${stat.ssim_sd.toFixed(4)}</td>
          <td>${stat.time_mean.toFixed(2)} +/- ${stat.time_sd.toFixed(2)}</td>
          <td>${stat.n_runs}</td>
        </tr>
      `;
    });
    html += '</tbody></table></div></div>';
  }

  if (wilcoxonRows.length > 0) {
    const groupedWilcoxon = {};
    wilcoxonRows
      .filter(row => isVisibleAlgo(row.challenger) && isVisibleAlgo(row.base) && ['boundary_dsc', 'fe', 'psnr', 'ssim'].includes(String(row.metric || '').toLowerCase()))
      .forEach((row) => {
        const challenger = row.challenger;
        groupedWilcoxon[challenger] = groupedWilcoxon[challenger] || {};
        groupedWilcoxon[challenger][String(row.metric).toLowerCase()] = row;
      });

    html += `
      <div class="algo-comparison-section">
        <h3>Kiểm định Wilcoxon theo ảnh đang chọn</h3>
        <div class="results-note" style="margin-bottom: 12px;">
          Mỗi hàng là <strong>${wilcoxonBaseName}</strong> so với một thuật toán khác trên cùng ảnh, dùng nhiều seed. Bang chi hien thi <strong>Delta mean</strong> va <strong>p-value</strong> cua kiem dinh Wilcoxon.
        </div>
        <div class="results-note" style="margin-bottom: 12px;">
          <code>p &lt; 0.05</code>: khác biệt có ý nghĩa thống kế.
        </div>
        <div class="algo-comparison-table-container">
          <table class="algo-comparison-table">
            <thead>
              <tr>
                <th>${wilcoxonBaseName} vs</th>
                <th>FE Delta mean</th>
                <th>FE p</th>
                <th>Boundary DSC Delta mean</th>
                <th>Boundary DSC p</th>
                <th>PSNR Delta mean</th>
                <th>PSNR p</th>
                <th>SSIM Delta mean</th>
                <th>SSIM p</th>
              </tr>
            </thead>
            <tbody>
    `;
    Object.entries(groupedWilcoxon).forEach(([challenger, metrics]) => {
      const boundaryDscRow = metrics.boundary_dsc || null;
      const feRow = metrics.fe || null;
      const psnrRow = metrics.psnr || null;
      const ssimRow = metrics.ssim || null;
      html += `
        <tr>
          <td>${challenger}</td>
          <td>${fmtDelta(feRow?.delta_mean)}</td>
          <td>${fmtP(feRow?.pvalue)}</td>
          <td>${fmtDelta(boundaryDscRow?.delta_mean)}</td>
          <td>${fmtP(boundaryDscRow?.pvalue)}</td>
          <td>${fmtDelta(psnrRow?.delta_mean)}</td>
          <td>${fmtP(psnrRow?.pvalue)}</td>
          <td>${fmtDelta(ssimRow?.delta_mean)}</td>
          <td>${fmtP(ssimRow?.pvalue)}</td>
        </tr>
      `;
    });
    html += '</tbody></table></div></div>';
  }

  html += `
    <div class="files-info-section">
      <h3>Nơi trả kết quả</h3>
      <div class="file-info-grid">
        <div class="file-info-item">
          <strong>Thư mục:</strong>
          <code>${data.run_dir}</code>
        </div>
        <div class="file-info-item">
          <strong>Tệp kết quả:</strong>
          <code>${data.results_file}</code>
        </div>
        ${data.history_run_dir ? `
        <div class="file-info-item">
          <strong>Run lịch sử:</strong>
          <code>${data.history_run_dir}</code>
        </div>
        ` : ''}
      </div>
    </div>
  `;

  html += '</div>';
  evalResults.innerHTML = html;
  evalResults.dataset.lastEvalJson = JSON.stringify(data);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  // Load precomputed FE data on page load
  loadPrecomputedFE();
});


// ============================================================================
// HISTOGRAM PANEL
// ============================================================================

function renderHistogramPanel(data) {
  const hist = data.histogram;
  const results = data.results || {};
  if (!hist || !hist.bins || !hist.counts) return;

  // Build thresholds map theo thuật toán
  HIST_THRESHOLDS = {};
  HIST_VISIBLE = {};

  visibleAlgoEntries(Object.entries(results)).forEach(([algo, r]) => {
    if (r && Array.isArray(r.thresholds)) {
      HIST_THRESHOLDS[algo] = r.thresholds.map(x => Number(x)).filter(x => Number.isFinite(x));
      HIST_VISIBLE[algo] = true; // mặc định bật hết
    }
  });

  const algoList = Object.keys(HIST_THRESHOLDS);
  if (algoList.length === 0) return;

  // Tạo HTML panel
  let chips = "";
  algoList.forEach(algo => {
    chips += `
      <label class="chip">
        <input type="checkbox" class="histAlgoChk" data-algo="${algo}" checked>
        <span style="width:10px;height:10px;border-radius:99px;background:${HIST_COLORS[algo] || "#0f172a"};display:inline-block"></span>
        ${algo}
      </label>
    `;
  });

  const html = `
    <div class="hist-panel">
      <div class="hist-header">
        <div class="hist-title">📊 Phân tích Histogram & Ngưỡng (K = ${data.k || 10})</div>
        <div class="hist-controls">
          ${chips}
        </div>
      </div>

      <div class="hist-canvas-wrap">
        <canvas id="histChart"></canvas>
      </div>

      <div class="hist-actions">
        <button id="btnDownloadHist" class="btn-secondary">⬇️ Tải xuống ảnh biểu đồ</button>
      </div>
      
    </div>
  `;

  // Chèn panel vào cuối segResults
  const container = document.createElement("div");
  container.innerHTML = html;
  segResults.appendChild(container.firstElementChild);

  // Vẽ Chart.js
  const canvas = document.getElementById("histChart");
  if (!canvas) return;

  if (HIST_CHART) {
    try { HIST_CHART.destroy(); } catch (e) { }
    HIST_CHART = null;
  }

  HIST_CHART = new Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: hist.bins, // 0..255
      datasets: [{
        label: "Tần suất",
        data: hist.counts,
        borderWidth: 0,
        backgroundColor: 'rgba(102, 126, 234, 0.6)',
        borderColor: 'rgba(102, 126, 234, 1)',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          callbacks: {
            title: function (context) {
              return `Cường độ: ${context[0].label}`;
            },
            label: function (context) {
              return `Tần suất: ${context.parsed.y}`;
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: "Cường độ điểm ảnh (0-255)", font: { size: 12 } },
          ticks: { maxTicksLimit: 16 }
        },
        y: {
          title: { display: true, text: "Tần suất", font: { size: 12 } }
        }
      }
    },
    plugins: [thresholdLinesPlugin]
  });

  // làm canvas cao hơn cho dễ nhìn
  canvas.parentElement.style.height = "600px";

  // checkbox toggle
  document.querySelectorAll(".histAlgoChk").forEach(chk => {
    chk.addEventListener("change", () => {
      const algo = chk.getAttribute("data-algo");
      HIST_VISIBLE[algo] = chk.checked;
      if (HIST_CHART) HIST_CHART.update();
    });
  });

  // download PNG
  const btn = document.getElementById("btnDownloadHist");
  if (btn) {
    btn.addEventListener("click", () => {
      if (!HIST_CHART) return;
      const a = document.createElement("a");
      a.href = canvas.toDataURL("image/png");
      a.download = "histogram_thresholds.png";
      a.click();
    });
  }

}

function renderRegionAnalysis(data) {
  const container = document.getElementById("regionAnalysisContainer");
  if (!container) return;

  const results = data.results || {};
  const algoNames = Object.keys(results).filter(isVisibleAlgo);

  if (algoNames.length === 0) return;

  let html = '<div class="region-analysis-section">';
  html += '<h3>📊 Phân tích tỷ lệ pixel theo vùng ngưỡng</h3>';
  html += '<p class="region-analysis-desc">Xác minh ngưỡng có hợp lý không dựa trên tỷ lệ pixel trong mỗi vùng. Vùng có tỷ lệ < 1% được đánh dấu đỏ (có thể không hợp lý).</p>';

  algoNames.forEach(algo => {
    const result = results[algo];
    const analysis = result.region_analysis;

    if (!analysis || !analysis.regions) return;

    html += `<div class="region-analysis-algo">`;
    html += `<h4>${algo}</h4>`;
    html += `<div class="region-table-container">`;
    html += `<table class="region-table">`;
    html += `<thead><tr>`;
    html += `<th>Vùng</th>`;
    html += `<th>Khoảng cường độ</th>`;
    html += `<th>Số pixel</th>`;
    html += `<th>Tỷ lệ (%)</th>`;
    html += `<th>Đánh giá</th>`;
    html += `</tr></thead><tbody>`;

    analysis.regions.forEach(region => {
      const rowClass = region.is_small ? 'warning-row' : '';
      const status = region.is_small ? '⚠️ Quá nhỏ' : '✓ OK';
      const statusClass = region.is_small ? 'status-warning' : 'status-ok';

      html += `<tr class="${rowClass}">`;
      html += `<td><strong>Vùng ${region.region}</strong></td>`;
      html += `<td><code>${region.range}</code></td>`;
      html += `<td>${region.count.toLocaleString()}</td>`;
      html += `<td><strong>${region.ratio}%</strong></td>`;
      html += `<td class="${statusClass}">${status}</td>`;
      html += `</tr>`;
    });

    html += `</tbody></table>`;
    html += `<div class="region-summary">Tổng: ${analysis.total_pixels.toLocaleString()} pixels, K = ${analysis.k} ngưỡng</div>`;
    html += `</div></div>`;
  });

  html += '</div>';
  container.innerHTML = html;
}


// ============================================================================
// HISTORY TAB
// ============================================================================

let HISTORY_DATA = [];
let HISTORY_FILTERED = [];
let CURRENT_HISTORY_TYPE = 'all';

// Load history when tab is opened
window.addEventListener('DOMContentLoaded', () => {
  // Load history when switching to history tab
  const historyTab = document.querySelector('[data-tab="history"]');
  if (historyTab) {
    historyTab.addEventListener('click', () => {
      loadHistory();
    });
  }
});

async function loadHistory() {
  const historyList = document.getElementById('historyList');
  if (!historyList) return;

  historyList.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">⏳</div>
      <div class="empty-text">Đang tải lịch sử...</div>
    </div>
  `;

  try {
    const res = await fetch('/api/history/list');
    const data = await res.json();

    if (!res.ok) throw new Error(data.error || 'Lỗi khi tải lịch sử');

    HISTORY_DATA = data.runs || [];
    populateHistoryFilters();
    applyHistoryFilters();

  } catch (err) {
    console.error('Error loading history:', err);
    historyList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">❌</div>
        <div class="empty-text">Lỗi: ${err.message}</div>
      </div>
    `;
  }
}

function updateHistoryStats() {
  const runs = HISTORY_FILTERED.length > 0 ? HISTORY_FILTERED : HISTORY_DATA;
  document.getElementById('statTotalRuns').textContent = runs.length;
  document.getElementById('statGWO').textContent = runs.filter(run => run.mode === 'single').length;
  document.getElementById('statWOA').textContent = runs.filter(run => run.mode === 'single_image_multi_seed').length;
  document.getElementById('statPSO').textContent = runs.filter(run => run.mode === 'cxr_demo' || (run.algorithms || []).includes('PA5') || (run.algorithms || []).includes('HYBRID-PA5')).length;
  const statOTSU = document.getElementById('statOTSU');
  if (statOTSU) statOTSU.textContent = '0';
  document.getElementById('statHYBRID').textContent = runs.filter(run => (run.algorithms || []).some(algo => String(algo).includes('PA') || String(algo).includes('HYBRID'))).length;
}

function populateHistoryFilters() {
  const kValues = [...new Set(HISTORY_DATA.map(r => r.k).filter(v => v !== undefined && v !== null))].sort((a, b) => a - b);
  const kFilter = document.getElementById('historyFilterK');
  const previousValue = kFilter ? kFilter.value : '';

  // Clear existing options except "Tất cả"
  kFilter.innerHTML = '<option value="">Tất cả</option>';

  kValues.forEach(k => {
    const option = document.createElement('option');
    option.value = k;
    option.textContent = k;
    kFilter.appendChild(option);
  });

  if (previousValue && kValues.some(k => String(k) === String(previousValue))) {
    kFilter.value = previousValue;
  } else {
    kFilter.value = '';
  }
}

function formatHistoryTime(value) {
  return value ? new Date(value).toLocaleString('vi-VN') : 'N/A';
}

function formatHistoryPreview(run) {
  const preview = run.preview_metrics || {};
  if (run.mode === 'cxr_demo') {
    const fe = preview.fe !== null && preview.fe !== undefined ? Number(preview.fe).toFixed(6) : 'N/A';
    const dsc = preview.dsc !== null && preview.dsc !== undefined ? `, DSC ${Number(preview.dsc).toFixed(4)}` : '';
    const time = preview.time !== null && preview.time !== undefined ? `, ${Number(preview.time).toFixed(2)}s` : '';
    return { label: 'CXR', value: `${preview.case_id || run.image_id || 'N/A'} - FE ${fe}${dsc}${time}` };
  }
  if (run.mode === 'single_image_multi_seed') {
    const value = preview.fe_mean !== null && preview.fe_mean !== undefined
      ? Number(preview.fe_mean).toFixed(6)
      : 'N/A';
    const extra = preview.fe_sd !== null && preview.fe_sd !== undefined
      ? ` +/- ${Number(preview.fe_sd).toFixed(6)}`
      : '';
    return { label: 'FE mean tốt nhất', value: `${value}${extra}` };
  }

  return {
    label: 'FE tốt nhất',
    value: preview.fe !== null && preview.fe !== undefined ? Number(preview.fe).toFixed(6) : 'N/A',
  };
}

function buildHistoryGroups(filteredRuns, allRuns) {
  const allByName = new Map(allRuns.map(run => [run.run_name, run]));
  const groups = new Map();
  const runImageKey = (run) => `${run?.image_name || run?.image_id || ''}::${run?.k ?? ''}`;
  const singleByImageKey = new Map(
    allRuns
      .filter(run => run.mode === 'single')
      .map(run => [runImageKey(run), run])
  );
  const sameImageAndK = (a, b) => !!a && !!b && runImageKey(a) === runImageKey(b);

  function findSingleRunForMulti(run) {
    if (run.source_single_run_name && allByName.has(run.source_single_run_name)) {
      return allByName.get(run.source_single_run_name);
    }
    return singleByImageKey.get(runImageKey(run)) || null;
  }

  function ensureGroup(singleRunName, fallbackRun) {
    const key = singleRunName || fallbackRun.run_name;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        single: singleRunName ? allByName.get(singleRunName) || null : null,
        multiSeeds: [],
        orphans: [],
      });
    }
    return groups.get(key);
  }

  filteredRuns.forEach(run => {
    if (run.mode === 'single_image_multi_seed') {
      const sourceSingle = findSingleRunForMulti(run);
      const group = ensureGroup(sourceSingle?.run_name || run.source_single_run_name || null, run);
      if (sourceSingle) {
        group.single = sourceSingle;
      }
      if (!group.multiSeeds.some(item => item.run_name === run.run_name)) {
        group.multiSeeds.push(run);
      }
      return;
    }

    if (run.mode === 'single') {
      const group = ensureGroup(run.run_name, run);
      group.single = run;
      allRuns
        .filter(item => item.mode === 'single_image_multi_seed' && (
          item.source_single_run_name === run.run_name || sameImageAndK(item, run)
        ))
        .forEach(item => {
          if (!group.multiSeeds.some(child => child.run_name === item.run_name)) {
            group.multiSeeds.push(item);
          }
        });
      return;
    }

    ensureGroup(null, run).orphans.push(run);
  });

  return [...groups.values()].sort((a, b) => {
    const newestA = Math.max(...[a.single, ...a.multiSeeds, ...a.orphans].filter(Boolean).map(run => new Date(run.created_at || 0).getTime()));
    const newestB = Math.max(...[b.single, ...b.multiSeeds, ...b.orphans].filter(Boolean).map(run => new Date(run.created_at || 0).getTime()));
    return newestB - newestA;
  });
}

function renderHistoryRunRow(run, label) {
  const preview = formatHistoryPreview(run);
  const runTypeClass = run.mode === 'cxr_demo' ? 'algo-HYBRID' : (run.mode === 'single_image_multi_seed' ? 'algo-HYBRID' : 'algo-GWO');
  const runType = run.mode === 'cxr_demo' ? 'CXR Demo' : (run.mode === 'single_image_multi_seed' ? 'Multi-seed' : 'Single');
  const nSeeds = run.mode === 'single_image_multi_seed' ? (run.n_seeds || 'N/A') : 1;
  const visibleAlgorithms = Array.isArray(run.algorithms) ? run.algorithms.filter(isVisibleAlgo) : [];
  const algorithms = run.mode === 'cxr_demo' ? 'PA5' : (visibleAlgorithms.length ? visibleAlgorithms.join(', ') : 'N/A');
  const imageName = run.image_name || run.image_id || 'N/A';

  return `
    <div class="history-linked-run">
      <div class="history-linked-run-top">
        <span class="history-linked-label">${label}</span>
        <span class="history-value algo-badge ${runTypeClass}">${runType}</span>
      </div>
      <div class="history-linked-name">${run.run_name}</div>
      <div class="history-info-grid compact">
        <div class="history-info-item">
          <span class="history-label">Thời gian:</span>
          <span class="history-value small">${formatHistoryTime(run.created_at)}</span>
        </div>
        <div class="history-info-item">
          <span class="history-label">Số seed:</span>
          <span class="history-value">${nSeeds}</span>
        </div>
        <div class="history-info-item full-width">
          <span class="history-label">Ảnh:</span>
          <span class="history-value small">${imageName}</span>
        </div>
        <div class="history-info-item full-width">
          <span class="history-label">Best algo:</span>
          <span class="history-value">${run.mode === 'cxr_demo' ? 'PA5' : (run.preview_metrics?.best_algorithm || 'N/A')}</span>
        </div>
        <div class="history-info-item full-width">
          <span class="history-label">Thuật toán:</span>
          <span class="history-value small">${algorithms}</span>
        </div>
        <div class="history-info-item full-width">
          <span class="history-label">${preview.label}:</span>
          <span class="history-value">${preview.value}</span>
        </div>
      </div>
      <div class="history-run-actions">
        <button class="btn-view-detail" onclick="viewRunDetail('${run.run_name}')">👁️ Xem chi tiết</button>
        <button class="btn-secondary" onclick="exportHistoryRun('${run.run_name}')">📦 Export run</button>
      </div>
    </div>
  `;
}

function renderHistoryList() {
  const historyList = document.getElementById('historyList');
  if (!historyList) return;

  if (HISTORY_FILTERED.length === 0) {
    historyList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📂</div>
        <div class="empty-text">Không có lần chạy nào</div>
      </div>
    `;
    return;
  }

  const groups = buildHistoryGroups(HISTORY_FILTERED, HISTORY_DATA);
  let html = '<div class="history-grid">';

  groups.forEach(group => {
    const runs = [group.single, ...group.multiSeeds, ...group.orphans].filter(Boolean);
    const primary = group.single || group.multiSeeds[0] || group.orphans[0];
    const imageName = primary.image_name || primary.image_id || 'N/A';
    const latestTime = runs
      .map(run => new Date(run.created_at || 0).getTime())
      .reduce((max, value) => Math.max(max, value), 0);
    const title = group.single ? group.single.run_name : primary.run_name;
    const groupType = group.single && group.multiSeeds.length
      ? 'Single + Multi-seed'
      : (primary.mode === 'single_image_multi_seed' ? 'Multi-seed' : 'Single');
    const totalSeeds = runs.reduce((sum, run) => {
      return sum + (run.mode === 'single_image_multi_seed' ? Number(run.n_seeds || 0) : 1);
    }, 0);

    html += `
      <div class="history-card history-card-group" data-run="${primary.run_name}">
        <div class="history-card-header">
          <div class="history-card-title">${title}</div>
          <div class="history-card-time">${latestTime ? formatHistoryTime(new Date(latestTime).toISOString()) : 'N/A'}</div>
        </div>
        <div class="history-card-body">
          <div class="history-info-grid">
            <div class="history-info-item">
              <span class="history-label">Nhóm:</span>
              <span class="history-value algo-badge algo-HYBRID">${groupType}</span>
            </div>
            <div class="history-info-item">
              <span class="history-label">k:</span>
              <span class="history-value">${primary.k ?? 'N/A'}</span>
            </div>
            <div class="history-info-item">
              <span class="history-label">Số run:</span>
              <span class="history-value">${runs.length}</span>
            </div>
            <div class="history-info-item">
              <span class="history-label">Tổng seed:</span>
              <span class="history-value">${totalSeeds || 'N/A'}</span>
            </div>
            <div class="history-info-item full-width">
              <span class="history-label">Ảnh:</span>
              <span class="history-value small">${imageName}</span>
            </div>
          </div>
          <div class="history-linked-runs">
            ${group.single ? renderHistoryRunRow(group.single, 'Ảnh / run đơn') : ''}
            ${group.multiSeeds.map((run, index) => renderHistoryRunRow(run, `Ảnh nhiều seed ${index + 1}`)).join('')}
            ${group.orphans.map((run, index) => renderHistoryRunRow(run, `Run ${index + 1}`)).join('')}
          </div>
        </div>
      </div>
    `;
  });

  html += '</div>';
  historyList.innerHTML = html;
  return;

  {
    if (HISTORY_FILTERED.length === 0) {
      historyList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📂</div>
        <div class="empty-text">Không có lần chạy nào</div>
      </div>
    `;
      return;
    }

    let html = '<div class="history-grid">';
    const childCountBySingleRun = {};
    HISTORY_FILTERED.forEach(run => {
      if (run.source_single_run_name) {
        childCountBySingleRun[run.source_single_run_name] = (childCountBySingleRun[run.source_single_run_name] || 0) + 1;
      }
    });

    HISTORY_FILTERED.forEach(run => {
      const timestamp = run.created_at ? new Date(run.created_at).toLocaleString('vi-VN') : 'N/A';
      const preview = run.preview_metrics || {};
      const runType = run.mode === 'single_image_multi_seed' ? 'Multi-seed' : 'Single';
      const runTypeClass = run.mode === 'single_image_multi_seed' ? 'algo-HYBRID' : 'algo-GWO';
      const imageName = run.image_name || run.image_id || 'N/A';
      const algorithms = Array.isArray(run.algorithms) ? run.algorithms.join(', ') : 'N/A';
      const previewLabel = run.mode === 'single_image_multi_seed' ? 'FE mean tốt nhất' : 'FE tốt nhất';
      const previewValue = run.mode === 'single_image_multi_seed'
        ? (preview.fe_mean !== null && preview.fe_mean !== undefined ? Number(preview.fe_mean).toFixed(6) : 'N/A')
        : (preview.fe !== null && preview.fe !== undefined ? Number(preview.fe).toFixed(6) : 'N/A');
      const previewExtra = run.mode === 'single_image_multi_seed' && preview.fe_sd !== null && preview.fe_sd !== undefined
        ? ` +/- ${Number(preview.fe_sd).toFixed(6)}`
        : '';
      const nSeeds = run.mode === 'single_image_multi_seed' ? (run.n_seeds || 'N/A') : 1;
      const linkedSingleRun = run.source_single_run_name || '';
      const linkedChildren = childCountBySingleRun[run.run_name] || 0;

      html += `
      <div class="history-card" data-run="${run.run_name}">
        <div class="history-card-header">
          <div class="history-card-title">${run.run_name}</div>
          <div class="history-card-time">${timestamp}</div>
        </div>
        <div class="history-card-body">
          <div class="history-info-grid">
            <div class="history-info-item">
              <span class="history-label">Loại run:</span>
              <span class="history-value algo-badge ${runTypeClass}">${runType}</span>
            </div>
            <div class="history-info-item">
              <span class="history-label">k:</span>
              <span class="history-value">${run.k ?? 'N/A'}</span>
            </div>
            <div class="history-info-item">
              <span class="history-label">Số seed:</span>
              <span class="history-value">${nSeeds}</span>
            </div>
            <div class="history-info-item">
              <span class="history-label">Best algo:</span>
              <span class="history-value">${preview.best_algorithm || 'N/A'}</span>
            </div>
            <div class="history-info-item full-width">
              <span class="history-label">Ảnh:</span>
              <span class="history-value small">${imageName}</span>
            </div>
            <div class="history-info-item full-width">
              <span class="history-label">Thuật toán:</span>
              <span class="history-value small">${algorithms}</span>
            </div>
            ${linkedSingleRun ? `
              <div class="history-info-item full-width">
                <span class="history-label">Run đơn gốc:</span>
                <span class="history-value small">${linkedSingleRun}</span>
              </div>
            ` : ''}
            ${run.mode === 'single' && linkedChildren > 0 ? `
              <div class="history-info-item full-width">
                <span class="history-label">Multi-seed liên kết:</span>
                <span class="history-value small">${linkedChildren} run</span>
              </div>
            ` : ''}
            <div class="history-info-item full-width">
              <span class="history-label">${previewLabel}:</span>
              <span class="history-value">${previewValue}${previewExtra}</span>
            </div>
            ${Array.isArray(run.warnings) && run.warnings.length ? `
              <div class="history-info-item full-width">
                <span class="history-label">Cảnh báo:</span>
                <span class="history-value small">${run.warnings.join(' | ')}</span>
              </div>
            ` : ''}
          </div>
          <div style="display:flex; gap:10px; margin-top:14px;">
            <button class="btn-view-detail" onclick="viewRunDetail('${run.run_name}')">👁️ Xem chi tiết</button>
            <button class="btn-secondary" onclick="exportHistoryRun('${run.run_name}')">📦 Export run</button>
          </div>
        </div>
      </div>
    `;
    });

    html += '</div>';
    historyList.innerHTML = html;
  }
}

async function viewRunDetail(runName) {
  const modal = document.getElementById('runDetailModal');
  const body = document.getElementById('runDetailBody');
  const title = document.getElementById('runDetailTitle');

  if (!modal || !body || !title) return;

  // Show modal
  modal.classList.add('active');
  document.body.classList.add('no-scroll');

  // Show loading
  body.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">⏳</div>
      <div class="empty-text">Đang tải chi tiết...</div>
    </div>
  `;

  try {
    const res = await fetch(`/api/history/detail/${encodeURIComponent(runName)}`);
    const data = await res.json();

    if (!res.ok) throw new Error(data.error || 'Lỗi khi tải chi tiết');

    title.textContent = `Chi tiết: ${runName}`;

    // Render detail
    let html = '<div class="run-detail-content-inner">';

    // Config section
    html += '<div class="detail-section">';
    html += '<h4>⚙️ Cấu hình</h4>';
    html += '<div class="detail-grid">';

    const config = data.config || {};
    Object.entries(config).forEach(([key, value]) => {
      if (typeof value === 'object') {
        value = JSON.stringify(value);
      }
      html += `
        <div class="detail-item">
          <span class="detail-label">${key}:</span>
          <span class="detail-value">${value}</span>
        </div>
      `;
    });

    html += '</div></div>';

    // Best result section
    html += '<div class="detail-section">';
    html += '<h4>🏆 Kết quả tốt nhất</h4>';
    html += '<div class="detail-grid">';

    const best = data.best_result || {};
    if (best.best_f !== undefined) {
      html += `
        <div class="detail-item">
          <span class="detail-label">Best F:</span>
          <span class="detail-value">${best.best_f.toFixed(6)}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Entropy:</span>
          <span class="detail-value">${(-best.best_f).toFixed(6)}</span>
        </div>
      `;
    }

    if (best.thresholds) {
      html += `
        <div class="detail-item full-width">
          <span class="detail-label">Thresholds:</span>
          <span class="detail-value">${best.thresholds.join(', ')}</span>
        </div>
      `;
    }

    html += '</div></div>';

    // ?nh section
    if (data.images && Object.keys(data.images).length > 0) {
      html += '<div class="detail-section">';
      html += '<h4>🖼️ Ảnh</h4>';
      html += '<div class="detail-images-grid">';

      Object.entries(data.images).forEach(([type, path]) => {
        // Convert Windows path to URL-friendly format
        const urlPath = path.replace(/\\/g, '/');
        html += `
          <div class="detail-image-item">
            <div class="detail-image-label">${type}</div>
            <img src="/api/image?path=${encodeURIComponent(urlPath)}" 
                 alt="${type}" 
                 onclick="openImageModal(this.src)"
                 onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
            <div style="display:none; padding:20px; text-align:center; color:#999;">
              Không thể tải ảnh
            </div>
          </div>
        `;
      });

      html += '</div></div>';
    }

    // History chart section
    if (data.history && data.history.length > 0) {
      html += '<div class="detail-section">';
      html += '<h4>📈 Lịch sử tối ưu hóa</h4>';
      html += '<div class="detail-chart-container">';
      html += '<canvas id="detailHistoryChart"></canvas>';
      html += '</div></div>';
    }

    html += '</div>';
    body.innerHTML = html;

    // Draw history chart if available
    if (data.history && data.history.length > 0) {
      setTimeout(() => {
        drawDetailHistoryChart(data.history);
      }, 100);
    }

  } catch (err) {
    console.error('Error loading run detail:', err);
    body.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">❌</div>
        <div class="empty-text">Lỗi: ${err.message}</div>
      </div>
    `;
  }
}

function drawDetailHistoryChart(history) {
  const canvas = document.getElementById('detailHistoryChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  const labels = history.map((_, i) => i);
  const data = history.map(h => h.best_f);

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Best Fitness',
        data: data,
        borderColor: '#667eea',
        backgroundColor: 'rgba(102, 126, 234, 0.1)',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.1,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (context) {
              return `Best F: ${context.parsed.y.toFixed(6)} (Entropy: ${(-context.parsed.y).toFixed(6)})`;
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: 'Iteration' }
        },
        y: {
          title: { display: true, text: 'Best Fitness (minimize)' }
        }
      }
    }
  });
}

// Close run detail modal
const btnCloseRunDetail = document.getElementById('btnCloseRunDetail');
if (btnCloseRunDetail) {
  btnCloseRunDetail.addEventListener('click', () => {
    const modal = document.getElementById('runDetailModal');
    if (modal) {
      modal.classList.remove('active');
      document.body.classList.remove('no-scroll');
    }
  });
}

// Refresh history button
const btnRefreshHistory = document.getElementById('btnRefreshHistory');
if (btnRefreshHistory) {
  btnRefreshHistory.addEventListener('click', () => {
    loadHistory();
  });
}

// Export history button
const btnExportHistory = document.getElementById('btnExportHistory');
if (btnExportHistory) {
  btnExportHistory.addEventListener('click', async () => {
    try {
      btnExportHistory.disabled = true;
      btnExportHistory.textContent = '⏳ Đang export...';

      const res = await fetch('/api/history/export', { method: 'POST' });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Lỗi khi export');
      }

      // Download file
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'history_summary.json';
      a.click();
      window.URL.revokeObjectURL(url);

      btnExportHistory.textContent = '✓ Đã export';
      setTimeout(() => {
        btnExportHistory.textContent = '📥 Export JSON';
        btnExportHistory.disabled = false;
      }, 2000);

    } catch (err) {
      alert(`Lỗi: ${err.message}`);
      btnExportHistory.textContent = '📥 Export JSON';
      btnExportHistory.disabled = false;
    }
  });
}

// Filter handlers
const historyFilterAlgo = document.getElementById('historyFilterAlgo');
const historyFilterK = document.getElementById('historyFilterK');
const historySearch = document.getElementById('historySearch');

function applyHistoryFilters() {
  const algoFilter = historyFilterAlgo ? historyFilterAlgo.value.toUpperCase() : '';
  const kFilter = historyFilterK ? historyFilterK.value : '';
  const searchText = historySearch ? historySearch.value.toLowerCase() : '';

  HISTORY_FILTERED = HISTORY_DATA.filter(run => {
    const algoList = (run.algorithms || []).map(item => String(item).toUpperCase());
    const matchAlgo = !algoFilter || algoList.some(algo => algo.includes(algoFilter));
    const matchK = !kFilter || run.k == kFilter;
    const searchBase = `${run.run_name} ${run.image_name || ''} ${run.image_id || ''}`.toLowerCase();
    const matchSearch = !searchText || searchBase.includes(searchText);
    return matchAlgo && matchK && matchSearch;
  });

  updateHistoryStats();
  renderHistoryList();
}

if (historyFilterAlgo) {
  historyFilterAlgo.addEventListener('change', applyHistoryFilters);
}

if (historyFilterK) {
  historyFilterK.addEventListener('change', applyHistoryFilters);
}

if (historySearch) {
  historySearch.addEventListener('input', applyHistoryFilters);
}

async function exportHistoryRun(runName) {
  try {
    const res = await fetch(`/api/history/export/${encodeURIComponent(runName)}`);
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || 'Lỗi export run');
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${runName}.zip`;
    a.click();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert(`Lỗi: ${err.message}`);
  }
}

// Make viewRunDetail global
window.viewRunDetail = viewRunDetail;
window.exportHistoryRun = exportHistoryRun;

// Update switchToTab to load history when switching to history tab
const originalSwitchToTab = window.switchToTab;
window.switchToTab = function (tabName) {
  originalSwitchToTab(tabName);

  if (tabName === 'history') {
    loadHistory();
  }
};
