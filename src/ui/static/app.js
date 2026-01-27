// app.js
const formSeg = document.getElementById("formSeg");
const btnSeg = document.getElementById("btnSeg");
const statusSeg = document.getElementById("statusSeg");
const segResults = document.getElementById("segResults");
const benchmarkResultsSeg = document.getElementById("benchmarkResultsSeg");
const benchmarkSummary = document.getElementById("benchmarkSummary");
const benchmarkCharts = document.getElementById("benchmarkCharts");
const benchmarkInfo = document.getElementById("benchmarkInfo");

const chkSegGWO = document.getElementById("chkSegGWO");
const chkSegWOA = document.getElementById("chkSegWOA");
const chkSegPSO = document.getElementById("chkSegPSO");
const chkSegOTSU = document.getElementById("chkSegOTSU");
const chkSegHYB = document.getElementById("chkSegHYB");
const hybridStrategiesDiv = document.getElementById("hybridStrategiesDiv");

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

let bds500Images = [];
let selectedBDS500Image = null;

function setStatus(el, t) { 
  if (el) el.textContent = t || ""; 
}

// Check if elements exist before adding event listeners
if (chkSegHYB) {
  chkSegHYB.addEventListener("change", () => {
    if (hybridStrategiesDiv) {
      hybridStrategiesDiv.style.display = chkSegHYB.checked ? "block" : "none";
    }
  });
}

// Handle penalty toggle
const chkUsePenalties = document.getElementById("chkUsePenalties");
const penaltySettings = document.getElementById("penaltySettings");

