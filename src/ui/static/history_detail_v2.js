// history_detail_v2.js - Chi tiết lần chạy với Benchmark

function isMultiSeedHistoryRun(data) {
    return data?.mode === 'single_image_multi_seed' || data?.config?.mode === 'single_image_multi_seed';
}

function isCXRHistoryRun(data) {
    return data?.mode === 'cxr_demo' || data?.config?.mode === 'cxr_demo';
}

function isVisibleAlgo(algoName) {
    return String(algoName || '').toUpperCase() !== 'OTSU';
}

function formatMeanSd(meanValue, sdValue, digits) {
    if (meanValue === null || meanValue === undefined || Number.isNaN(Number(meanValue))) return 'N/A';
    const meanText = Number(meanValue).toFixed(digits);
    if (sdValue === null || sdValue === undefined || Number.isNaN(Number(sdValue))) return meanText;
    return `${meanText} +/- ${Number(sdValue).toFixed(digits)}`;
}

function formatValue(value, digits = 4, suffix = '') {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
    return `${Number(value).toFixed(digits)}${suffix}`;
}

function renderConfigGrid(items) {
    return `
      <div class="detail-section">
        <h4>⚙️ Cấu hình</h4>
        <div class="detail-grid">
          ${items.map(item => `
            <div class="detail-item">
              <span class="detail-label">${item.label}:</span>
              <span class="detail-value">${item.value ?? 'N/A'}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
}

function renderWarnings(warnings) {
    if (!Array.isArray(warnings) || warnings.length === 0) return '';
    return `
      <div class="detail-section">
        <h4>⚠️ Cảnh báo</h4>
        <div class="results-note">${warnings.join('<br>')}</div>
      </div>
    `;
}

function renderGraySection(grayPath) {
    if (!grayPath) return '';
    return `
      <div class="detail-section">
        <h4>🖼️ Ảnh gốc</h4>
        <div class="detail-original-image">
          <div id="grayImageContainer" data-path="${grayPath}"></div>
        </div>
      </div>
    `;
}

