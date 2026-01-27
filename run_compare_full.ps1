# Full run: all images, 30 agents, 100 iterations, seed 42
Write-Host "Running full comparison (all images, 30 agents, 100 iterations, seed 42)..." -ForegroundColor Green
Write-Host ""

python -m src.runner.compare_gwo_woa_strategies `
  --root dataset/BDS500/images/val `
  --out_root outputs/compareGWO-WOA `
  --k 10 `
  --n_agents 30 `
  --n_iters 100 `
  --seed 42 `
  --share_interval 4

Write-Host ""
Write-Host "Done! Check outputs/compareGWO-WOA/ for results." -ForegroundColor Cyan
Read-Host "Press Enter to continue"
