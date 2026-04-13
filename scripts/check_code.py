#!/usr/bin/env python
"""
代码质量检查脚本

运行所有代码质量检查工具:
- ruff: 代码格式和 lint
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """运行命令并返回是否成功"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    checks = [
        (["python", "-m", "ruff", "check", "core/", "utils/", "controllers/", "gui/"], "Lint (ruff)"),
        (["python", "-m", "ruff", "format", "--check", "core/", "utils/", "controllers/", "gui/"], "Format Check (ruff)"),
    ]

    results = []
    for cmd, desc in checks:
        success = run_command(cmd, desc)
        results.append((desc, success))

    # 可选检查 - 如果安装了对应模块则运行
    optional_checks = [
        (["python", "-m", "pytest", "tests/", "-v", "--tb=short"], "Unit Tests"),
        (["python", "-m", "mypy", "core/", "utils/", "--ignore-missing-imports"], "Type Check (mypy)"),
    ]

    for cmd, desc in optional_checks:
        try:
            result = subprocess.run(
                [cmd[0], "-c", f"import {cmd[2].split('.')[1]}"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                success = run_command(cmd, desc)
                results.append((desc, success))
            else:
                print(f"\n[SKIP] {desc} (module not installed)")
        except Exception:
            print(f"\n[SKIP] {desc} (module not available)")

    print("\n" + "="*60)
    print("Summary")
    print("="*60)

    all_passed = True
    for desc, success in results:
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {desc}")
        if not success:
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