function renderSingleDetail(data) {
    const config = data.config || {};
    const summary = data.summary || {};
    const detail = data.detail || {};
    const algorithms = detail.algorithms || {};
    const ranking = (summary.ranking || []).filter(row => isVisibleAlgo(row.algorithm));
    const algoNames = Object.keys(algorithms).filter(isVisibleAlgo).sort((a, b) => {
        const fa = Number(algorithms[a]?.result?.best_f ?? Infinity);
        const fb = Number(algorithms[b]?.result?.best_f ?? Infinity);
        return fa - fb;
    });
    const visibleBestAlgo = isVisibleAlgo(summary.best_overall_algo) ? summary.best_overall_algo : (algoNames[0] || null);
    const visibleBestResult = visibleBestAlgo ? (algorithms[visibleBestAlgo]?.result || {}) : {};

    let html = '<div class="run-detail-content-inner">';
    html += renderWarnings(data.warnings);
    html += `
      <div class="detail-section">
        <h4>📊 Tóm tắt</h4>
        <div class="summary-cards">
          <div class="summary-card-detail">
            <div class="summary-card-label">Thuật toán tốt nhất</div>
            <div class="summary-card-value">${visibleBestAlgo || 'N/A'}</div>
          </div>
          <div class="summary-card-detail">
            <div class="summary-card-label">Entropy tốt nhất</div>
            <div class="summary-card-value">${formatValue(visibleBestResult.fe ?? visibleBestResult.entropy ?? summary.best_overall_entropy, 6)}</div>
          </div>
          <div class="summary-card-detail">
            <div class="summary-card-label">Tổng thời gian</div>
            <div class="summary-card-value">${formatValue(summary.total_time, 2, 's')}</div>
          </div>
        </div>
      </div>
    `;
    html += renderConfigGrid([
        { label: 'Tên ảnh', value: config.image_name || config.image_id },
        { label: 'Đường dẫn ảnh', value: config.image_path || 'uploaded' },
        { label: 'Thời gian chạy', value: config.created_at || summary.created_at },
        { label: 'k', value: config.k },
        { label: 'Seed', value: config.seed },
        { label: 'n_agents', value: config.n_agents },
        { label: 'n_iters', value: config.n_iters },
        { label: 'Objective', value: config.objective_name },
        { label: 'Penalty mode', value: config.penalty_mode ?? 'None' },
        { label: 'share_interval', value: config.share_interval },
    ]);
    html += renderGraySection(data.assets?.gray);

    if (algoNames.length > 0) {
        html += `
          <div class="detail-section">
            <h4>📋 Bảng tổng hợp thuật toán</h4>
            <div class="comparison-table-container">
              <table class="comparison-table">
                <thead>
                  <tr>
                    <th>Thuật toán</th>
                    <th>FE / Entropy</th>
                    <th>Boundary DSC</th>
                    <th>PSNR</th>
                    <th>SSIM</th>
                    <th>Thời gian</th>
                    <th>Ngưỡng</th>
                  </tr>
                </thead>
                <tbody>
                  ${algoNames.map((algoName) => {
                    const result = algorithms[algoName]?.result || {};
                    const isBest = visibleBestAlgo === algoName;
                    return `
                      <tr class="${isBest ? 'best-row' : ''}">
                        <td class="algo-name-cell">${isBest ? '#1 ' : ''}${algoName}</td>
                        <td>${formatValue(result.fe ?? result.entropy, 6)}</td>
                        <td>${formatValue(result.boundary_dsc, 4)}</td>
                        <td>${formatValue(result.psnr, 2)}</td>
                        <td>${formatValue(result.ssim, 4)}</td>
                        <td>${formatValue(result.time, 2, 's')}</td>
                        <td>${Array.isArray(result.thresholds) ? result.thresholds.join(', ') : 'N/A'}</td>
                      </tr>
                    `;
                  }).join('')}
                </tbody>
              </table>
            </div>
          </div>
        `;
    }

    algoNames.forEach((algoName, idx) => {
        const item = algorithms[algoName] || {};
        const result = item.result || {};
        const images = item.images || {};
        html += `
          <div class="detail-section">
            <h4>🔎 ${algoName}</h4>
            <div class="detail-grid">
              <div class="detail-item"><span class="detail-label">FE:</span><span class="detail-value">${formatValue(result.fe ?? result.entropy, 6)}</span></div>
              <div class="detail-item"><span class="detail-label">Boundary DSC:</span><span class="detail-value">${formatValue(result.boundary_dsc, 4)}</span></div>
              <div class="detail-item"><span class="detail-label">PSNR:</span><span class="detail-value">${formatValue(result.psnr, 2)}</span></div>
              <div class="detail-item"><span class="detail-label">SSIM:</span><span class="detail-value">${formatValue(result.ssim, 4)}</span></div>
              <div class="detail-item"><span class="detail-label">Time:</span><span class="detail-value">${formatValue(result.time, 2, 's')}</span></div>
              <div class="detail-item"><span class="detail-label">History iterations:</span><span class="detail-value">${item.history?.length ?? result.history_length ?? 0}</span></div>
              <div class="detail-item full-width"><span class="detail-label">Thresholds:</span><span class="detail-value">${Array.isArray(result.thresholds) ? result.thresholds.join(', ') : 'N/A'}</span></div>
            </div>
            <div class="detail-images-grid-large">
              ${images.segmented ? `<div class="detail-image-item-large"><div class="detail-image-label-large">${algoName} segmented</div><div class="seg-image-container" id="segImage${idx}" data-path="${images.segmented}"></div></div>` : ''}
              ${images.overlay ? `<div class="detail-image-item-large"><div class="detail-image-label-large">${algoName} overlay</div><div class="seg-image-container" id="overlayImage${idx}" data-path="${images.overlay}"></div></div>` : ''}
              ${images.histogram ? `<div class="detail-image-item-large"><div class="detail-image-label-large">${algoName} histogram</div><div class="seg-image-container" id="histImage${idx}" data-path="${images.histogram}"></div></div>` : ''}
            </div>
            ${item.history && item.history.length > 0 ? `<div class="detail-chart-container" style="margin-top:16px;"><canvas id="singleHistoryChart${idx}"></canvas></div>` : ''}
          </div>
        `;
    });

    if (data.detail?.histogram?.bins && data.detail?.histogram?.counts) {
        html += `
          <div class="detail-section">
            <h4>📊 Histogram & Ngưỡng</h4>
            <div style="margin-bottom: 16px; display: flex; gap: 16px; flex-wrap: wrap; align-items: center;">
              ${algoNames.map(algoName => `
                <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
                  <input type="checkbox" class="histogram-algo-checkbox-dynamic" data-algo="${algoName}" checked style="cursor:pointer;">
                  <span style="font-size:13px;">${algoName}</span>
                </label>
              `).join('')}
              <button onclick="downloadCurrentHistogram()" style="margin-left:auto; padding:8px 16px; background:#4c51bf; color:white; border:none; border-radius:6px; cursor:pointer;">Tải xuống ảnh biểu đồ</button>
            </div>
            <div style="background:white; border-radius:8px; padding:16px;">
              <div id="histogramImageContainer" style="text-align:center; min-height:400px; display:flex; align-items:center; justify-content:center;">
                <div style="color:#999;">⏳ Đang tải histogram...</div>
              </div>
            </div>
          </div>
        `;
    }

    if (Array.isArray(detail.benchmark) && detail.benchmark.length > 0) {
        html += '<div class="detail-section"><h4>📈 Benchmark</h4><div class="charts-grid-detail">';
        detail.benchmark.forEach((bm, idx) => {
            if (!bm.error && bm.results) {
                html += `<div class="chart-card-detail"><h5>F${bm.fun} - ${bm.fun_name}</h5><div class="chart-container-detail"><canvas id="benchmarkChart${idx}"></canvas></div></div>`;
            }
        });
        html += '</div></div>';
    }

    if (ranking.length > 0) {
        html += `
          <div class="detail-section">
            <h4>🏆 Ranking</h4>
            <div class="comparison-table-container">
              <table class="comparison-table">
                <thead><tr><th>Hạng</th><th>Thuật toán</th><th>FE</th><th>Boundary DSC</th><th>PSNR</th><th>SSIM</th><th>Time</th></tr></thead>
                <tbody>
                  ${ranking.map(row => `
                    <tr class="${row.rank === 1 ? 'best-row' : ''}">
                      <td>${row.rank}</td>
                      <td>${row.algorithm}</td>
                      <td>${formatValue(row.fe, 6)}</td>
                      <td>${formatValue(row.boundary_dsc, 4)}</td>
                      <td>${formatValue(row.psnr, 2)}</td>
                      <td>${formatValue(row.ssim, 4)}</td>
                      <td>${formatValue(row.time, 2, 's')}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        `;
    }

    html += '</div>';
    return html;
}

function renderCXRDetail(data) {
    const config = data.config || {};
    const summary = data.summary || {};
    const detail = data.detail || {};
    const metrics = detail.metrics || {};
    const thresholds = summary.thresholds || detail.thresholds?.thresholds || [];
    const convergencePoints = detail.convergence?.points || [];
    const qc = summary.qc_info || detail.qc_info || {};

    let html = '<div class="run-detail-content-inner">';
    html += renderWarnings(data.warnings);
    html += `
      <div class="detail-section">
        <h4>CXR Demo</h4>
        <div class="summary-cards">
          <div class="summary-card-detail"><div class="summary-card-label">Algorithm</div><div class="summary-card-value">PA5</div></div>
          <div class="summary-card-detail"><div class="summary-card-label">FE</div><div class="summary-card-value">${formatValue(summary.fe ?? metrics.fe, 6)}</div></div>
          <div class="summary-card-detail"><div class="summary-card-label">DSC</div><div class="summary-card-value">${formatValue(summary.dsc ?? metrics.dsc, 4)}</div></div>
          <div class="summary-card-detail"><div class="summary-card-label">Time</div><div class="summary-card-value">${formatValue(summary.time ?? metrics.time, 2, 's')}</div></div>
        </div>
      </div>
    `;
    html += renderConfigGrid([
        { label: 'mode', value: 'cxr_demo' },
        { label: 'case_id', value: config.case_id || summary.case_id },
        { label: 'dataset_root', value: config.dataset_root },
        { label: 'image_path', value: config.image_path },
        { label: 'mask_path', value: config.mask_path },
        { label: 'k', value: config.k },
        { label: 'seed', value: config.seed },
        { label: 'n_agents', value: config.n_agents },
        { label: 'n_iters', value: config.n_iters },
        { label: 'share_interval', value: config.share_interval },
        { label: 'objective', value: config.objective_name },
    ]);
    html += `
      <div class="detail-section">
        <h4>Images</h4>
        <div class="detail-images-grid-large">
          ${data.assets?.gray ? `<div class="detail-image-item-large"><div class="detail-image-label-large">Original</div><div class="seg-image-container" id="cxrGrayImage" data-path="${data.assets.gray}"></div></div>` : ''}
          ${data.assets?.preprocessed ? `<div class="detail-image-item-large"><div class="detail-image-label-large">Preprocessed</div><div class="seg-image-container" id="cxrPreImage" data-path="${data.assets.preprocessed}"></div></div>` : ''}
          ${data.assets?.mask ? `<div class="detail-image-item-large"><div class="detail-image-label-large">Lung mask</div><div class="seg-image-container" id="cxrMaskImage" data-path="${data.assets.mask}"></div></div>` : ''}
          ${data.assets?.overlay ? `<div class="detail-image-item-large"><div class="detail-image-label-large">Overlay</div><div class="seg-image-container" id="cxrOverlayImage" data-path="${data.assets.overlay}"></div></div>` : ''}
          ${data.assets?.gt_mask ? `<div class="detail-image-item-large"><div class="detail-image-label-large">GT mask</div><div class="seg-image-container" id="cxrGTImage" data-path="${data.assets.gt_mask}"></div></div>` : ''}
        </div>
      </div>
      <div class="detail-section">
        <h4>Thresholds</h4>
        <div class="results-note">${Array.isArray(thresholds) ? thresholds.join(', ') : 'N/A'}</div>
      </div>
      <div class="detail-section">
        <h4>Metrics</h4>
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-label">FE:</span><span class="detail-value">${formatValue(summary.fe ?? metrics.fe, 6)}</span></div>
          <div class="detail-item"><span class="detail-label">DSC:</span><span class="detail-value">${formatValue(summary.dsc ?? metrics.dsc, 4)}</span></div>
          <div class="detail-item"><span class="detail-label">IoU:</span><span class="detail-value">${formatValue(summary.iou ?? metrics.iou, 4)}</span></div>
          <div class="detail-item"><span class="detail-label">PSNR:</span><span class="detail-value">${formatValue(summary.psnr ?? metrics.psnr, 2)}</span></div>
          <div class="detail-item"><span class="detail-label">SSIM:</span><span class="detail-value">${formatValue(summary.ssim ?? metrics.ssim, 4)}</span></div>
          <div class="detail-item"><span class="detail-label">Time:</span><span class="detail-value">${formatValue(summary.time ?? metrics.time, 2, 's')}</span></div>
        </div>
      </div>
      <div class="detail-section">
        <h4>QC info</h4>
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-label">Components:</span><span class="detail-value">${qc.num_components ?? 'N/A'}</span></div>
          <div class="detail-item"><span class="detail-label">Low confidence:</span><span class="detail-value">${qc.low_confidence ? 'true' : 'false'}</span></div>
          <div class="detail-item full-width"><span class="detail-label">Areas:</span><span class="detail-value">${Array.isArray(qc.component_areas) ? qc.component_areas.join(', ') : 'N/A'}</span></div>
        </div>
      </div>
      ${convergencePoints.length ? `<div class="detail-section"><h4>Convergence</h4><div class="detail-chart-container"><canvas id="cxrHistoryDetailChart"></canvas></div></div>` : ''}
    `;
    html += '</div>';
    return html;
}

function renderMultiSeedDetail(data) {
    const config = data.config || {};
    const summary = data.summary || {};
    const detail = data.detail || {};
    const algorithms = detail.algorithms || {};
    const summaryStats = summary.summary_statistics || {};
    const stochasticSummary = summary.stochastic_summary || {};
    const rankingPrimary = (summary.ranking_primary || []).filter(row => isVisibleAlgo(row.algorithm));
    const stochasticAlgos = Object.keys(summaryStats).filter(isVisibleAlgo);
    const sortedStochastic = [...stochasticAlgos].sort((a, b) => {
        return (
            Number(summaryStats[b]?.fe_mean ?? Number.NEGATIVE_INFINITY) - Number(summaryStats[a]?.fe_mean ?? Number.NEGATIVE_INFINITY)
            || Number(summaryStats[a]?.fe_sd ?? Number.POSITIVE_INFINITY) - Number(summaryStats[b]?.fe_sd ?? Number.POSITIVE_INFINITY)
        );
    });
    const bestFeMeanAlgo = sortedStochastic[0] || null;
    const bestFeSdAlgo = [...stochasticAlgos].sort((a, b) => {
        return Number(summaryStats[a]?.fe_sd ?? Number.POSITIVE_INFINITY) - Number(summaryStats[b]?.fe_sd ?? Number.POSITIVE_INFINITY);
    })[0] || null;
    const comparisons = (detail.wilcoxon?.comparisons || []).filter(row => isVisibleAlgo(row.vs));
    const baseAlgo = detail.wilcoxon?.base_algorithm || summary.base_algorithm || 'PA5';

    let html = '<div class="run-detail-content-inner">';
    html += renderWarnings(data.warnings);
    html += renderConfigGrid([
        { label: 'Tên ảnh', value: config.image_name || config.image_id },
        { label: 'Đường dẫn ảnh', value: config.image_path },
        { label: 'Thời gian chạy', value: config.created_at || summary.created_at },
        { label: 'k', value: config.k },
        { label: 'start_seed', value: config.start_seed },
        { label: 'Số lượng seed', value: summary.n_seeds || config.n_seeds },
        { label: 'n_agents', value: config.n_agents },
        { label: 'n_iters', value: config.n_iters },
        { label: 'Objective', value: config.objective_name },
        { label: 'Penalty mode', value: config.penalty_mode ?? 'None' },
        { label: 'share_interval', value: config.share_interval },
        { label: 'Total time', value: formatValue(summary.total_time, 2, 's') },
    ]);
    html += renderGraySection(data.assets?.gray);

    html += `
      <div class="detail-section">
        <h4>📌 Kết luận nhanh</h4>
        <div class="summary-cards">
          <div class="summary-card-detail">
            <div class="summary-card-label">FE mean tốt nhất</div>
            <div class="summary-card-value">${bestFeMeanAlgo || 'N/A'}</div>
            <div class="summary-card-label">${formatValue(summaryStats[bestFeMeanAlgo]?.fe_mean, 6)}</div>
          </div>
          <div class="summary-card-detail">
            <div class="summary-card-label">FE SD thấp nhất</div>
            <div class="summary-card-value">${bestFeSdAlgo || 'N/A'}</div>
            <div class="summary-card-label">${formatValue(summaryStats[bestFeSdAlgo]?.fe_sd, 6)}</div>
          </div>
        </div>
      </div>
    `;

    html += `
      <div class="detail-section">
        <h4>📊 Bảng mean +/- SD</h4>
        <div class="comparison-table-container">
          <table class="comparison-table">
            <thead>
              <tr>
                <th>Thuật toán</th>
                <th>FE</th>
                <th>Boundary DSC</th>
                <th>PSNR</th>
                <th>SSIM</th>
                <th>Time</th>
                <th>Số lượt chạy</th>
              </tr>
            </thead>
            <tbody>
              ${sortedStochastic.map((algoName, idx) => {
                const stat = summaryStats[algoName] || {};
                return `
                  <tr class="${idx === 0 ? 'best-row' : ''}">
                    <td class="algo-name-cell">${idx === 0 ? '#1 ' : ''}${algoName}</td>
                    <td>${formatMeanSd(stat.fe_mean, stat.fe_sd, 6)}</td>
                    <td>${formatMeanSd(stat.boundary_dsc_mean, stat.boundary_dsc_sd, 4)}</td>
                    <td>${formatMeanSd(stat.psnr_mean, stat.psnr_sd, 2)}</td>
                    <td>${formatMeanSd(stat.ssim_mean, stat.ssim_sd, 4)}</td>
                    <td>${formatMeanSd(stat.time_mean, stat.time_sd, 2)}</td>
                    <td>${stat.n_runs ?? 'N/A'}</td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    if (false) {
        html += `
          <div class="detail-section">
            <h4>📏 Baseline xác định</h4>
            <div class="comparison-table-container">
              <table class="comparison-table">
                <thead><tr><th>Thuật toán</th><th>FE</th><th>Boundary DSC</th><th>PSNR</th><th>SSIM</th><th>Time</th><th>Ghi chú</th></tr></thead>
                <tbody>
                  <tr>
                    <td>${deterministicBaseline.algorithm || 'OTSU'}</td>
                    <td>${formatValue(deterministicBaseline.fe_mean, 6)}</td>
                    <td>${formatValue(deterministicBaseline.boundary_dsc_mean, 4)}</td>
                    <td>${formatValue(deterministicBaseline.psnr_mean, 2)}</td>
                    <td>${formatValue(deterministicBaseline.ssim_mean, 4)}</td>
                    <td>${formatValue(deterministicBaseline.time_mean, 2, 's')}</td>
                    <td>SD = 0 (deterministic)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        `;
    }

    if (comparisons.length > 0) {
        html += `
          <div class="detail-section">
            <h4>🧪 Wilcoxon</h4>
            <div class="comparison-table-container">
              <table class="comparison-table">
                <thead>
                  <tr>
                    <th>${baseAlgo} vs</th>
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
                  ${comparisons.map(row => `
                    <tr>
                      <td>${row.vs}</td>
                      <td>${formatValue(row.fe_delta_mean, 4)}</td>
                      <td>${row.fe_p !== null && row.fe_p !== undefined ? Number(row.fe_p).toExponential(2) : 'N/A'}</td>
                      <td>${formatValue(row.boundary_dsc_delta_mean, 4)}</td>
                      <td>${row.boundary_dsc_p !== null && row.boundary_dsc_p !== undefined ? Number(row.boundary_dsc_p).toExponential(2) : 'N/A'}</td>
                      <td>${formatValue(row.psnr_delta_mean, 4)}</td>
                      <td>${row.psnr_p !== null && row.psnr_p !== undefined ? Number(row.psnr_p).toExponential(2) : 'N/A'}</td>
                      <td>${formatValue(row.ssim_delta_mean, 4)}</td>
                      <td>${row.ssim_p !== null && row.ssim_p !== undefined ? Number(row.ssim_p).toExponential(2) : 'N/A'}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        `;
    }

    if (rankingPrimary.length > 0) {
        html += `
          <div class="detail-section">
            <h4>🏆 Ranking stochastic</h4>
            <div class="comparison-table-container">
              <table class="comparison-table">
                <thead><tr><th>Hạng</th><th>Thuật toán</th><th>FE mean</th><th>FE SD</th></tr></thead>
                <tbody>
                  ${rankingPrimary.map(row => `
                    <tr class="${row.rank === 1 ? 'best-row' : ''}">
                      <td>${row.rank}</td>
                      <td>${row.algorithm}</td>
                      <td>${formatValue(row.fe_mean, 6)}</td>
                      <td>${formatValue(row.fe_sd, 6)}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        `;
    }

    const detailRows = detail.results || [];
    const algoNames = Object.keys(algorithms).filter(isVisibleAlgo);
    if (algoNames.length > 0) {
        html += '<div class="detail-section"><h4>🧬 Per-seed detail</h4>';
        algoNames.forEach((algoName, idx) => {
            const algo = algorithms[algoName] || {};
            const rows = algo.per_seed || detailRows.filter(row => row.algorithm === algoName);
            const images = algo.images || {};
            html += `
              <div style="margin-bottom:24px;">
                <h5>${algoName}</h5>
                <div class="detail-images-grid-large">
                  ${images.segmented ? `<div class="detail-image-item-large"><div class="detail-image-label-large">${algoName} segmented</div><div class="seg-image-container" id="multiSegImage${idx}" data-path="${images.segmented}"></div></div>` : ''}
                  ${images.overlay ? `<div class="detail-image-item-large"><div class="detail-image-label-large">${algoName} overlay</div><div class="seg-image-container" id="multiOverlayImage${idx}" data-path="${images.overlay}"></div></div>` : ''}
                </div>
                <div class="comparison-table-container">
                  <table class="comparison-table">
                    <thead><tr><th>Seed</th><th>FE</th><th>Boundary DSC</th><th>PSNR</th><th>SSIM</th><th>Time</th><th>Thresholds</th></tr></thead>
                    <tbody>
                      ${rows.map(row => `
                        <tr>
                          <td>${row.seed ?? 'N/A'}</td>
                          <td>${formatValue(row.fe, 6)}</td>
                          <td>${formatValue(row.boundary_dsc, 4)}</td>
                          <td>${formatValue(row.psnr, 2)}</td>
                          <td>${formatValue(row.ssim, 4)}</td>
                          <td>${formatValue(row.time, 2, 's')}</td>
                          <td>${Array.isArray(row.thresholds) ? row.thresholds.join(', ') : 'N/A'}</td>
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                </div>
              </div>
            `;
        });
        html += '</div>';
    }

    html += '</div>';
    return html;
}

function drawSingleHistoryChart(history, canvasId, label) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !Array.isArray(history) || history.length === 0) return;
    const labels = history.map(item => item.iter ?? 0);
    const values = history.map(item => Number(item.best_f));
    new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label,
                data: values,
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37,99,235,0.08)',
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
                y: { title: { display: true, text: 'Best fitness' } }
            }
        }
    });
}

