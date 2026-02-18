import pymysql


def get_mysql_table_schema(host, port, user, password, database, table_name):
    """
    简化版 - 获取MySQL表的CREATE TABLE语句

    Args:
        host: 数据库主机
        port: 数据库端口
        user: 用户名
        password: 密码
        database: 数据库名
        table_name: 表名

    Returns:
        CREATE TABLE语句字符串
    """
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )

        with connection.cursor() as cursor:
            cursor.execute(f"SHOW CREATE TABLE {table_name}")
            result = cursor.fetchone()

            if result:
                return result[1]  # CREATE TABLE语句在第二列
            else:
                return None

    except pymysql.Error as e:
        print(f"错误: {e}")
        return None
    finally:
        if 'connection' in locals():
            connection.close()


if __name__ == '__main__':
    tables=["employees", "customers", "products" ,"sales_orders" ,"order_items", "sales_order_details" ]
    for table in tables :
        schema = get_mysql_table_schema(
            host="localhost",
            port=3306,
            user="root",
            password="csd123456",
            database="ai_sales_data",
            table_name=table
        )

        if schema:
            print(schema)
            print('+++'*20)
