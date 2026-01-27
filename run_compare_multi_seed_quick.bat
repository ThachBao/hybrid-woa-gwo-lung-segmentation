@echo off
REM Quick multi-seed test: 5 images, 10 agents, 20 iterations, 30 seeds
echo Running quick multi-seed test (5 images, 10 agents, 20 iterations, 30 seeds)...
echo This will still take some time!
echo.
echo Press Ctrl+C to cancel, or
pause

for /L %%s in (0,1,29) do (
  echo.
  echo ========================================
  echo Running seed %%s / 29
  echo ========================================
  python -m src.runner.compare_gwo_woa_strategies ^
    --root dataset/BDS500/images/val ^
    --out_root outputs/compareGWO-WOA ^
    --limit 100 ^
    --k 10 ^
    --n_agents 30 ^
    --n_iters 100 ^
    --seed %%s
)

echo.
echo Done! All 30 seeds completed.
echo Check outputs/compareGWO-WOA/ for results.
pause
