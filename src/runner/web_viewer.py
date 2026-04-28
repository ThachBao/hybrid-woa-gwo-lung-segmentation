#!/usr/bin/env python3
"""
Web viewer đơn giản để xem lịch sử các lần chạy qua trình duyệt.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path

from src.runner.history_manager import HistoryManager


def generate_html(manager: HistoryManager) -> str:
    """Tạo HTML để hiển thị lịch sử"""
    runs = manager.list_runs()
    
    html = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lịch sử chạy - Image Segmentation</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 {
            color: #333;
            margin-bottom: 30px;
            text-align: center;
        }
        .stats {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .stat-item {
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #2196F3;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        .filters {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .filter-group {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }
        .filter-group label {
            font-weight: 500;
        }
        .filter-group select, .filter-group input {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .runs-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 20px;
        }
        .run-card {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .run-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }
        .run-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
        }
        .run-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 5px;
            word-break: break-all;
        }
        .run-time {
            font-size: 12px;
            opacity: 0.9;
        }
        .run-body {
            padding: 15px;
        }
        .run-info {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
        }
        .info-item {
            font-size: 13px;
        }
        .info-label {
            color: #666;
            font-weight: 500;
        }
        .info-value {
            color: #333;
            font-weight: 600;
        }
        .run-images {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 15px;
        }
        .image-container {
            text-align: center;
        }
        .image-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }
        .run-images img {
            width: 100%;
            height: auto;
            border-radius: 4px;
            border: 1px solid #ddd;
        }
        .thresholds {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 12px;
            word-break: break-all;
        }
        .no-runs {
            text-align: center;
            padding: 60px 20px;
            color: #666;
            font-size: 18px;
        }
        .algo-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .algo-gwo { background: #e3f2fd; color: #1976d2; }
        .algo-woa { background: #f3e5f5; color: #7b1fa2; }
        .algo-hybrid { background: #e8f5e9; color: #388e3c; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Lịch sử chạy Image Segmentation</h1>
        
        <div class="stats">
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value" id="total-runs">0</div>
                    <div class="stat-label">Tổng số lần chạy</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="total-gwo">0</div>
                    <div class="stat-label">GWO</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="total-woa">0</div>
                    <div class="stat-label">WOA</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="total-hybrid">0</div>
                    <div class="stat-label">HYBRID</div>
                </div>
            </div>
        </div>
        
        <div class="filters">
            <div class="filter-group">
                <label>Lọc theo thuật toán:</label>
                <select id="filter-algo" onchange="filterRuns()">
                    <option value="">Tất cả</option>
                    <option value="GWO">GWO</option>
                    <option value="WOA">WOA</option>
                    <option value="HYBRID">HYBRID</option>
                </select>
                
                <label>Lọc theo k:</label>
                <select id="filter-k" onchange="filterRuns()">
                    <option value="">Tất cả</option>
                </select>
                
                <label>Tìm kiếm:</label>
                <input type="text" id="search-box" placeholder="Tên run..." onkeyup="filterRuns()">
            </div>
        </div>
        
        <div class="runs-grid" id="runs-container">
        </div>
    </div>
    
    <script>
        const runsData = """ + json.dumps([r.get_summary() for r in runs]) + """;
        
        function imageToBase64(imagePath) {
            // Placeholder - trong thực tế cần load ảnh từ server
            return "";
        }
        
        function formatTimestamp(isoString) {
            if (!isoString) return "N/A";
            const date = new Date(isoString);
            return date.toLocaleString('vi-VN');
        }
        
        function getAlgoClass(algo) {
            const algoUpper = algo.toUpperCase();
            if (algoUpper === 'GWO') return 'algo-gwo';
            if (algoUpper === 'WOA') return 'algo-woa';
            if (algoUpper.includes('HYBRID')) return 'algo-hybrid';
            return 'algo-gwo';
        }
        
        function renderRun(run) {
            const bestF = run.best_f !== null && run.best_f !== undefined 
                ? run.best_f.toFixed(6) 
                : 'N/A';
            
            const thresholds = run.thresholds 
                ? run.thresholds.join(', ') 
                : 'N/A';
            
            let imagesHtml = '';
            if (run.images && (run.images.gray || run.images.segmented)) {
                imagesHtml = '<div class="run-images">';
                if (run.images.gray) {
                    imagesHtml += `
                        <div class="image-container">
                            <div class="image-label">Ảnh gốc</div>
                            <img src="file:///${run.images.gray.replace(/\\\\/g, '/')}" 
                                 alt="Gray" 
                                 onerror="this.style.display='none'">
                        </div>
                    `;
                }
                if (run.images.segmented) {
                    imagesHtml += `
                        <div class="image-container">
                            <div class="image-label">Ảnh phân đoạn</div>
                            <img src="file:///${run.images.segmented.replace(/\\\\/g, '/')}" 
                                 alt="Segmented"
                                 onerror="this.style.display='none'">
                        </div>
                    `;
                }
                imagesHtml += '</div>';
            }
            
            return `
                <div class="run-card" data-algo="${run.algo}" data-k="${run.k}" data-name="${run.run_name}">
                    <div class="run-header">
                        <div class="run-title">${run.run_name}</div>
                        <div class="run-time">${formatTimestamp(run.timestamp)}</div>
                    </div>
                    <div class="run-body">
                        <div class="run-info">
                            <div class="info-item">
                                <div class="info-label">Thuật toán</div>
                                <div class="info-value">
                                    <span class="algo-badge ${getAlgoClass(run.algo)}">${run.algo}</span>
                                </div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Số ngưỡng (k)</div>
                                <div class="info-value">${run.k}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Agents</div>
                                <div class="info-value">${run.n_agents || 'N/A'}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Iterations</div>
                                <div class="info-value">${run.n_iters || 'N/A'}</div>
                            </div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Best Fitness</div>
                            <div class="info-value">${bestF}</div>
                        </div>
                        <div class="thresholds">
                            <strong>Thresholds:</strong> ${thresholds}
                        </div>
                        ${imagesHtml}
                    </div>
                </div>
            `;
        }
        
        function updateStats() {
            document.getElementById('total-runs').textContent = runsData.length;
            document.getElementById('total-gwo').textContent = 
                runsData.filter(r => r.algo.toUpperCase() === 'GWO').length;
            document.getElementById('total-woa').textContent = 
                runsData.filter(r => r.algo.toUpperCase() === 'WOA').length;
            document.getElementById('total-hybrid').textContent = 
                runsData.filter(r => r.algo.toUpperCase().includes('HYBRID')).length;
            
            // Populate k filter
            const kValues = [...new Set(runsData.map(r => r.k))].sort((a, b) => a - b);
            const kFilter = document.getElementById('filter-k');
            kValues.forEach(k => {
                const option = document.createElement('option');
                option.value = k;
                option.textContent = k;
                kFilter.appendChild(option);
            });
        }
        
        function filterRuns() {
            const algoFilter = document.getElementById('filter-algo').value.toUpperCase();
            const kFilter = document.getElementById('filter-k').value;
            const searchText = document.getElementById('search-box').value.toLowerCase();
            
            const cards = document.querySelectorAll('.run-card');
            let visibleCount = 0;
            
            cards.forEach(card => {
                const algo = card.dataset.algo.toUpperCase();
                const k = card.dataset.k;
                const name = card.dataset.name.toLowerCase();
                
                const matchAlgo = !algoFilter || algo === algoFilter || 
                                  (algoFilter === 'HYBRID' && algo.includes('HYBRID'));
                const matchK = !kFilter || k === kFilter;
                const matchSearch = !searchText || name.includes(searchText);
                
                if (matchAlgo && matchK && matchSearch) {
                    card.style.display = 'block';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });
            
            const container = document.getElementById('runs-container');
            if (visibleCount === 0 && cards.length > 0) {
                container.innerHTML = '<div class="no-runs">Không tìm thấy kết quả phù hợp</div>';
            }
        }
        
        function init() {
            const container = document.getElementById('runs-container');
            
            if (runsData.length === 0) {
                container.innerHTML = '<div class="no-runs">Chưa có lần chạy nào</div>';
                return;
            }
            
            container.innerHTML = runsData.map(run => renderRun(run)).join('');
            updateStats();
        }
        
        init();
    </script>
</body>
</html>
    """
    
    return html


def main():
    ap = argparse.ArgumentParser(description="Web viewer cho lịch sử chạy")
    ap.add_argument("--base_dir", type=str, default="outputs/runs", help="Thư mục chứa lịch sử")
    ap.add_argument("--output", type=str, default="outputs/history_viewer.html", help="File HTML output")
    args = ap.parse_args()
    
    manager = HistoryManager(args.base_dir)
    html = generate_html(manager)
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Đã tạo web viewer tại: {args.output}")
    print(f"Mở file này bằng trình duyệt để xem lịch sử")


if __name__ == "__main__":
    main()
