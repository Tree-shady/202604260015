import sys
import subprocess
from colorama import init, Fore

from utils.storage import ensure_dir

init(autoreset=True)

PRIMARY_COLOR = Fore.GREEN
SECONDARY_COLOR = Fore.CYAN
ACCENT_COLOR = Fore.YELLOW
TEXT_COLOR = Fore.WHITE
ERROR_COLOR = Fore.RED
SUCCESS_COLOR = Fore.GREEN
INFO_COLOR = Fore.BLUE


def get_python_command():
    """根据操作系统返回正确的 Python 命令"""
    if sys.platform.startswith('win'):
        return 'python'
    else:
        return 'python3'

def get_os_name():
    """获取操作系统名称"""
    if sys.platform.startswith('win'):
        return 'Windows'
    elif sys.platform.startswith('linux'):
        return 'Linux'
    elif sys.platform.startswith('darwin'):
        return 'macOS'
    else:
        return sys.platform

def main():
    """主函数"""
    ensure_dir()

    os_name = get_os_name()
    python_cmd = get_python_command()

    print(f"\n{SECONDARY_COLOR}{'=' * 40}")
    print(f"{PRIMARY_COLOR}        个人日记本")
    print(f"{SECONDARY_COLOR}{'=' * 40}")
    print(f"{INFO_COLOR}检测到系统: {os_name}")
    print(f"{INFO_COLOR}使用命令: {python_cmd}")
    print(f"{SECONDARY_COLOR}{'=' * 40}")
    print(f"{TEXT_COLOR}1. Web 应用模式")
    print(f"{TEXT_COLOR}2. 本地图形化模式")
    print(f"{ERROR_COLOR}0. 退出")
    print(f"{SECONDARY_COLOR}{'=' * 40}")

    choice = input("请选择运行模式: ").strip()

    if choice == '1':
        print(f"{SUCCESS_COLOR}正在启动 Web 应用...")
        subprocess.run([python_cmd, 'app.py'])
    elif choice == '2':
        print(f"{SUCCESS_COLOR}正在启动本地图形化界面...")
        try:
            from utils.gui import pyqt_mode
            pyqt_mode()
        except ImportError as e:
            print(f"{ERROR_COLOR}无法启动图形化界面: {e}")
            print(f"{ACCENT_COLOR}请确保已安装 PyQt6: pip install PyQt6")
    elif choice == '0':
        print(f"{SUCCESS_COLOR}再见！")
    else:
        print(f"{ERROR_COLOR}无效选择，请重新运行程序")

if __name__ == "__main__":
    main()
