# -*- coding: utf-8 -*-
"""Excel 解析与入库（覆盖逻辑、固定条件筛选）"""
import os
import pandas as pd
from db import get_conn
from config import EXCEL_COLUMN_MAP, FILTER_ATTRIBUTE_16


def parse_excel(file_path):
    """读取Excel并按映射重命名列，返回标准DataFrame；失败抛出异常"""
    df = pd.read_excel(file_path, engine="openpyxl")
    # 列名去除首尾空白后映射
    df.columns = [str(c).strip() for c in df.columns]
    missing = [k for k in EXCEL_COLUMN_MAP if k not in df.columns]
    if missing:
        raise ValueError(f"Excel缺失必要列: {missing}")
    df = df.rename(columns=EXCEL_COLUMN_MAP)
    return df


def _norm_month(val):
    """将发生月份/列账月份统一为 'YYYY-MM' 字符串；无法解析或异常年份返回 None"""
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s.isdigit() and len(s) == 6:
        y, m = s[:4], s[4:]
        if 2015 <= int(y) <= 2100 and 1 <= int(m) <= 12:
            return f"{y}-{m}"
    if s.isdigit() and len(s) == 8:
        y, m = s[:4], s[4:6]
        if 2015 <= int(y) <= 2100 and 1 <= int(m) <= 12:
            return f"{y}-{m}"
    try:
        ts = pd.to_datetime(val, errors="coerce")
        if pd.isna(ts):
            return None
        y = ts.year
        if y < 2015 or y > 2100:
            return None
        return ts.strftime("%Y-%m")
    except Exception:
        return s if len(s) >= 7 and s[:4].isdigit() and 2015 <= int(s[:4]) <= 2100 else None


def _norm_num(val):
    if pd.isna(val):
        return 0.0
    try:
        return float(val)
    except Exception:
        return 0.0


def import_records(df):
    """
    入库主流程：
    1. 过滤 attribute_16 == 异网标品
    2. 规整月份/数值
    3. 按发生月份分组，先删后插（事务原子性）
    返回 (插入行数, 覆盖月份数)
    """
    df = df[df["attribute_16"] == FILTER_ATTRIBUTE_16].copy()
    if df.empty:
        return 0, 0

    df["occurrence_month"] = df["occurrence_month"].apply(_norm_month)
    df["billing_month"] = df["billing_month"].apply(_norm_month)
    df["billing_amount"] = df["billing_amount"].apply(_norm_num)
    df["usage_volume"] = df["usage_volume"].apply(_norm_num)
    df = df[df["occurrence_month"].notna() & df["city_company"].notna()]
    if df.empty:
        return 0, 0

    conn = get_conn()
    inserted = 0
    months_covered = set()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN")
        for month, group in df.groupby("occurrence_month"):
            # 覆盖逻辑：先删该月全部旧记录
            cur.execute("DELETE FROM customer_billing WHERE occurrence_month = ?", (month,))
            months_covered.add(month)
            for _, row in group.iterrows():
                cur.execute("""
                    INSERT INTO customer_billing
                    (customer_name, city_company, account_type, email, usage_volume,
                     occurrence_month, billing_amount, product_name, billing_month, attribute_16)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get("customer_name", "")),
                    str(row.get("city_company", "")),
                    str(row.get("account_type", "")) if pd.notna(row.get("account_type")) else "",
                    str(row.get("email", "")) if pd.notna(row.get("email")) else "",
                    float(row.get("usage_volume", 0.0)),
                    str(row["occurrence_month"]),
                    float(row.get("billing_amount", 0.0)),
                    str(row.get("product_name", "")) if pd.notna(row.get("product_name")) else "",
                    str(row["billing_month"]) if row["billing_month"] else "",
                    str(row.get("attribute_16", "")),
                ))
                inserted += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return inserted, len(months_covered)


def process_uploaded_files(file_paths):
    """批量处理多个Excel文件，返回汇总结果字典"""
    total_inserted = 0
    total_months = set()
    errors = []
    for fp in file_paths:
        fname = os.path.basename(fp)
        try:
            df = parse_excel(fp)
            ins, mc = import_records(df)
            total_inserted += ins
            # 记录被覆盖的月份用于结果展示
            df_months = df[df["attribute_16"] == FILTER_ATTRIBUTE_16]["occurrence_month"]
            for m in df_months:
                m = _norm_month(m)
                if m:
                    total_months.add(m)
        except Exception as e:
            errors.append(f"{fname}: {e}")
        finally:
            try:
                os.remove(fp)
            except OSError:
                pass
    return {
        "inserted": total_inserted,
        "months": sorted(total_months),
        "errors": errors,
    }
