@echo off
REM Full sweep: 30 agents, 100 iterations, seed 0-30, all val images
echo ========================================
echo FULL SWEEP: PA1-PA5
echo ========================================
echo Config:
echo   - Images: All val images
echo   - Agents: 30
echo   - Iterations: 100
echo   - Seeds: 0-30 (31 seeds)
echo   - Strategies: PA1, PA2, PA3, PA4, PA5
echo.
echo This will take a VERY long time!
echo Press Ctrl+C to cancel, or
pause

python -m src.runner.compare_gwo_woa_seed_sweep ^
  --root dataset/BDS500/images/val ^
  --out_root outputs/compareGWO-WOA ^
  --k 10 ^
  --n_agents 30 ^
  --n_iters 100 ^
  --seed_start 0 ^
  --seed_end 30 ^
  --strategies PA1,PA2,PA3,PA4,PA5

echo.
echo ========================================
echo DONE!
echo ========================================
echo Check outputs/compareGWO-WOA/ for results
pause
