"""
Test BDS500 API endpoint
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_eval_bds500_api():
    """Test API đánh giá BDS500"""
    print("=" * 60)
    print("TEST BDS500 API")
    print("=" * 60)
    
    # Test với 2 ảnh, 2 thuật toán
    data = {
        "split": "train",
        "limit": "2",  # Chỉ 2 ảnh để test nhanh
        "k": "3",      # Ít ngưỡng để test nhanh
        "seed": "42",
        "n_agents": "10",  # Ít cá thể để test nhanh
        "n_iters": "5",    # Ít vòng lặp để test nhanh
        "algorithms": "GWO,WOA",  # 2 thuật toán
    }
    
    print("\nGửi request đến /api/eval_bds500...")
    print(f"Params: {data}")
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/eval_bds500", data=data)
        elapsed = time.time() - start_time
        
        print(f"\nStatus code: {response.status_code}")
        print(f"Time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✓ SUCCESS")
            print(f"  Run dir: {result.get('run_dir')}")
            print(f"  N images: {result.get('n_images')}")
            print(f"  N algorithms: {result.get('n_algorithms')}")
            print(f"  Total runs: {result.get('total_runs')}")
            print(f"  Total time: {result.get('total_time', 0):.2f}s")
            
            # Print statistics
            stats = result.get('statistics', {})
            if stats:
                print("\n  Statistics:")
                for algo, s in stats.items():
                    print(f"    {algo}:")
                    print(f"      DICE: {s.get('dice_mean', 0):.4f} ± {s.get('dice_std', 0):.4f}")
                    print(f"      Time: {s.get('time_mean', 0):.2f}s")
            
            return True
        else:
            print(f"\n✗ ERROR: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Không thể kết nối đến server")
        print("Hãy chạy: python -m src.ui.app")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bds500_list_api():
    """Test API lấy danh sách ảnh BDS500"""
    print("\n" + "=" * 60)
    print("TEST BDS500 LIST API")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/bds500/list?split=train&limit=5")
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✓ SUCCESS")
            print(f"  Split: {result.get('split')}")
            print(f"  Total: {result.get('total')}")
            
            images = result.get('images', [])
            if images:
                print(f"\n  First 3 images:")
                for img in images[:3]:
                    print(f"    - {img.get('id')}: {img.get('name')}")
            
            return True
        else:
            print(f"\n✗ ERROR: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Không thể kết nối đến server")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("KIỂM TRA BDS500 API")
    print("=" * 60)
    print("\nLưu ý: Server phải đang chạy (python -m src.ui.app)")
    print()
    
    input("Nhấn Enter để tiếp tục...")
    
    results = []
    
    results.append(("BDS500 List API", test_bds500_list_api()))
    results.append(("BDS500 Eval API", test_eval_bds500_api()))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    print()
    if all_passed:
        print("✓ TẤT CẢ TESTS ĐỀU PASS")
    else:
        print("✗ CÓ TESTS FAIL")
    
    print("=" * 60)
