# -*- coding: utf-8 -*-
"""集中配置：所有可调参数统一放置于此"""
import os

# 基础路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "billing.db")
UPLOAD_TMP_DIR = os.path.join(BASE_DIR, "tmp_upload")

# 业务参数
FILTER_ATTRIBUTE_16 = "异网标品"      # 固定筛选条件，不可修改
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 单次上传上限 200MB

# Excel 列名 → 数据库字段 映射
EXCEL_COLUMN_MAP = {
    "客户名称": "customer_name",
    "市公司": "city_company",
    "账户类型": "account_type",
    "客户邮箱": "email",
    "用量": "usage_volume",
    "发生月份": "occurrence_month",
    "计费列账金额(扣除坏账率)": "billing_amount",
    "产品名称": "product_name",
    "列账月": "billing_month",
    "属性16": "attribute_16",
}

# 数据库所有业务字段（按表格展示顺序）
DETAIL_COLUMNS = [
    "id", "customer_name", "city_company", "account_type", "email",
    "usage_volume", "occurrence_month", "billing_amount",
    "product_name", "billing_month", "attribute_16", "is_settled",
]
DETAIL_COLUMNS_CN = {
    "id": "ID",
    "customer_name": "客户名称",
    "city_company": "市公司",
    "account_type": "账户类型",
    "email": "客户邮箱",
    "usage_volume": "用量",
    "occurrence_month": "发生月份",
    "billing_amount": "计费列账金额(扣除坏账率)",
    "product_name": "产品名称",
    "billing_month": "列账月",
    "attribute_16": "属性16",
    "is_settled": "是否销账",
}
