import time
import os
import subprocess
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AppReloader(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.start_app()

    def start_app(self):
        # 终止现有进程
        if self.process:
            self.process.terminate()
            self.process.wait()
        
        # 启动新进程
        print("\n=== 正在启动服务器 ===")
        self.process = subprocess.Popen([sys.executable, "main.py"])
        print("=== 服务器已启动 ===\n")

    def on_modified(self, event):
        if event.src_path.endswith('.py') or event.src_path.endswith('.md'):
            print(f"\n检测到文件变化: {event.src_path}")
            self.start_app()

    def on_created(self, event):
        if event.src_path.endswith('.py') or event.src_path.endswith('.md'):
            print(f"\n检测到新文件: {event.src_path}")
            self.start_app()

def main():
    # 创建观察者
    observer = Observer()
    event_handler = AppReloader()
    
    # 监视apps目录
    observer.schedule(event_handler, 'apps', recursive=True)
    # 监视main.py
    observer.schedule(event_handler, '.', recursive=False)
    
    observer.start()
    print("=== 热重载监视器已启动 ===")
    print("监视目录: ./apps")
    print("监视文件: ./main.py")
    print("按Ctrl+C退出\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
        print("\n=== 服务已停止 ===")

    observer.join()

if __name__ == "__main__":
    main() 