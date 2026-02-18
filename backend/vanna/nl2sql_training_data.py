"""
训练数据定义
包含文档、DDL、SQL 示例
"""

# ==================== 文档数据 ====================

def get_documentations():
    """获取所有文档数据"""
    
    documentation_product = """
表名: dim_product
描述: 存储所有电子产品的基本信息，用于产品分析
字段:
- product_sk (BIGINT, 主键): 产品唯一标识，代理键
- product_name (VARCHAR): 产品完整名称，如"OPPO 投影仪 X4"
- brand (VARCHAR): 品牌名称，如"OPPO"、"小米"、"苹果"、"华为"
- category (VARCHAR): 产品分类，如"投影仪"、"智能手机"、"电视"、"耳机"
记录数: 800
"""

    documentation_location = """
表名: dim_location
描述: 存储发货城市信息
字段:
- location_sk (BIGINT, 主键): 地点唯一标识，代理键
- location_name (VARCHAR): 城市名称，包含"北京"、"上海"、"广州"、"深圳"、"杭州"、"武汉"、"成都"
记录数: 7
"""

    documentation_calendar = """
表名: dim_calendar
描述: 时间维度表，预计算了日期的各种属性，用于时间序列分析
字段:
- date_id (VARCHAR(8), 主键): 日期ID，格式YYYYMMDD，如"20240209"
- date (DATE): 标准日期格式
- year (INT): 年份，如2024
- month (INT): 月份，1-12
- day (INT): 日期，1-31
- day_of_week (INT): 星期几，0=周一, 1=周二, ..., 6=周日
- month_name (VARCHAR): 月份英文名，如"February"、"December"
- day_name (VARCHAR): 星期英文名，如"Monday"、"Friday"
记录数: 366
用途: 支持按年/月/周/日等多粒度时间分析，以及工作日/周末对比
"""

    documentation_fact_sales = """
表名: fact_sales_electronics
描述: 电子产品销售事实表，存储每笔交易的详细数据和度量指标
字段:
- product_sk (BIGINT, 外键): 关联 dim_product.product_sk
- location_sk (BIGINT, 外键): 关联 dim_location.location_sk，表示发货地
- date_id (VARCHAR(8), 外键): 关联 dim_calendar.date_id，表示交易日期
- price (DOUBLE): 实际销售价格(元)，核心度量
- quantity (DOUBLE): 销售数量(件)，核心度量
- list_price (DOUBLE): 原价(元)
- discount_rate (DOUBLE): 折扣率，如31.85表示31.85%的折扣
- review_count (DOUBLE): 评价数量
- positive_rate (DOUBLE): 好评率，如97.64表示97.64%好评
- warranty_months (DOUBLE): 保修期(月)，如6、12、18、24
记录数: 55,231
重要指标:
- GMV(成交总额) = price × quantity
- 平均折扣率 = AVG(discount_rate)
- 平均好评率 = AVG(positive_rate)
"""

    documentation_relationships = """
数据模型: 星型模型(Star Schema)
表关系:
1. fact_sales_electronics.product_sk → dim_product.product_sk
2. fact_sales_electronics.location_sk → dim_location.location_sk
3. fact_sales_electronics.date_id → dim_calendar.date_id

查询规则:
- 获取产品名称、品牌、分类时，必须 JOIN dim_product
- 获取城市名称时，必须 JOIN dim_location
- 进行时间维度分析时，必须 JOIN dim_calendar
- 计算GMV使用: SUM(price * quantity)
- 外键不会自动关联，需要显式编写 JOIN 语句

常见查询模式:
- 品牌销量: JOIN dim_product, GROUP BY brand
- 城市分布: JOIN dim_location, GROUP BY location_name
- 时间趋势: JOIN dim_calendar, GROUP BY year/month
- 多维分析: 同时 JOIN 多个维度表
"""

    documentation_examples = """
常见业务问题与SQL模式:
1. "哪个品牌销量最高?" 
   → SELECT brand FROM dim_product JOIN fact_sales GROUP BY brand ORDER BY SUM(quantity) DESC

2. "北京的总销售额是多少?"
   → SELECT SUM(price*quantity) FROM fact_sales JOIN dim_location WHERE location_name='北京'

3. "2024年每月的销量趋势"
   → SELECT month, SUM(quantity) FROM fact_sales JOIN dim_calendar WHERE year=2024 GROUP BY month

4. "周末和工作日的销售对比"
   → SELECT CASE WHEN day_of_week IN (5,6) THEN '周末' ELSE '工作日' END FROM dim_calendar JOIN fact_sales

5. "平均折扣率最高的产品类别"
   → SELECT category, AVG(discount_rate) FROM dim_product JOIN fact_sales GROUP BY category
"""
    documentation_1 = """
    location_sk 的意思是商品发货地的意思。
    """

    # ==================== 服装销售数据文档 ====================
    
    documentation_clothing_product = """
表名: dim_clothing_product
描述: 存储所有服装产品的基本信息，用于服装商品分析
字段:
- product_sk (INT, 主键): 产品唯一标识，代理键
- product_name (VARCHAR): 产品完整名称，如"Puma 休闲oversize百褶裙"
- brand (VARCHAR): 品牌名称，如"Puma"、"ZARA"、"Dior"、"Calvin Klein"、"波司登"、"美特斯邦威"等
- category (VARCHAR): 产品大类，如"裙装"、"运动"、"内衣"、"下装"、"上装"、"配饰"
- sub_category (VARCHAR): 产品子类，如"百褶裙"、"运动内衣"、"睡衣"、"打底裤"、"连衣裙"、"袖扣"、"西装"、"运动裤"等
- material (VARCHAR): 材质，如"蕾丝"、"牛仔布"、"羊毛"、"涤纶"、"混纺"、"雪纺"等
- color (VARCHAR): 颜色，如"卡其"、"绿色"、"银灰"、"粉色"、"印花"、"香槟金"、"白色"、"深蓝"、"黑色"等
- size (VARCHAR): 尺码，如"L"、"XS"、"XXL"、"32"、"S"、"M"等
- season (VARCHAR): 适用季节，如"冬季"、"春季"、"秋季"、"四季"、"夏季"
记录数: 100,000
"""

    documentation_clothing_customer = """
表名: dim_clothing_customer
描述: 存储客户信息，用于客户画像和消费行为分析
字段:
- customer_sk (INT, 主键): 客户唯一标识，代理键
- customer_name (VARCHAR): 客户姓名
- customer_gender (VARCHAR): 客户性别，"男"或"女"
- customer_age (INT): 客户年龄
- customer_phone (VARCHAR): 客户手机号
- customer_address (VARCHAR): 客户地址（省市区信息）
用途: 支持客户性别、年龄段分析，地域分布统计
"""

    documentation_clothing_calendar = """
表名: dim_clothing_calendar
描述: 时间维度表，预计算了日期的各种属性，用于时间序列分析
字段:
- date_id (VARCHAR(8), 主键): 日期ID，格式YYYYMMDD
- date (DATE): 标准日期格式
- year (INT): 年份
- month (INT): 月份，1-12
- day (INT): 日期，1-31
- season (VARCHAR): 销售季节（来自原始数据的"季节"字段）
用途: 支持按年/月/日/季节等多粒度时间分析
"""

    documentation_fact_sales_clothing = """
表名: fact_sales_clothing
描述: 服装销售事实表，存储每笔订单的详细交易数据
字段:
- order_id (VARCHAR): 订单唯一标识
- date_id (VARCHAR(8), 外键): 关联 dim_clothing_calendar.date_id，表示销售日期
- product_sk (INT, 外键): 关联 dim_clothing_product.product_sk
- customer_sk (INT, 外键): 关联 dim_clothing_customer.customer_sk
- price (FLOAT): 实际售价(元)，核心度量
- quantity (INT): 销售数量(件)，核心度量
- total_amount (FLOAT): 订单总金额(元) = price × quantity
- list_price (FLOAT): 标准价格(元)
- discount_amount (FLOAT): 优惠金额(元)
- channel (VARCHAR): 销售渠道，如"线上"、"线下"
- payment (VARCHAR): 支付方式，如"微信支付"、"支付宝"、"银行卡"等
- is_returned (VARCHAR): 是否退换货，"是"或"否"
- return_reason (VARCHAR): 退换货原因
- review_star (INT): 评价星级，1-5星
- sales_person (VARCHAR): 销售人员姓名
- logistics (VARCHAR): 物流公司名称
记录数: 1,000,000
重要指标:
- GMV(成交总额) = SUM(total_amount) 或 SUM(price × quantity)
- 平均客单价 = AVG(total_amount)
- 退货率 = COUNT(is_returned='是') / COUNT(*)
- 平均评价星级 = AVG(review_star)
- 折扣率 = discount_amount / list_price
"""

    documentation_clothing_relationships = """
数据模型: 星型模型(Star Schema)
表关系:
1. fact_sales_clothing.product_sk → dim_clothing_product.product_sk
2. fact_sales_clothing.customer_sk → dim_clothing_customer.customer_sk
3. fact_sales_clothing.date_id → dim_clothing_calendar.date_id

查询规则:
- 获取产品名称、品牌、品类、材质、颜色等信息时，必须 JOIN dim_clothing_product
- 获取客户姓名、性别、年龄、地址等信息时，必须 JOIN dim_clothing_customer
- 进行时间维度分析时，必须 JOIN dim_clothing_calendar
- 计算GMV使用: SUM(total_amount) 或 SUM(price * quantity)
- 外键不会自动关联，需要显式编写 JOIN 语句

常见查询模式:
- 品牌销量: JOIN dim_clothing_product, GROUP BY brand
- 品类分析: JOIN dim_clothing_product, GROUP BY category/sub_category
- 客户画像: JOIN dim_clothing_customer, GROUP BY customer_gender/customer_age
- 时间趋势: JOIN dim_clothing_calendar, GROUP BY year/month
- 渠道对比: GROUP BY channel
- 退货分析: WHERE is_returned='是', GROUP BY return_reason
"""

    documentation_clothing_examples = """
常见业务问题与SQL模式:
1. "哪个品牌的服装销量最高?" 
   → SELECT brand FROM dim_clothing_product JOIN fact_sales_clothing GROUP BY brand ORDER BY SUM(quantity) DESC

2. "女性客户的平均消费金额是多少?"
   → SELECT AVG(total_amount) FROM fact_sales_clothing JOIN dim_clothing_customer WHERE customer_gender='女'

3. "2024年每月的销售额趋势"
   → SELECT year, month, SUM(total_amount) FROM fact_sales_clothing JOIN dim_clothing_calendar WHERE year=2024 GROUP BY year, month

4. "线上和线下渠道的销售对比"
   → SELECT channel, SUM(total_amount), COUNT(*) FROM fact_sales_clothing GROUP BY channel

5. "退货率最高的产品类别"
   → SELECT category, COUNT(CASE WHEN is_returned='是' THEN 1 END)/COUNT(*) FROM fact_sales_clothing JOIN dim_clothing_product GROUP BY category

6. "不同年龄段客户的购买偏好"
   → SELECT CASE WHEN customer_age<25 THEN '青年' WHEN customer_age<40 THEN '中年' ELSE '中老年' END, category FROM fact_sales_clothing JOIN dim_clothing_customer JOIN dim_clothing_product

7. "冬季服装的销售情况"
   → SELECT brand, SUM(quantity) FROM fact_sales_clothing JOIN dim_clothing_product WHERE season='冬季' GROUP BY brand

8. "评价星级分布"
   → SELECT review_star, COUNT(*) FROM fact_sales_clothing GROUP BY review_star ORDER BY review_star
"""

    return [
        documentation_product,
        documentation_location,
        documentation_calendar,
        documentation_fact_sales,
        documentation_relationships,
        documentation_examples,
        documentation_1,
        # 服装销售数据文档
        documentation_clothing_product,
        documentation_clothing_customer,
        documentation_clothing_calendar,
        documentation_fact_sales_clothing,
        documentation_clothing_relationships,
        documentation_clothing_examples,
    ]