if (chkUsePenalties && penaltySettings) {
  chkUsePenalties.addEventListener("change", () => {
    penaltySettings.style.display = chkUsePenalties.checked ? "block" : "none";
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

// Load BDS500 images
if (btnLoadBDS500) {
  btnLoadBDS500.addEventListener('click', async () => {
  const split = bds500Split.value;
  btnLoadBDS500.disabled = true;
  btnLoadBDS500.textContent = '⏳ Đang tải...';
  
  try {
    const res = await fetch(`/api/bds500/list?split=${split}&limit=50`);
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
}

if (formSeg) {
  formSeg.addEventListener("submit", async (e) => {
  e.preventDefault();
  btnSeg.disabled = true;
  segResults.innerHTML = "";
  benchmarkResultsSeg.style.display = "none";

  let logMessages = [];
  function addLog(msg) {
    logMessages.push(`[${new Date().toLocaleTimeString()}] ${msg}`);
    setStatus(statusSeg, logMessages.join('\n'));
    statusSeg.scrollTop = statusSeg.scrollHeight;
  }

  addLog("🚀 Bắt đầu xử lý...");

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
      addLog(`📷 Ảnh từ BDS500: ${selectedBDS500Image.name}`);
      addLog(`✓ Có ground truth - DICE sẽ được tính`);
    } else {
      const fileInput = document.getElementById('imageFile');
      if (!fileInput.files || fileInput.files.length === 0) {
        throw new Error("Vui lòng chọn ảnh");
      }
      addLog("📸 Đang tải ảnh lên server...");
    }
    
    fd.set("run_gwo", chkSegGWO.checked ? "1" : "0");
    fd.set("run_woa", chkSegWOA.checked ? "1" : "0");
    fd.set("run_pso", chkSegPSO.checked ? "1" : "0");
    fd.set("run_otsu", chkSegOTSU.checked ? "1" : "0");
    fd.set("run_hybrid", chkSegHYB.checked ? "1" : "0");
    
    const strategies = Array.from(document.querySelectorAll(".strategy-chk:checked"))
      .map(cb => cb.value).join(",");
    fd.set("hybrid_strategies", strategies);
    
    // Penalty settings
    fd.set("use_penalties", chkUsePenalties.checked ? "1" : "0");
    fd.set("penalty_mode", document.getElementById("penaltyMode").value);

    const algos = [];
    if (chkSegGWO.checked) algos.push("GWO");
    if (chkSegWOA.checked) algos.push("WOA");
    if (chkSegPSO.checked) algos.push("PSO");
    if (chkSegOTSU.checked) algos.push("OTSU");
    if (chkSegHYB.checked) algos.push(`HYBRID(${strategies})`);
    addLog(`📋 Thuật toán: ${algos.join(", ")}`);
    addLog(`⚙️ Tham số: n_agents=${fd.get("n_agents")}, n_iters=${fd.get("n_iters")}`);

    const res = await fetch(apiUrl, { method: "POST", body: fd });
    
    addLog("⏳ Server đang xử lý...");
    
    const data = await res.json();
    if (!res.ok) throw new Error(data && data.error ? data.error : "error");

    addLog("✅ Phân đoạn ảnh hoàn thành!");
    addLog(`⏱️ Thời gian phân đoạn: ${data.segmentation_time.toFixed(2)}s`);
    addLog(`🏆 Thuật toán tốt nhất: ${data.best_overall_algo}`);
    
    if (data.has_ground_truth) {
      addLog(`📊 Ground truth có sẵn - DICE đã được tính`);
    }

    displaySegmentationResults(data);

    if (data.benchmark && Array.isArray(data.benchmark)) {
      addLog("📊 Đang xử lý kết quả benchmark...");
      displayAllBenchmarks(data.benchmark, data.benchmark_time);
      addLog(`✅ Benchmark hoàn thành (${data.benchmark.length} hàm, ${data.benchmark_time.toFixed(2)}s)`);
    }

    addLog(`🎉 TẤT CẢ HOÀN THÀNH! Tổng thời gian: ${data.total_time.toFixed(2)}s`);
  } catch (err) {
    addLog(`❌ LỖI: ${err.message || err}`);
  } finally {
    btnSeg.disabled = false;
  }
});
} // End if (formSeg)

function displaySegmentationResults(data) {
  const results = data.results || {};
  
  // Sắp xếp theo best_f (tốt nhất trước - giá trị nhỏ nhất vì đang minimize)
  const sortedResults = Object.entries(results).sort((a, b) => a[1].best_f - b[1].best_f);
  
  let html = '<div class="results-section">';
  
  // Ảnh gốc
  html += `<div class="original-image">
    <img src="${data.gray_data_url}" alt="Original" onclick="openImageModal(this.src)">
    <div class="image-label">Ảnh gốc (Grayscale)</div>
    ${data.image_name ? `<div class="image-label" style="font-size: 11px; color: #a0aec0;">${data.image_name}</div>` : ''}
  </div>`;
  
  // Kết quả các thuật toán - GRID 4 COLUMNS
  html += '<div class="results-horizontal-container">';
  html += '<div class="results-horizontal-scroll">';
  
  sortedResults.forEach(([algo, result], index) => {
    const isBest = index === 0;
    const metrics = result.metrics || {};
    const hasMetrics = Object.keys(metrics).length > 0;
    const hasDice = metrics.dice !== undefined;
    
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
          ${hasDice ? `
            <div class="metric" style="grid-column: 1 / -1; background: #c6f6d5;">
              <span class="metric-label">DICE (Boundary):</span>
              <span class="metric-value" style="color: #22543d; font-size: 15px;">${metrics.dice.toFixed(4)}</span>
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
  
  html += '</div></div></div>';
  segResults.innerHTML = html;
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
  
  modal.onclick = function(e) {
    if (e.target === modal || e.target.className === 'image-modal-close') {
      document.body.removeChild(modal);
    }
  };
}

function displayAllBenchmarks(benchmarks, totalTime) {
  benchmarkResultsSeg.style.display = "block";
  
  benchmarkInfo.innerHTML = `
    <div class="info-item">📊 Tổng số hàm: <strong>${benchmarks.length}</strong></div>
    <div class="info-item">⏱️ Thời gian: <strong>${totalTime.toFixed(2)}s</strong></div>
    <div class="info-item">📏 Dim: <strong>${benchmarks[0]?.dim || 'N/A'}</strong></div>
  `;
  
  // Tạo bảng tổng hợp
  const firstBm = benchmarks.find(b => b.results && Object.keys(b.results).length > 0);
  const algoNames = firstBm ? Object.keys(firstBm.results) : [];
  
  let summaryHtml = '<div class="table-container">';
  summaryHtml += '<table class="benchmark-table">';
  summaryHtml += '<thead><tr><th>Hàm</th>';
  
  algoNames.forEach(algo => {
    summaryHtml += `<th>${algo}</th>`;
  });
  summaryHtml += '</tr></thead><tbody>';
  
  benchmarks.forEach(bm => {
    if (bm.error) {
      summaryHtml += `<tr><td><strong>F${bm.fun}</strong> ${bm.fun_name}</td>`;
      summaryHtml += `<td colspan="${algoNames.length}" class="error-cell">Error: ${bm.error}</td></tr>`;
    } else {
      summaryHtml += `<tr><td class="func-name"><strong>F${bm.fun}</strong> ${bm.fun_name}</td>`;
      
      // Tìm giá trị tốt nhất
      const values = algoNames.map(algo => bm.results[algo]?.best_f || Infinity);
      const minValue = Math.min(...values);
      
      algoNames.forEach(algo => {
        const val = bm.results[algo]?.best_f;
        const isBest = val === minValue;
        const cellClass = isBest ? 'best-cell' : '';
        summaryHtml += `<td class="${cellClass}">${val ? val.toExponential(4) : 'N/A'}</td>`;
      });
      summaryHtml += '</tr>';
    }
  });
  summaryHtml += '</tbody></table></div>';
  benchmarkSummary.innerHTML = summaryHtml;
  
  // Tạo biểu đồ cho 6 hàm đầu
  let chartsHtml = '<details open class="charts-details"><summary>📈 Biểu đồ Convergence (6 hàm đầu)</summary>';
  chartsHtml += '<div class="charts-grid">';
  
  benchmarks.slice(0, 6).forEach((bm, idx) => {
    if (!bm.error && bm.results) {
      chartsHtml += `
        <div class="chart-card">
          <h4>F${bm.fun} - ${bm.fun_name}</h4>
          <canvas id="chartBm${idx}" height="200"></canvas>
        </div>
      `;
    }
  });
  chartsHtml += '</div></details>';
  benchmarkCharts.innerHTML = chartsHtml;
  
  // Vẽ biểu đồ
  benchmarks.slice(0, 6).forEach((bm, idx) => {
    if (!bm.error && bm.results) {
      const canvas = document.getElementById(`chartBm${idx}`);
      if (canvas) {
        const ctx = canvas.getContext("2d");
        const results = bm.results;
        const keys = Object.keys(results);
        const maxLen = keys.reduce((m, k) => Math.max(m, (results[k].series || []).length), 0);
        const labels = Array.from({length: maxLen}, (_, i) => i);
        
        const datasets = keys.map(k => {
          const s = results[k].series || [];
          const padded = labels.map((_, i) => (i < s.length ? s[i] : null));
          return { 
            label: k, 
            data: padded, 
            spanGaps: true,
            borderWidth: 2,
            pointRadius: 0,
          };
        });
        
        new Chart(ctx, {
          type: "line",
          data: { labels, datasets },
          options: {
            responsive: true,
            maintainAspectRatio: true,
            animation: false,
            interaction: { mode: "nearest", intersect: false },
            plugins: { 
              legend: { display: true, position: 'top' },
              tooltip: { mode: 'index', intersect: false }
            },
            scales: {
              x: { 
                title: { display: true, text: "Iteration" },
                grid: { color: 'rgba(0,0,0,0.05)' }
              },
              y: { 
                title: { display: true, text: "Best Fitness" },
                grid: { color: 'rgba(0,0,0,0.05)' }
              }
            }
          }
        });
      }
    }
  });
}


// ============================================================================
// TABS NAVIGATION
// ============================================================================

// Global function for inline onclick handlers
window.switchToTab = function(tabName) {
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
  } else if (tabName === 'history') {
    const tab = document.getElementById('tabHistory');
    if (tab) tab.classList.add('active');
    if (typeof loadHistory === 'function') {
      loadHistory();
    }
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

const formBDS500Eval = document.getElementById('formBDS500Eval');
const btnEvalBDS500 = document.getElementById('btnEvalBDS500');
const evalProgress = document.getElementById('evalProgress');
const evalProgressText = document.getElementById('evalProgressText');
const evalProgressBar = document.getElementById('evalProgressBar');
const evalLogs = document.getElementById('evalLogs');
const evalResults = document.getElementById('evalResults');

if (formBDS500Eval) {
  formBDS500Eval.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Get selected algorithms
    const selectedAlgos = Array.from(document.querySelectorAll('input[name="algorithms"]:checked'))
    .map(cb => cb.value);
  
  if (selectedAlgos.length === 0) {
    alert('Vui lòng chọn ít nhất 1 thuật toán');
    return;
  }
  
  // Disable form
  btnEvalBDS500.disabled = true;
  evalProgress.style.display = 'block';
  evalResults.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">⏳</div>
      <div class="empty-text">Đang xử lý...</div>
    </div>
  `;
  
  let logMessages = [];
  function addEvalLog(msg) {
    logMessages.push(`[${new Date().toLocaleTimeString()}] ${msg}`);
    evalLogs.textContent = logMessages.join('\n');
    evalLogs.scrollTop = evalLogs.scrollHeight;
  }
  
  addEvalLog('🚀 Bắt đầu đánh giá BDS500...');
  
  try {
    const fd = new FormData(formBDS500Eval);
    fd.set('algorithms', selectedAlgos.join(','));
    
    const split = fd.get('split');
    const limit = fd.get('limit');
    const k = fd.get('k');
    const seed = fd.get('seed');
    
    addEvalLog(`📁 Dataset: ${split}, Limit: ${limit} ảnh`);
    addEvalLog(`🎯 Thuật toán: ${selectedAlgos.join(', ')}`);
    addEvalLog(`⚙️ Tham số: k=${k}, seed=${seed}, n_agents=${fd.get('n_agents')}, n_iters=${fd.get('n_iters')}`);
    addEvalLog('⏳ Đang gửi yêu cầu đến server...');
    
    evalProgressText.textContent = 'Đang xử lý trên server...';
    evalProgressBar.style.width = '30%';
    
    const res = await fetch('/api/eval_bds500', {
      method: 'POST',
      body: fd
    });
    
    addEvalLog('📥 Đang nhận kết quả từ server...');
    evalProgressBar.style.width = '60%';
    
    const data = await res.json();
    
    if (!res.ok) {
      throw new Error(data.error || 'Lỗi khi đánh giá');
    }
    
    addEvalLog('✅ Đánh giá hoàn thành!');
    addEvalLog(`⏱️ Tổng thời gian: ${data.total_time.toFixed(2)}s`);
    addEvalLog(`📊 Đã xử lý: ${data.stats.total_images} ảnh`);
    addEvalLog(`💾 Kết quả đã lưu tại: ${data.results_file}`);
    
    evalProgressText.textContent = 'Hoàn thành!';
    evalProgressBar.style.width = '100%';
    
    // Display results
    displayBDS500Results(data);
    
  } catch (err) {
    addEvalLog(`❌ LỖI: ${err.message}`);
    evalResults.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">❌</div>
        <div class="empty-text">Lỗi: ${err.message}</div>
      </div>
    `;
  } finally {
    btnEvalBDS500.disabled = false;
  }
});
} // End if (formBDS500Eval)

function displayBDS500Results(data) {
  const stats = data.stats;
  const diceStats = data.dice_stats || {};
  const feStats = data.fe_stats || {};
  
  let html = '<div class="bds500-results-content">';
  
  // Summary section
  html += `
    <div class="results-summary-section">
      <h3>📊 Tổng quan</h3>
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-icon">📷</div>
          <div class="summary-value">${stats.total_images}</div>
          <div class="summary-label">Tổng số ảnh</div>
        </div>
        <div class="summary-card">
          <div class="summary-icon">✅</div>
          <div class="summary-value">${stats.successful}</div>
          <div class="summary-label">Thành công</div>
        </div>
        <div class="summary-card">
          <div class="summary-icon">❌</div>
          <div class="summary-value">${stats.failed}</div>
          <div class="summary-label">Thất bại</div>
        </div>
        <div class="summary-card">
          <div class="summary-icon">⏱️</div>
          <div class="summary-value">${data.total_time.toFixed(1)}s</div>
          <div class="summary-label">Tổng thời gian</div>
        </div>
      </div>
    </div>
  `;
  
  // DICE comparison table
  if (Object.keys(diceStats).length > 0) {
    html += `
      <div class="algo-comparison-section">
        <h3>🎯 So sánh DICE Score</h3>
        <div class="algo-comparison-table-container">
          <table class="algo-comparison-table">
            <thead>
              <tr>
                <th>Thuật toán</th>
                <th>DICE (Mean)</th>
                <th>DICE (Std)</th>
                <th>DICE (Min)</th>
                <th>DICE (Max)</th>
                <th>Số ảnh</th>
              </tr>
            </thead>
            <tbody>
    `;
    
    // Sort by mean DICE (descending - higher is better)
    const sortedDiceAlgos = Object.entries(diceStats).sort((a, b) => 
      b[1].dice_mean - a[1].dice_mean
    );
    
    sortedDiceAlgos.forEach(([algo, stat], index) => {
      const isBest = index === 0;
      const rowClass = isBest ? 'best-row' : '';
      html += `
        <tr class="${rowClass}">
          <td class="algo-name-cell">
            ${isBest ? '🏆 ' : ''}${algo}
          </td>
          <td class="dice-cell"><strong>${stat.dice_mean.toFixed(4)}</strong></td>
          <td>${stat.dice_std.toFixed(4)}</td>
          <td>${stat.dice_min.toFixed(4)}</td>
          <td>${stat.dice_max.toFixed(4)}</td>
          <td>${stat.n_images}</td>
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
  
  // FE comparison table
  if (Object.keys(feStats).length > 0) {
    html += `
      <div class="algo-comparison-section">
        <h3>🔬 So sánh Fuzzy Entropy</h3>
        <div class="algo-comparison-table-container">
          <table class="algo-comparison-table">
            <thead>
              <tr>
                <th>Thuật toán</th>
                <th>FE (Mean)</th>
                <th>FE (Std)</th>
                <th>Thời gian (Mean)</th>
              </tr>
            </thead>
            <tbody>
    `;
    
    // Sort by mean FE (descending - higher is better)
    const sortedFeAlgos = Object.entries(feStats).sort((a, b) => 
      b[1].fe_mean - a[1].fe_mean
    );
    
    sortedFeAlgos.forEach(([algo, stat], index) => {
      const isBest = index === 0;
      const rowClass = isBest ? 'best-row' : '';
      html += `
        <tr class="${rowClass}">
          <td class="algo-name-cell">
            ${isBest ? '🏆 ' : ''}${algo}
          </td>
          <td class="fe-cell"><strong>${stat.fe_mean.toFixed(6)}</strong></td>
          <td>${stat.fe_std.toFixed(6)}</td>
          <td>${stat.time_mean.toFixed(2)}s</td>
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
  
  // Files info
  html += `
    <div class="files-info-section">
      <h3>💾 Kết quả đã lưu</h3>
      <div class="file-info-grid">
        <div class="file-info-item">
          <strong>📁 Thư mục:</strong>
          <code>${data.run_dir}</code>
        </div>
        <div class="file-info-item">
          <strong>📄 File kết quả:</strong>
          <code>${data.results_file}</code>
        </div>
      </div>
    </div>
  `;
  
  html += '</div>';
  evalResults.innerHTML = html;
}

// ============================================================================
// HISTORY TAB
// ============================================================================

const historyList = document.getElementById('historyList');
const btnRefreshHistory = document.getElementById('btnRefreshHistory');
const runDetailModal = document.getElementById('runDetailModal');
const runDetailBody = document.getElementById('runDetailBody');
const runDetailTitle = document.getElementById('runDetailTitle');

// Load history
async function loadHistory() {
  try {
    historyList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⏳</div>
        <div class="empty-text">Đang tải lịch sử...</div>
      </div>
    `;
    
    const res = await fetch('/api/runs/list');
    const data = await res.json();
    
    if (!res.ok) {
      throw new Error(data.error || 'Lỗi khi tải lịch sử');
    }
    
    if (data.runs.length === 0) {
      historyList.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📂</div>
          <div class="empty-text">Chưa có lịch sử chạy nào</div>
        </div>
      `;
      return;
    }
    
    // Render history items
    historyList.innerHTML = data.runs.map(run => `
      <div class="history-item" data-run="${run.run_name}">
        <div class="history-item-header">
          <div>
            <div class="history-item-title">📷 ${run.image_name}</div>
            <div class="history-item-time">🕐 ${formatTimestamp(run.timestamp)}</div>
          </div>
          <div class="history-item-actions">
            <button class="btn-view" onclick="viewRunDetail('${run.run_name}')">
              👁️ Xem
            </button>
            <button class="btn-delete" onclick="deleteRun('${run.run_name}', event)">
              🗑️ Xóa
            </button>
          </div>
        </div>
        
        <div class="history-item-info">
          <div class="history-info-item">
            <span class="history-info-label">Thuật toán tốt nhất</span>
            <span class="history-info-value">${run.best_algo}</span>
          </div>
          <div class="history-info-item">
            <span class="history-info-label">Entropy</span>
            <span class="history-info-value">${run.best_entropy.toFixed(6)}</span>
          </div>
          <div class="history-info-item">
            <span class="history-info-label">Thời gian</span>
            <span class="history-info-value">${run.total_time.toFixed(2)}s</span>
          </div>
          <div class="history-info-item">
            <span class="history-info-label">Tham số</span>
            <span class="history-info-value">k=${run.k}, n=${run.n_agents}, iter=${run.n_iters}</span>
          </div>
        </div>
        
        <div class="history-item-algos">
          ${run.algorithms.map(algo => `<span class="algo-badge">${algo}</span>`).join('')}
          ${run.use_penalties ? '<span class="algo-badge" style="background: #fef5e7; color: #7d6608;">🛡️ Penalties</span>' : ''}
        </div>
      </div>
    `).join('');
    
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

// Format timestamp
function formatTimestamp(timestamp) {
  if (!timestamp) return 'N/A';
  const date = new Date(timestamp);
  return date.toLocaleString('vi-VN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

// View run detail
async function viewRunDetail(runName) {
  try {
    runDetailTitle.textContent = `Chi tiết: ${runName}`;
    runDetailBody.innerHTML = `
      <div style="text-align: center; padding: 40px;">
        <div style="font-size: 48px;">⏳</div>
        <div style="margin-top: 16px; color: #718096;">Đang tải...</div>
      </div>
    `;
    runDetailModal.style.display = 'flex';
    
    const res = await fetch(`/api/runs/${runName}`);
    const data = await res.json();
    
    if (!res.ok) {
      throw new Error(data.error || 'Lỗi khi tải chi tiết');
    }
    
    // Render detail
    let html = '';
    
    // Summary section
    html += `
      <div class="run-detail-section">
        <h4>📊 Tóm tắt</h4>
        <div class="run-detail-grid">
          <div class="run-detail-item">
            <strong>Ảnh</strong>
            <span>${data.summary.image_name}</span>
          </div>
          <div class="run-detail-item">
            <strong>Thời gian</strong>
            <span>${formatTimestamp(data.summary.timestamp)}</span>
          </div>
          <div class="run-detail-item">
            <strong>Tổng thời gian</strong>
            <span>${data.summary.total_time.toFixed(2)}s</span>
          </div>
          <div class="run-detail-item">
            <strong>Thuật toán tốt nhất</strong>
            <span>${data.summary.best_overall_algo}</span>
          </div>
          <div class="run-detail-item">
            <strong>Entropy tốt nhất</strong>
            <span>${data.summary.best_overall_entropy.toFixed(6)}</span>
          </div>
        </div>
      </div>
    `;
    
    // Config section
    html += `
      <div class="run-detail-section">
        <h4>⚙️ Cấu hình</h4>
        <div class="run-detail-grid">
          <div class="run-detail-item">
            <strong>k (số ngưỡng)</strong>
            <span>${data.config.k}</span>
          </div>
          <div class="run-detail-item">
            <strong>n_agents</strong>
            <span>${data.config.n_agents}</span>
          </div>
          <div class="run-detail-item">
            <strong>n_iters</strong>
            <span>${data.config.n_iters}</span>
          </div>
          <div class="run-detail-item">
            <strong>seed</strong>
            <span>${data.config.seed !== null ? data.config.seed : 'Random'}</span>
          </div>
          <div class="run-detail-item">
            <strong>Penalties</strong>
            <span>${data.config.use_penalties ? `✅ ${data.config.penalty_mode}` : '❌ Không'}</span>
          </div>
        </div>
      </div>
    `;
    
    // Images section
    if (data.gray_data_url) {
      html += `
        <div class="run-detail-section">
          <h4>🖼️ Ảnh gốc</h4>
          <div class="run-images-grid">
            <div class="run-image-card">
              <h5>Grayscale</h5>
              <img src="${data.gray_data_url}" alt="Gray">
            </div>
          </div>
        </div>
      `;
    }
    
    // Algorithms results
    html += `
      <div class="run-detail-section">
        <h4>🎯 Kết quả các thuật toán</h4>
        <div class="run-algo-results">
    `;
    
    for (const [algoName, algoData] of Object.entries(data.algorithms)) {
      const best = algoData.best;
      html += `
        <div class="run-algo-card">
          <h5>${algoName}</h5>
          <div class="run-algo-info">
            <div class="run-detail-item">
              <strong>Entropy</strong>
              <span>${best.entropy.toFixed(6)}</span>
            </div>
            <div class="run-detail-item">
              <strong>Thời gian</strong>
              <span>${best.time.toFixed(2)}s</span>
            </div>
            ${best.metrics.psnr ? `
              <div class="run-detail-item">
                <strong>PSNR</strong>
                <span>${best.metrics.psnr.toFixed(2)} dB</span>
              </div>
            ` : ''}
            ${best.metrics.ssim ? `
              <div class="run-detail-item">
                <strong>SSIM</strong>
                <span>${best.metrics.ssim.toFixed(4)}</span>
              </div>
            ` : ''}
            ${best.metrics.dice ? `
              <div class="run-detail-item">
                <strong>DICE</strong>
                <span>${best.metrics.dice.toFixed(4)}</span>
              </div>
            ` : ''}
          </div>
          <div class="run-detail-item" style="margin-top: 12px;">
            <strong>Ngưỡng</strong>
            <span style="font-size: 12px;">[${best.thresholds.join(', ')}]</span>
          </div>
          ${algoData.seg_data_url ? `
            <div style="margin-top: 12px;">
              <img src="${algoData.seg_data_url}" alt="${algoName}" style="width: 100%; border-radius: 8px;">
            </div>
          ` : ''}
        </div>
      `;
    }
    
    html += `
        </div>
      </div>
    `;
    
    runDetailBody.innerHTML = html;
    
  } catch (err) {
    console.error('Error loading run detail:', err);
    runDetailBody.innerHTML = `
      <div style="text-align: center; padding: 40px;">
        <div style="font-size: 48px;">❌</div>
        <div style="margin-top: 16px; color: #e53e3e;">Lỗi: ${err.message}</div>
      </div>
    `;
  }
}

// Close run detail
function closeRunDetail() {
  runDetailModal.style.display = 'none';
}

// Delete run
async function deleteRun(runName, event) {
  event.stopPropagation();
  
  if (!confirm(`Bạn có chắc muốn xóa run "${runName}"?`)) {
    return;
  }
  
  try {
    const res = await fetch(`/api/runs/${runName}`, {
      method: 'DELETE'
    });
    
    const data = await res.json();
    
    if (!res.ok) {
      throw new Error(data.error || 'Lỗi khi xóa run');
    }
    
    alert(`✓ Đã xóa run: ${runName}`);
    loadHistory(); // Reload history
    
  } catch (err) {
    console.error('Error deleting run:', err);
    alert(`❌ Lỗi: ${err.message}`);
  }
}

// Refresh history button
btnRefreshHistory.addEventListener('click', loadHistory);

// Close modal when clicking outside
runDetailModal.addEventListener('click', (e) => {
  if (e.target === runDetailModal) {
    closeRunDetail();
  }
});

// Load history on page load (so it's ready when user clicks the tab)
document.addEventListener('DOMContentLoaded', () => {
  // Only load history if the element exists
  if (historyList && typeof loadHistory === 'function') {
    loadHistory();
  }
});
}