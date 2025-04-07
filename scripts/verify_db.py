#!/usr/bin/env python
# scripts/verify_db.py

import sqlite3
import os
from pathlib import Path

def verify_db():
    """验证数据库表是否存在"""
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    db_file = project_root / "stepflow.db"
    
    if not db_file.exists():
        print(f"错误: 数据库文件不存在: {db_file}")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        print(f"数据库中的表: {table_names}")
        
        # 检查必要的表是否存在
        required_tables = [
            'workflow_templates',
            'workflow_executions',
            'workflow_events',
            'timers',
            'activity_tasks',
            'workflow_visibility'
        ]
        
        missing_tables = [table for table in required_tables if table not in table_names]
        
        if missing_tables:
            print(f"错误: 缺少以下表: {missing_tables}")
            return False
        
        # 检查每个表的结构
        for table in required_tables:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            print(f"\n表 {table} 的列:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        
        print("\n数据库验证成功！所有必要的表都存在。")
        return True
    
    except sqlite3.Error as e:
        print(f"SQLite 错误: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    verify_db() 