@echo off
REM PA5 share_interval sweep: Test different knowledge transfer rates
echo ========================================
echo PA5 SHARE_INTERVAL SWEEP
echo ========================================
echo Config:
echo   - Images: All val images
echo   - Agents: 30
echo   - Iterations: 100
echo   - Seeds: 0-30 (31 seeds)
echo   - Strategy: PA5 only
echo   - Share intervals: 1, 2, 3, 5, 10, 20
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
  --strategies PA5 ^
  --pa5_share_intervals 1,2,3,5,10,20

echo.
echo ========================================
echo DONE!
echo ========================================
echo Check summary_sorted.csv to find best share_interval
pause
