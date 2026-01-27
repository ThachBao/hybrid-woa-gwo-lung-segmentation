@echo off
REM Quick test: 5 images, 10 agents, 20 iterations
echo Running quick test (5 images, 10 agents, 20 iterations)...
python -m src.runner.compare_gwo_woa_strategies ^
  --root dataset/BDS500/images/val ^
  --out_root outputs/compareGWO-WOA ^
  --limit 5 ^
  --k 10 ^
  --n_agents 10 ^
  --n_iters 20 ^
  --seed 42

echo.
echo Done! Check outputs/compareGWO-WOA/ for results.
pause