async function viewRunDetail(runName) {
    const modal = document.getElementById('runDetailModal');
    const body = document.getElementById('runDetailBody');
    const title = document.getElementById('runDetailTitle');
    if (!modal || !body || !title) return;

    modal.classList.add('active');
    document.body.classList.add('no-scroll');
    body.innerHTML = `<div class="empty-state"><div class="empty-icon">⏳</div><div class="empty-text">Đang tải chi tiết...</div></div>`;

    try {
        const res = await fetch(`/api/history/detail/${encodeURIComponent(runName)}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Lỗi khi tải chi tiết');

        title.textContent = `Chi tiết: ${runName}`;
        body.innerHTML = isCXRHistoryRun(data)
            ? renderCXRDetail(data)
            : (isMultiSeedHistoryRun(data) ? renderMultiSeedDetail(data) : renderSingleDetail(data));

        setTimeout(() => {
            if (!isCXRHistoryRun(data) && data.assets?.gray) loadImageToContainer('grayImageContainer', data.assets.gray);
            document.querySelectorAll('.seg-image-container').forEach(container => {
                const path = container.getAttribute('data-path');
                if (path) loadImageToContainer(container.id, path);
            });

            if (isCXRHistoryRun(data) && Array.isArray(data.detail?.convergence?.points)) {
                const points = data.detail.convergence.points;
                drawSingleHistoryChart(points.map(p => ({ iter: p.iter, best_f: p.fe })), 'cxrHistoryDetailChart', 'FE');
            }

            if (!isCXRHistoryRun(data) && !isMultiSeedHistoryRun(data) && data.detail?.algorithms) {
                Object.entries(data.detail.algorithms).forEach(([algoName, algo], idx) => {
                    if (Array.isArray(algo.history) && algo.history.length > 0) {
                        drawSingleHistoryChart(algo.history, `singleHistoryChart${idx}`, algoName);
                    }
                });
            }

            if (!isCXRHistoryRun(data) && !isMultiSeedHistoryRun(data) && data.detail?.histogram?.bins && data.detail?.histogram?.counts) {
                loadDynamicHistogram(data.run_name);
                document.querySelectorAll('.histogram-algo-checkbox-dynamic').forEach(checkbox => {
                    checkbox.addEventListener('change', () => loadDynamicHistogram(data.run_name));
                });
            }

            if (!isCXRHistoryRun(data) && !isMultiSeedHistoryRun(data) && Array.isArray(data.detail?.benchmark)) {
                data.detail.benchmark.forEach((bm, idx) => {
                    if (!bm.error && bm.results) drawBenchmarkChartDetail(bm, `benchmarkChart${idx}`);
                });
            }
        }, 50);
    } catch (err) {
        console.error('Error loading run detail:', err);
        body.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><div class="empty-text">Lỗi: ${err.message}</div></div>`;
    }
}

function loadImageToContainer(containerId, imagePath) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container not found: ${containerId}`);
        return;
    }

    // Show loading
    container.innerHTML = '<div style="padding:20px; text-align:center; color:#999;">⏳ Đang tải...</div>';

    // Debug log
    console.log(`Fetching image: /api/image?path=${encodeURIComponent(imagePath)}`);

    // Fetch image
    fetch(`/api/image?path=${encodeURIComponent(imagePath)}`)
        .then(res => {
            console.log(`Response status for ${imagePath}:`, res.status);
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
            return res.json();
        })
        .then(data => {
            console.log(`Response data for ${imagePath}:`, data.error ? `Error: ${data.error}` : 'Success');
            if (data.data_url) {
                container.innerHTML = `
                    <img src="${data.data_url}" 
                         alt="Image" 
                         onclick="openImageModal(this.src)"
                         style="max-width:100%; height:auto; cursor:pointer; display:block;">
                `;
            } else if (data.error) {
                container.innerHTML = `<div style="padding:20px; text-align:center; color:#e53e3e;">❌ ${data.error}</div>`;
            } else {
                container.innerHTML = '<div style="padding:20px; text-align:center; color:#e53e3e;">❌ Không thể tải ảnh</div>';
            }
        })
        .catch(err => {
            console.error('Error loading image:', imagePath, err);
            container.innerHTML = `<div style="padding:20px; text-align:center; color:#e53e3e;">❌ Lỗi: ${err.message}<br><small>Path: ${imagePath}</small></div>`;
        });
}

function drawBenchmarkChartDetail(bm, canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const results = bm.results;
    const algoNames = Object.keys(results).filter(isVisibleAlgo);

    // Tìm độ dài series lớn nhất
    const maxLen = algoNames.reduce((m, k) => Math.max(m, (results[k].series || []).length), 0);
    const labels = Array.from({ length: maxLen }, (_, i) => i);

    // Màu sắc cho từng thuật toán
    const colors = {
        'GWO': '#2563eb',
        'WOA': '#7c3aed',
        'PSO': '#dc2626',
        'OTSU': '#f59e0b',
        'HYBRID-PA5': '#16a34a',
        'HYBRID-PA6': '#0f766e',
        'HYBRID-PA1': '#38b2ac',
        'HYBRID-PA2': '#ed64a6',
        'HYBRID-PA3': '#ecc94b',
        'HYBRID-PA4': '#667eea',
    };

    const EPS = 1e-12;

    const datasets = algoNames.map(k => {
        const s = results[k].series || [];
        const padded = labels.map((_, i) => {
            if (i >= s.length) return null;
            const v = s[i];
            if (v === null || v === undefined || Number.isNaN(v)) return null;
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

    new Chart(ctx, {
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
                        boxWidth: 12,
                        font: { size: 10 },
                        padding: 8,
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
                    title: { display: true, text: "Iteration", font: { size: 11 } },
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: { font: { size: 10 } }
                },
                y: {
                    type: 'logarithmic',
                    min: 1e-12,
                    title: { display: true, text: "Best Fitness", font: { size: 11 } },
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: {
                        font: { size: 10 },
                        callback: function (value) {
                            return Number(value).toExponential(2);
                        }
                    }
                }
            }
        }
    });
}

// Make function global
window.viewRunDetail = viewRunDetail;

// Global variables
let histogramChartInstance = null;
let currentHistogramDataUrl = null;
let currentRunName = null;

function loadDynamicHistogram(runName) {
    const container = document.getElementById('histogramImageContainer');
    if (!container) return;

    // Store current run name
    currentRunName = runName;

    // Show loading
    container.innerHTML = '<div style="color: #999;">⏳ Đang tạo histogram...</div>';

    // Get selected algorithms
    const checkboxes = document.querySelectorAll('.histogram-algo-checkbox-dynamic:checked');
    const selectedAlgos = Array.from(checkboxes).map(cb => cb.getAttribute('data-algo'));

    console.log('Loading histogram for run:', runName, 'with algorithms:', selectedAlgos);

    // Call API to generate histogram
    fetch('/api/generate_histogram', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            run_name: runName,
            algorithms: selectedAlgos
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.data_url) {
                currentHistogramDataUrl = data.data_url;
                container.innerHTML = `
                <img src="${data.data_url}" 
                     alt="Histogram" 
                     onclick="openImageModal(this.src)"
                     style="max-width:100%; height:auto; cursor:pointer; display:block;">
            `;
                console.log('Histogram loaded successfully');
            } else if (data.error) {
                container.innerHTML = `<div style="padding:20px; text-align:center; color:#e53e3e;">❌ ${data.error}</div>`;
            } else {
                container.innerHTML = '<div style="padding:20px; text-align:center; color:#e53e3e;">❌ Không thể tải histogram</div>';
            }
        })
        .catch(err => {
            console.error('Error loading histogram:', err);
            container.innerHTML = `<div style="padding:20px; text-align:center; color:#e53e3e;">❌ Lỗi: ${err.message}</div>`;
        });
}

function downloadCurrentHistogram() {
    if (!currentHistogramDataUrl) {
        alert('Histogram chưa được tạo!');
        return;
    }

    // Convert data URL to blob and download
    const byteString = atob(currentHistogramDataUrl.split(',')[1]);
    const mimeString = currentHistogramDataUrl.split(',')[0].split(':')[1].split(';')[0];
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
    }
    const blob = new Blob([ab], { type: mimeString });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'histogram_chart.png';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Make functions global
window.loadDynamicHistogram = loadDynamicHistogram;
window.downloadCurrentHistogram = downloadCurrentHistogram;

function downloadHistogramImage(imagePath) {
    // Download histogram image directly
    fetch(`/api/image?path=${encodeURIComponent(imagePath)}`)
        .then(res => res.json())
        .then(data => {
            if (data.data_url) {
                // Convert data URL to blob and download
                const byteString = atob(data.data_url.split(',')[1]);
                const mimeString = data.data_url.split(',')[0].split(':')[1].split(';')[0];
                const ab = new ArrayBuffer(byteString.length);
                const ia = new Uint8Array(ab);
                for (let i = 0; i < byteString.length; i++) {
                    ia[i] = byteString.charCodeAt(i);
                }
                const blob = new Blob([ab], { type: mimeString });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'histogram_chart.png';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } else {
                alert('Không thể tải ảnh histogram!');
            }
        })
        .catch(err => {
            console.error('Error downloading histogram:', err);
            alert('Lỗi khi tải ảnh: ' + err.message);
        });
}

// Make function global
window.downloadHistogramImage = downloadHistogramImage;

function downloadHistogramChart() {
    if (!histogramChartInstance) {
        alert('Biểu đồ chưa được tạo!');
        return;
    }

    const canvas = document.getElementById('histogramChart');
    if (!canvas) {
        alert('Không tìm thấy canvas!');
        return;
    }

    // Convert canvas to blob and download
    canvas.toBlob(function (blob) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'histogram_chart.png';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
}

// Make function global
window.downloadHistogramChart = downloadHistogramChart;

function drawHistogramChart(histogramData, algorithms, k) {
    const canvas = document.getElementById('histogramChart');
    if (!canvas) {
        console.error('Canvas histogramChart not found!');
        return;
    }

    const ctx = canvas.getContext('2d');
    const bins = histogramData.bins || [];
    const counts = histogramData.counts || [];

    console.log('Drawing histogram chart:', {
        bins: bins.length,
        counts: counts.length,
        algorithms: Object.keys(algorithms || {})
    });

    // Destroy previous chart if exists
    if (histogramChartInstance) {
        histogramChartInstance.destroy();
    }

    // Color map for algorithms
    const colorMap = {
        'GWO': '#2563eb',
        'WOA': '#7c3aed',
        'PSO': '#dc2626',
        'OTSU': '#f59e0b',
        'HYBRID-PA5': '#16a34a',
        'HYBRID-PA6': '#0f766e',
        'HYBRID-PA1': '#38b2ac',
        'HYBRID-PA2': '#ed64a6',
        'HYBRID-PA3': '#ecc94b',
        'HYBRID-PA4': '#667eea',
    };

    // Prepare threshold lines datasets
    const thresholdDatasets = [];
    const algoNames = Object.keys(algorithms || {}).sort();

    algoNames.forEach(algoName => {
        const algo = algorithms[algoName];
        const thresholds = algo.best_result?.thresholds || [];
        const color = colorMap[algoName] || '#718096';

        // Create vertical line data for each threshold
        thresholds.forEach(threshold => {
            thresholdDatasets.push({
                label: algoName,
                data: [
                    { x: threshold, y: 0 },
                    { x: threshold, y: Math.max(...counts) }
                ],
                borderColor: color,
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                showLine: true,
                tension: 0,
            });
        });
    });

    // Create chart
    histogramChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: bins,
            datasets: [
                {
                    label: 'Tần suất',
                    data: counts,
                    backgroundColor: 'rgba(99, 102, 241, 0.5)',
                    borderColor: 'rgba(99, 102, 241, 1)',
                    borderWidth: 1,
                    type: 'bar',
                },
                ...thresholdDatasets
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        font: { size: 11 },
                        padding: 8,
                        filter: function (item, chart) {
                            // Only show unique algorithm names
                            return item.text === 'Tần suất' ||
                                chart.data.datasets.findIndex(d => d.label === item.text) === item.datasetIndex;
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function (context) {
                            return 'Cường độ điểm ảnh: ' + context[0].label;
                        },
                        label: function (context) {
                            if (context.dataset.label === 'Tần suất') {
                                return 'Tần suất: ' + context.parsed.y;
                            }
                            return context.dataset.label + ': Ngưỡng';
                        }
                    }
                },
                title: {
                    display: true,
                    text: `Phân tích Histogram & Ngưỡng (K = ${k})`,
                    font: { size: 14, weight: 'bold' }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Cường độ điểm ảnh (0-255)',
                        font: { size: 12 }
                    },
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: {
                        font: { size: 10 },
                        maxTicksLimit: 20
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Tần suất',
                        font: { size: 12 }
                    },
                    grid: { color: 'rgba(0,0,0,0.1)' },
                    ticks: { font: { size: 10 } }
                }
            }
        }
    });

    // Add checkbox event listeners
    const checkboxes = document.querySelectorAll('.histogram-algo-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function () {
            const algoName = this.getAttribute('data-algo');
            const isChecked = this.checked;

            // Update visibility of threshold lines for this algorithm
            histogramChartInstance.data.datasets.forEach((dataset, index) => {
                if (dataset.label === algoName && index > 0) {
                    dataset.hidden = !isChecked;
                }
            });

            histogramChartInstance.update();
        });
    });

    console.log('Histogram chart created successfully');
}
