#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MySQL 数据库连接测试脚本
用于测试 NL2SQL 系统配置的 MySQL 数据库是否能够正常连接
"""

import pymysql
from pymysql.cursors import DictCursor
import sys


def load_config():
    """从 .env 文件加载配置"""
    config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'ai_sales_data',
        'user': 'root',
        'password': 'csd123456'
    }

    # 尝试从 .env 文件读取配置
    env_path = '/home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/backend/.env'
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key == 'MYSQL_HOST':
                        config['host'] = value
                    elif key == 'MYSQL_PORT':
                        config['port'] = int(value)
                    elif key == 'MYSQL_DATABASE':
                        config['database'] = value
                    elif key == 'MYSQL_USER':
                        config['user'] = value
                    elif key == 'MYSQL_PASSWORD':
                        config['password'] = value
    except FileNotFoundError:
        print(f"Warning: .env file not found at {env_path}, using default config")

    return config


def test_connection(config):
    """测试数据库连接"""
    print("=" * 50)
    print("MySQL 数据库连接测试")
    print("=" * 50)
    print(f"Host: {config['host']}")
    print(f"Port: {config['port']}")
    print(f"Database: {config['database']}")
    print(f"User: {config['user']}")
    print("-" * 50)

    try:
        # 建立连接
        connection = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4',
            cursorclass=DictCursor
        )

        print("[✓] 数据库连接成功!")

        # 获取数据库版本
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() as version")
            version = cursor.fetchone()
            print(f"[✓] MySQL 版本: {version['version']}")

        # 显示数据库中的表
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_names = [list(t.values())[0] for t in tables]
            print(f"[✓] 数据库共有 {len(table_names)} 张表:")
            for table in table_names:
                # 获取表的记录数
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()['count']
                print(f"    - {table}: {count} 条记录")

        # 执行一个简单的查询测试
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM products LIMIT 3")
            products = cursor.fetchall()
            print(f"\n[✓] 查询 products 表前 3 条数据:")
            for i, product in enumerate(products, 1):
                print(f"    {i}. {product}")

        connection.close()
        print("\n" + "=" * 50)
        print("测试完成! 数据库连接正常。")
        print("=" * 50)
        return True

    except pymysql.ConnectError as e:
        print(f"\n[✗] 数据库连接失败!")
        print(f"错误信息: {e}")
        return False
    except Exception as e:
        print(f"\n[✗] 执行测试时发生错误!")
        print(f"错误信息: {e}")
        return False


if __name__ == "__main__":
    config = load_config()
    success = test_connection(config)
    sys.exit(0 if success else 1)
