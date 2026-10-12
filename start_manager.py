# -*- coding: utf-8 -*-
"""一键启动管理器（由"启动.bat"调用）。

功能：
1. 清理占用 8000/5173 端口的旧服务（自愈）
2. 启动后端（uvicorn）与前端（Vite dev server）
3. 等待就绪后自动打开浏览器 http://localhost:5173
4. 心跳监控：网页每 3 秒向后端 /api/heartbeat 报心跳；
   心跳停止超过 12 秒（网页已关闭）→ 自动停止前后端服务
5. 直接关闭本窗口或 Ctrl+C → 服务随控制台一并终止
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

# stdout 统一 UTF-8（bat 窗口 chcp 65001；其他环境下兜底，避免中文输出编码错误）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
HEARTBEAT_FILE = BACKEND_DIR / "data" / "heartbeat.txt"

APP_URL = "http://localhost:5173"
HEARTBEAT_TIMEOUT = 12  # 心跳停止多少秒后判定网页已关闭
CHECK_INTERVAL = 1      # 监控轮询间隔


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def free_port(port: int) -> None:
    """端口被占用时通过 netstat 找到监听进程并强制结束（清理旧服务残留）。"""
    if not port_in_use(port):
        return
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True,
                             text=True, timeout=10).stdout
        pids = set()
        for line in out.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                pids.add(line.split()[-1])
        for pid in pids:
            subprocess.run(["taskkill", "/F", "/PID", pid],
                           capture_output=True, timeout=10)
        time.sleep(1)
    except (OSError, subprocess.SubprocessError):
        print(f"  ! 端口 {port} 清理失败，若启动异常请手动关闭占用进程")


def wait_http(url: str, timeout: float = 90) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def kill_tree(procs: list[subprocess.Popen]) -> None:
    """终止服务进程及其子进程树（Windows 下 npm→vite 存在子进程，须杀树）。"""
    for p in procs:
        if p.poll() is not None:
            continue
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)],
                           capture_output=True, timeout=15)
        else:
            p.terminate()
    for p in procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def main() -> int:
    print("=" * 46)
    print("  法律论证标注系统 · 一键启动")
    print("=" * 46)

    # 1. 清理旧服务（端口自愈）
    print("[1/4] 检查端口…")
    free_port(8000)
    free_port(5173)

    # 2. 启动后端与前端（共享控制台：关闭本窗口即连带终止）
    print("[2/4] 启动后端（FastAPI :8000）…")
    procs: list[subprocess.Popen] = []
    try:
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
            cwd=str(BACKEND_DIR)))
        print("[2/4] 启动前端（Vite :5173）…")
        npm = "npm.cmd" if os.name == "nt" else "npm"
        procs.append(subprocess.Popen([npm, "run", "dev"],
                                      cwd=str(FRONTEND_DIR)))
    except OSError as e:
        print(f"  [错误] 启动失败：{e}")
        return 1

    # 3. 等待就绪并打开浏览器
    print("[3/4] 等待服务就绪…")
    if not wait_http("http://127.0.0.1:8000/api/health"):
        print("  [错误] 后端启动失败，请检查 backend 依赖是否已安装（pip install -r requirements.txt）")
        kill_tree(procs)
        return 1
    if not wait_http(APP_URL):
        print("  [错误] 前端启动失败，请检查 frontend 依赖是否已安装（npm install）")
        kill_tree(procs)
        return 1
    print(f"[4/4] 打开浏览器：{APP_URL}")
    webbrowser.open(APP_URL)
    print()
    print(f"  关闭网页后约 {HEARTBEAT_TIMEOUT} 秒将自动停止前后端服务。")
    print("  也可直接关闭本窗口或按 Ctrl+C 立即停止。")
    print("-" * 46)

    # 4. 心跳监控
    if HEARTBEAT_FILE.exists():
        HEARTBEAT_FILE.unlink()
    try:
        while True:
            time.sleep(CHECK_INTERVAL)
            if any(p.poll() is not None for p in procs):
                print("  [提示] 服务进程意外退出，正在停止…")
                break
            last_beat = 0.0
            if HEARTBEAT_FILE.exists():
                try:
                    last_beat = float(HEARTBEAT_FILE.read_text().strip())
                except ValueError:
                    pass
            if time.time() - last_beat > HEARTBEAT_TIMEOUT:
                print("\n  检测到网页已关闭，正在停止前后端服务…")
                break
    except KeyboardInterrupt:
        print("\n  收到中断，正在停止服务…")
    finally:
        kill_tree(procs)
        print("  [完成] 服务已停止。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
