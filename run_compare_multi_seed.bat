@echo off
REM Run with multiple seeds (0..29 = 30 seeds)
echo Running with 30 seeds (0..29)...
echo This will take a VERY long time!
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
    --k 10 ^
    --n_agents 30 ^
    --n_iters 80 ^
    --seed %%s
)

echo.
echo Done! All 30 seeds completed.
echo Check outputs/compareGWO-WOA/ for results.
pause
