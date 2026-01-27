@echo off
REM Quick test: 5 images, 10 agents, 20 iterations, seed 0-2
echo ========================================
echo QUICK TEST SWEEP
echo ========================================
echo Config:
echo   - Images: 5
echo   - Agents: 10
echo   - Iterations: 20
echo   - Seeds: 0-2 (3 seeds)
echo   - Strategies: PA1, PA2, PA3, PA4, PA5
echo.
echo This is a quick test (~5-10 minutes)
pause

python -m src.runner.compare_gwo_woa_seed_sweep ^
  --root dataset/BDS500/images/val ^
  --out_root outputs/compareGWO-WOA ^
  --limit 5 ^
  --k 10 ^
  --n_agents 10 ^
  --n_iters 20 ^
  --seed_start 0 ^
  --seed_end 2 ^
  --strategies PA1,PA2,PA3,PA4,PA5

echo.
echo ========================================
echo DONE!
echo ========================================
echo Check outputs/compareGWO-WOA/ for results
pause
