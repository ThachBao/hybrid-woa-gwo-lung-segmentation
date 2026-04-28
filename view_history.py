#!/usr/bin/env python3
"""
Script đơn giản để xem lịch sử các lần chạy.

Cách sử dụng:
  python view_history.py                    # Xem 10 lần chạy gần nhất
  python view_history.py --list             # Xem tất cả các lần chạy
  python view_history.py --run <tên_run>    # Xem chi tiết một lần chạy
  python view_history.py --algo GWO         # Lọc theo thuật toán
  python view_history.py --k 3              # Lọc theo số ngưỡng
  python view_history.py --export summary.json  # Export tóm tắt
"""

from src.runner.history_manager import main

if __name__ == "__main__":
    main()
