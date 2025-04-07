#!/usr/bin/env python
# scripts/fix_alembic_heads.py

import subprocess
import re
import os
from pathlib import Path

def get_alembic_heads():
    """获取当前的 Alembic 头版本"""
    result = subprocess.run(["alembic", "heads"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"获取头版本失败: {result.stderr}")
        return []
    
    # 解析输出以获取版本 ID
    heads = []
    for line in result.stdout.splitlines():
        match = re.search(r'([0-9a-f]+)(?:\s|\()', line)
        if match:
            heads.append(match.group(1))
    
    return heads

def merge_heads():
    """合并多个头版本"""
    heads = get_alembic_heads()
    
    if not heads:
        print("没有找到头版本")
        return False
    
    if len(heads) == 1:
        print(f"只有一个头版本: {heads[0]}，不需要合并")
        return True
    
    print(f"发现多个头版本: {heads}")
    
    # 创建合并迁移
    try:
        print("创建合并迁移...")
        result = subprocess.run(["alembic", "merge", "heads", "-m", "Merge multiple heads"], check=True)
        print("合并迁移创建成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"创建合并迁移失败: {e}")
        return False

def main():
    """主函数"""
    # 确保在项目根目录运行
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("修复 Alembic 多头版本问题...")
    
    if merge_heads():
        print("尝试应用迁移...")
        try:
            subprocess.run(["alembic", "upgrade", "head"], check=True)
            print("迁移应用成功")
        except subprocess.CalledProcessError as e:
            print(f"应用迁移失败: {e}")
    else:
        print("无法修复多头版本问题")

if __name__ == "__main__":
    main() 