# ==================== DDL 数据 ====================

def get_ddls():
    """获取所有 DDL 数据"""
    
    ddl_product = """
CREATE TABLE dim_product (
    product_sk      BIGINT NOT NULL COMMENT '产品唯一标识，代理键',
    product_name    VARCHAR(255) COMMENT '产品完整名称，如"OPPO 投影仪 X4"',
    brand           VARCHAR(100) COMMENT '品牌名称，如"OPPO"、"小米"、"苹果"、"华为"',
    category        VARCHAR(100) COMMENT '产品分类，如"投影仪"、"智能手机"、"电视"、"耳机"',
    PRIMARY KEY (product_sk)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品维度表：存储所有电子产品的基本信息';
"""

    ddl_location = """
CREATE TABLE dim_location (
    location_sk     BIGINT NOT NULL COMMENT '地点唯一标识，代理键',
    location_name   VARCHAR(100) COMMENT '城市名称，包含"北京"、"上海"、"广州"、"深圳"、"杭州"、"武汉"、"成都"',
    PRIMARY KEY (location_sk)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='地点维度表：存储发货城市信息';
"""

    ddl_calendar = """
CREATE TABLE dim_calendar (
    date_id     VARCHAR(8) NOT NULL COMMENT '日期ID，格式YYYYMMDD，如"20240209"',
    date        DATE COMMENT '标准日期格式',
    year        INT COMMENT '年份，如2024',
    month       INT COMMENT '月份，1-12',
    day         INT COMMENT '日期，1-31',
    day_of_week INT COMMENT '星期几，0=周一, 1=周二, ..., 6=周日',
    month_name  VARCHAR(20) COMMENT '月份英文名，如"February"、"December"',
    day_name    VARCHAR(20) COMMENT '星期英文名，如"Monday"、"Friday"',
    PRIMARY KEY (date_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='时间维度表：预计算了日期的各种属性，用于时间序列分析';
"""

    ddl_fact_sales = """
CREATE TABLE fact_sales_electronics (
    product_sk      BIGINT COMMENT '关联 dim_product.product_sk',
    location_sk     BIGINT COMMENT '关联 dim_location.location_sk，表示发货地',
    date_id         VARCHAR(8) COMMENT '关联 dim_calendar.date_id，表示交易日期',
    price           DOUBLE COMMENT '实际销售价格(元)，核心度量',
    quantity        DOUBLE COMMENT '销售数量(件)，核心度量',
    list_price      DOUBLE COMMENT '原价(元)',
    discount_rate   DOUBLE COMMENT '折扣率，如31.85表示31.85%的折扣',
    review_count    DOUBLE COMMENT '评价数量',
    positive_rate   DOUBLE COMMENT '好评率，如97.64表示97.64%好评',
    warranty_months DOUBLE COMMENT '保修期(月)，如6、12、18、24',
    KEY idx_prod (product_sk),
    KEY idx_loc  (location_sk),
    KEY idx_date (date_id),
    CONSTRAINT fk_prod FOREIGN KEY (product_sk) REFERENCES dim_product(product_sk),
    CONSTRAINT fk_loc  FOREIGN KEY (location_sk) REFERENCES dim_location(location_sk),
    CONSTRAINT fk_date FOREIGN KEY (date_id)   REFERENCES dim_calendar(date_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售事实表：存储每笔交易的详细数据和度量指标';
"""

    # ==================== 服装销售数据 DDL ====================
    
    ddl_clothing_product = """
CREATE TABLE dim_clothing_product (
    product_sk INT PRIMARY KEY COMMENT '产品唯一标识，代理键',
    product_name VARCHAR(255) COMMENT '产品完整名称，如"Puma 休闲oversize百褶裙"',
    brand VARCHAR(100) COMMENT '品牌名称，如"Puma"、"ZARA"、"Dior"',
    category VARCHAR(100) COMMENT '产品大类，如"裙装"、"运动"、"内衣"',
    sub_category VARCHAR(100) COMMENT '产品子类，如"百褶裙"、"运动内衣"',
    material VARCHAR(100) COMMENT '材质，如"蕾丝"、"牛仔布"、"羊毛"',
    color VARCHAR(50) COMMENT '颜色，如"卡其"、"绿色"、"银灰"',
    size VARCHAR(20) COMMENT '尺码，如"L"、"XS"、"XXL"、"32"',
    season VARCHAR(20) COMMENT '适用季节，如"冬季"、"春季"、"秋季"、"四季"、"夏季"'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='服装产品维度表';
"""

    ddl_clothing_customer = """
CREATE TABLE dim_clothing_customer (
    customer_sk INT PRIMARY KEY COMMENT '客户唯一标识，代理键',
    customer_name VARCHAR(100) COMMENT '客户姓名',
    customer_gender VARCHAR(10) COMMENT '客户性别，"男"或"女"',
    customer_age INT COMMENT '客户年龄',
    customer_phone VARCHAR(20) COMMENT '客户手机号',
    customer_address VARCHAR(255) COMMENT '客户地址（省市区信息）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户维度表';
"""

    ddl_clothing_calendar = """
CREATE TABLE dim_clothing_calendar (
    date_id VARCHAR(8) PRIMARY KEY COMMENT '日期ID，格式YYYYMMDD',
    date DATE COMMENT '标准日期格式',
    year INT COMMENT '年份',
    month INT COMMENT '月份，1-12',
    day INT COMMENT '日期，1-31',
    season VARCHAR(20) COMMENT '销售季节'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='时间维度表';
"""

    ddl_fact_sales_clothing = """
CREATE TABLE fact_sales_clothing (
    order_id VARCHAR(50) COMMENT '订单唯一标识',
    date_id VARCHAR(8) COMMENT '关联 dim_clothing_calendar.date_id，表示销售日期',
    product_sk INT COMMENT '关联 dim_clothing_product.product_sk',
    customer_sk INT COMMENT '关联 dim_clothing_customer.customer_sk',
    price FLOAT COMMENT '实际售价(元)，核心度量',
    quantity INT COMMENT '销售数量(件)，核心度量',
    total_amount FLOAT COMMENT '订单总金额(元)',
    list_price FLOAT COMMENT '标准价格(元)',
    discount_amount FLOAT COMMENT '优惠金额(元)',
    channel VARCHAR(50) COMMENT '销售渠道，如"线上"、"线下"',
    payment VARCHAR(50) COMMENT '支付方式',
    is_returned VARCHAR(10) COMMENT '是否退换货，"是"或"否"',
    return_reason VARCHAR(50) COMMENT '退换货原因',
    review_star INT COMMENT '评价星级，1-5星',
    sales_person VARCHAR(50) COMMENT '销售人员姓名',
    logistics VARCHAR(50) COMMENT '物流公司名称',
    FOREIGN KEY (date_id) REFERENCES dim_clothing_calendar(date_id),
    FOREIGN KEY (product_sk) REFERENCES dim_clothing_product(product_sk),
    FOREIGN KEY (customer_sk) REFERENCES dim_clothing_customer(customer_sk)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='服装销售事实表';
"""

    return [
        ddl_product,
        ddl_location,
        ddl_calendar,
        ddl_fact_sales,
        # 服装销售数据 DDL
        ddl_clothing_product,
        ddl_clothing_customer,
        ddl_clothing_calendar,
        ddl_fact_sales_clothing,
    ]


