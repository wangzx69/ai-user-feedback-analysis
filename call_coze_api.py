# -*- coding: utf-8 -*-
"""Python调用扣子编程工作流API（异步版）
用法：python call_coze_api.py
"""
import json, sys, time, requests
from pathlib import Path
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ===== 配置 =====
API_BASE = "https://dykbfkp3n9.coze.site"
API_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImYyNzI3NjIyLWNlMzAtNDUyNi1iZjhhLWVjNjc5YjlmYzViYyJ9.eyJpc3MiOiJodHRwczovL2FwaS5jb3plLmNuIiwiYXVkIjpbIllqZFRBQ01Mb1VVV3NyeEp2R2Jua21HaUtYMW9hdGFlIl0sImV4cCI6ODIxMDI2Njg3Njc5OSwiaWF0IjoxNzg5OTU3MDA2LCJzdWIiOiJzcGlmZmU6Ly9hcGkuY296ZS5jbi93b3JrbG9hZF9pZGVudGl0eS9pZDo3Njg3NTMzOTA1MDA3NjA3ODE3Iiwic3JjIjoiaW5ib3VuZF9hdXRoX2FjY2Vzc190b2tlbl9pZDo3Njg3ODA2ODA1NjI3MzcxNTYzIn0.Vz03GaqGPVjqIa7ph-B4S_WHFqXhuieZPMaK0Y6VK72u5u5noperXZel0sqURMUGpbQR9QrhNtPbAAHh2RhFI08ev0q8wWey-n_dMI-poEJn-tVAhzdOqo4ubQ697LYV3GdiARlKHm8aM8B1-CoB0P4fsLQ_yTTxt-v-JH3I44P2RuO93q-Zs-679aeBoX6t5fPD47EKmDxgu1IP_sGodvqWSYExTCAD0XNW-PipyPcCEyLWwW649BKypqwGJenzn3vcY_kVI4n2REyhPIkkLBjcpnvG4Q0QPmQLQ2DqnD0fvIpfXk_kkMazCKd9u_MSXj9dR_3G7R6nGwT5VHUDhw"
DATA_FILE = Path(__file__).parent.parent / "data" / "coze_input_all.txt"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "coze_analysis_result.json"
# ================

def main():
    comments = DATA_FILE.read_text(encoding="utf-8")
    print(f"正在调用Coze API...")
    print(f"  评论长度: {len(comments)}字")

    headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}

    # 1. 提交异步任务
    resp = requests.post(f"{API_BASE}/async_run", headers=headers,
                        json={"comments_text": comments}, timeout=30)
    task = resp.json()
    task_id = task.get("task_id")
    print(f"  任务ID: {task_id}")

    # 2. 轮询结果
    print("  等待分析完成...")
    for i in range(120):
        time.sleep(10)
        r = requests.get(f"{API_BASE}/task/{task_id}", headers=headers, timeout=10).json()
        status = r.get("status")
        print(f"    [{i*10}s] {status}")
        if status == "success" or status == "completed":
            OUTPUT_FILE.write_text(json.dumps(r.get("result", r), ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n✅ 完成! 结果已保存: {OUTPUT_FILE}")
            result = r.get("result", r)
            for k, v in result.items():
                if "report" in k.lower() or "text" in k.lower():
                    print(f"\n运营周报:\n{v}")
                    break
            return
        if status == "failed":
            print(f"❌ 失败: {r.get('error')}")
            return

if __name__ == "__main__":
    main()
