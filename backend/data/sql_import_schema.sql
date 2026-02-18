-- 创建销售分析数据库
CREATE DATABASE IF NOT EXISTS ai_sales_data
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ai_sales_data;

-- 1. 员工信息表 - 存储公司员工基本信息
CREATE TABLE employees (
    employee_id VARCHAR(10) PRIMARY KEY COMMENT '员工编号，主键',
    name VARCHAR(50) NOT NULL COMMENT '员工姓名',
    department VARCHAR(50) NOT NULL COMMENT '所属部门',
    position VARCHAR(50) NOT NULL COMMENT '职位',
    hire_date DATE NOT NULL COMMENT '入职日期',
    salary DECIMAL(10,2) NOT NULL COMMENT '薪资',
    performance_score INT NOT NULL COMMENT '绩效评分（0-100分）',
    city VARCHAR(50) NOT NULL COMMENT '所在城市'
) COMMENT = '员工基本信息表';

-- 2. 客户信息表 - 存储客户基本信息和消费记录
CREATE TABLE customers (
    customer_id VARCHAR(10) PRIMARY KEY COMMENT '客户编号，主键',
    name VARCHAR(50) NOT NULL COMMENT '客户姓名',
    age INT NOT NULL COMMENT '年龄',
    gender ENUM('男', '女') NOT NULL COMMENT '性别',
    city VARCHAR(50) NOT NULL COMMENT '所在城市',
    membership_level ENUM('白银', '黄金', '钻石') NOT NULL COMMENT '会员等级',
    registration_date DATE NOT NULL COMMENT '注册日期',
    total_consumption DECIMAL(12,2) NOT NULL COMMENT '消费总额'
) COMMENT = '客户信息表';

-- 3. 产品目录表 - 存储产品基本信息
CREATE TABLE products (
    product_id VARCHAR(10) PRIMARY KEY COMMENT '产品编号，主键',
    product_name VARCHAR(100) NOT NULL COMMENT '产品名称',
    category VARCHAR(50) NOT NULL COMMENT '产品类别',
    price DECIMAL(10,2) NOT NULL COMMENT '单价',
    stock_quantity INT NOT NULL COMMENT '库存数量',
    supplier VARCHAR(100) NOT NULL COMMENT '供应商',
    rating DECIMAL(3,1) NOT NULL COMMENT '产品评分（5分制）',
    update_date DATE NOT NULL COMMENT '信息更新日期'
) COMMENT = '产品目录表';

-- 4. 销售订单主表 - 存储订单基本信息
CREATE TABLE sales_orders (
    order_id VARCHAR(10) PRIMARY KEY COMMENT '订单编号，主键',
    customer_id VARCHAR(10) NOT NULL COMMENT '客户编号，外键关联customers表',
    order_date DATE NOT NULL COMMENT '订单日期',
    total_amount DECIMAL(10,2) NOT NULL COMMENT '订单总金额',
    order_status ENUM('待发货', '配送中', '已完成') NOT NULL COMMENT '订单状态',
    payment_method ENUM('支付宝', '微信支付', '信用卡') NOT NULL COMMENT '支付方式',
    shipping_address VARCHAR(200) NOT NULL COMMENT '配送地址',
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) COMMENT = '销售订单主表';

-- 5. 订单明细表 - 存储订单商品明细（支持一个订单多个商品）
CREATE TABLE order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '订单明细ID，自增主键',
    order_id VARCHAR(10) NOT NULL COMMENT '订单编号，外键关联sales_orders表',
    product_id VARCHAR(10) NOT NULL COMMENT '产品编号，外键关联products表',
    quantity INT NOT NULL DEFAULT 1 COMMENT '购买数量',
    unit_price DECIMAL(10,2) NOT NULL COMMENT '商品单价',
    FOREIGN KEY (order_id) REFERENCES sales_orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
) COMMENT = '订单明细表';

-- 6. 创建视图：销售订单完整视图（包含客户和产品信息）
CREATE VIEW sales_order_details AS
SELECT
    so.order_id,
    so.order_date,
    so.total_amount,
    so.order_status,
    so.payment_method,
    c.customer_id,
    c.name as customer_name,
    c.membership_level,
    p.product_id,
    p.product_name,
    p.category,
    oi.quantity,
    oi.unit_price,
    (oi.quantity * oi.unit_price) as item_total
FROM sales_orders so
JOIN customers c ON so.customer_id = c.customer_id
JOIN order_items oi ON so.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id;

-- 插入示例数据（根据文档内容）

-- 插入员工数据
INSERT INTO employees VALUES
('E001','张三','销售部','销售经理','2020-03-15',15000.00,90,'北京'),
('E002','李四','技术部','高级工程师','2019-06-20',18000.00,95,'上海'),
('E015','韩七','财务部','财务经理','2019-05-30',19000.00,96,'广州');

-- 插入客户数据
INSERT INTO customers VALUES
('C001','张伟',28,'男','北京','黄金','2023-01-15',15680.50),
('C002','李娜',35,'女','上海','钻石','2022-08-22',28950.00),
('C020','沈涛',31,'男','郑州','黄金','2023-02-05',13450.00);

-- 插入产品数据
INSERT INTO products VALUES
('P001','华为Mate60手机','电子产品',5999.00,120,'华为科技',4.8,'2024-01-15'),
('P002','小米电视55寸','电子产品',2899.00,85,'小米集团',4.6,'2024-01-18'),
('P020','阿迪达斯运动服','服饰鞋包',599.00,300,'阿迪达斯中国',4.5,'2024-01-27');

-- 插入销售订单数据（需要先插入客户数据）
INSERT INTO sales_orders VALUES
('S001','C001','2024-01-20',5999.00,'已完成','支付宝','北京市朝阳区建国路88号'),
('S002','C002','2024-01-22',6499.00,'已完成','微信支付','上海市浦东新区陆家嘴环路1000号'),
('S025','C020','2024-02-15',1798.00,'配送中','支付宝','郑州市金水区花园路39号');

-- 插入订单明细数据（需要先插入订单和产品数据）
-- 只引用已存在的产品
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
('S001','P001',1,5999.00),
('S002','P001',1,5999.00),  -- 改为已存在的P001
('S025','P002',2,2899.00);  -- 改为已存在的P002