# ==================== SQL 示例数据 ====================

def get_sql_examples():
    """获取 SQL 示例（需逐个训练）"""
    
    return [
        # 1. 品牌销量排名
        '''
SELECT 
    p.brand,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.price * f.quantity), 2) AS total_gmv
FROM fact_sales_electronics f
JOIN dim_product p ON f.product_sk = p.product_sk
GROUP BY p.brand
ORDER BY total_quantity DESC
LIMIT 10
''',
        # 2. 城市销售统计
        '''
SELECT 
    l.location_name,
    ROUND(SUM(f.price * f.quantity), 2) AS total_gmv,
    SUM(f.quantity) AS total_quantity,
    COUNT(*) AS order_count
FROM fact_sales_electronics f
JOIN dim_location l ON f.location_sk = l.location_sk
WHERE l.location_name = '北京'
GROUP BY l.location_name
''',
        # 3. 月度趋势
        '''
SELECT 
    c.year,
    c.month,
    c.month_name,
    SUM(f.quantity) AS monthly_quantity,
    ROUND(SUM(f.price * f.quantity), 2) AS monthly_gmv
FROM fact_sales_electronics f
JOIN dim_calendar c ON f.date_id = c.date_id
WHERE c.year = 2024
GROUP BY c.year, c.month, c.month_name
ORDER BY c.month
''',
        # 4. 品牌-城市交叉分析
        '''
SELECT 
    p.brand,
    l.location_name,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.price * f.quantity), 2) AS total_gmv,
    ROUND(AVG(f.price), 2) AS avg_price
FROM fact_sales_electronics f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_location l ON f.location_sk = l.location_sk
GROUP BY p.brand, l.location_name
ORDER BY total_quantity DESC
LIMIT 20
''',
        # 5. 周末vs工作日
        '''
SELECT 
    CASE 
        WHEN c.day_of_week IN (5, 6) THEN '周末'
        ELSE '工作日'
    END AS day_type,
    COUNT(*) AS order_count,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.price * f.quantity), 2) AS total_gmv,
    ROUND(AVG(f.price * f.quantity), 2) AS avg_order_value
FROM fact_sales_electronics f
JOIN dim_calendar c ON f.date_id = c.date_id
GROUP BY day_type
''',
        # ==================== 服装销售数据 SQL 示例 ====================
        # 6. 服装品牌销量排名
        '''
SELECT 
    p.brand,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.total_amount), 2) AS total_gmv,
    COUNT(DISTINCT f.order_id) AS order_count
FROM fact_sales_clothing f
JOIN dim_clothing_product p ON f.product_sk = p.product_sk
GROUP BY p.brand
ORDER BY total_quantity DESC
LIMIT 10
''',
        # 7. 客户性别消费分析
        '''
SELECT 
    c.customer_gender,
    COUNT(DISTINCT f.order_id) AS order_count,
    ROUND(AVG(f.total_amount), 2) AS avg_order_value,
    ROUND(SUM(f.total_amount), 2) AS total_gmv
FROM fact_sales_clothing f
JOIN dim_clothing_customer c ON f.customer_sk = c.customer_sk
GROUP BY c.customer_gender
''',
        # 8. 服装品类销售趋势
        '''
SELECT 
    cal.year,
    cal.month,
    p.category,
    SUM(f.quantity) AS monthly_quantity,
    ROUND(SUM(f.total_amount), 2) AS monthly_gmv
FROM fact_sales_clothing f
JOIN dim_clothing_product p ON f.product_sk = p.product_sk
JOIN dim_clothing_calendar cal ON f.date_id = cal.date_id
GROUP BY cal.year, cal.month, p.category
ORDER BY cal.year, cal.month, monthly_gmv DESC
''',
        # 9. 销售渠道对比
        '''
SELECT 
    f.channel,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.total_amount), 2) AS total_gmv,
    ROUND(AVG(f.total_amount), 2) AS avg_order_value
FROM fact_sales_clothing f
GROUP BY f.channel
''',
        # 10. 退货分析
        '''
SELECT 
    p.category,
    p.sub_category,
    COUNT(CASE WHEN f.is_returned = '是' THEN 1 END) AS return_count,
    COUNT(*) AS total_count,
    ROUND(COUNT(CASE WHEN f.is_returned = '是' THEN 1 END) * 100.0 / COUNT(*), 2) AS return_rate,
    f.return_reason
FROM fact_sales_clothing f
JOIN dim_clothing_product p ON f.product_sk = p.product_sk
WHERE f.is_returned = '是'
GROUP BY p.category, p.sub_category, f.return_reason
ORDER BY return_count DESC
LIMIT 20
''',
        # 11. 客户年龄段购买偏好
        '''
SELECT 
    CASE 
        WHEN c.customer_age < 25 THEN '18-24岁'
        WHEN c.customer_age < 35 THEN '25-34岁'
        WHEN c.customer_age < 45 THEN '35-44岁'
        ELSE '45岁以上'
    END AS age_group,
    p.category,
    COUNT(DISTINCT f.order_id) AS order_count,
    ROUND(SUM(f.total_amount), 2) AS total_gmv
FROM fact_sales_clothing f
JOIN dim_clothing_customer c ON f.customer_sk = c.customer_sk
JOIN dim_clothing_product p ON f.product_sk = p.product_sk
GROUP BY age_group, p.category
ORDER BY age_group, total_gmv DESC
''',
        # 12. 季节性服装销售分析
        '''
SELECT 
    p.season,
    p.category,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.total_amount), 2) AS total_gmv,
    ROUND(AVG(f.review_star), 2) AS avg_rating
FROM fact_sales_clothing f
JOIN dim_clothing_product p ON f.product_sk = p.product_sk
GROUP BY p.season, p.category
ORDER BY p.season, total_gmv DESC
''',
        # 13. 评价星级分布
        '''
SELECT 
    f.review_star,
    COUNT(*) AS order_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage
FROM fact_sales_clothing f
GROUP BY f.review_star
ORDER BY f.review_star DESC
''',
        # 14. 支付方式偏好分析
        '''
SELECT 
    f.payment,
    COUNT(DISTINCT f.order_id) AS order_count,
    ROUND(SUM(f.total_amount), 2) AS total_gmv,
    ROUND(AVG(f.total_amount), 2) AS avg_order_value
FROM fact_sales_clothing f
GROUP BY f.payment
ORDER BY order_count DESC
''',
        # 15. 销售人员业绩排名
        '''
SELECT 
    f.sales_person,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.total_amount), 2) AS total_gmv,
    ROUND(AVG(f.review_star), 2) AS avg_rating
FROM fact_sales_clothing f
GROUP BY f.sales_person
ORDER BY total_gmv DESC
LIMIT 20
''',
    ]