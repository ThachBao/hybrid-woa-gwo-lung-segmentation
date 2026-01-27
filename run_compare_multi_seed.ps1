# Run with multiple seeds (0..29 = 30 seeds)
# Có thể thay đổi share_interval cho PA5 (mặc định = 4)
Write-Host "Running with 30 seeds (0..29)..." -ForegroundColor Yellow
Write-Host "This will take a VERY long time!" -ForegroundColor Red
Write-Host ""
Read-Host "Press Ctrl+C to cancel, or Enter to continue"

for ($s = 0; $s -le 29; $s++) {
  Write-Host ""
  Write-Host "========================================" -ForegroundColor Cyan
  Write-Host "Running seed $s / 29" -ForegroundColor Cyan
  Write-Host "========================================" -ForegroundColor Cyan
  
  python -m src.runner.compare_gwo_woa_strategies `
    --root dataset/BDS500/images/val `
    --out_root outputs/compareGWO-WOA `
    --k 10 `
    --n_agents 30 `
    --n_iters 80 `
    --seed $s `
    --share_interval 4
}

Write-Host ""
Write-Host "Done! All 30 seeds completed." -ForegroundColor Green
Write-Host "Check outputs/compareGWO-WOA/ for results." -ForegroundColor Cyan
Read-Host "Press Enter to continue"
