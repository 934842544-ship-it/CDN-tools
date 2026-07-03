# -*- coding: utf-8 -*-
"""Flask 主程序：路由 + API"""
import os
import uuid
from flask import Flask, request, jsonify, render_template, redirect, url_for
from db import init_db, get_conn
from excel_parser import process_uploaded_files
from config import MAX_CONTENT_LENGTH, DETAIL_COLUMNS, DETAIL_COLUMNS_CN, FILTER_ATTRIBUTE_16

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


@app.before_request
def _ensure_db():
    # 首次请求自动初始化表结构
    if not getattr(app, "_db_inited", False):
        init_db()
        app._db_inited = True


def ok(data=None, msg="ok"):
    return jsonify({"code": 0, "msg": msg, "data": data})


def fail(msg, code=1):
    return jsonify({"code": code, "msg": msg, "data": None})


# ---------- 页面路由 ----------
@app.route("/")
def index():
    return render_template("summary.html")


@app.route("/detail")
def detail_page():
    city = request.args.get("city", "全部")
    month = request.args.get("month", "")
    return render_template("detail.html", city=city, month=month)


# ---------- API ----------
@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    if not files or all(not f.filename for f in files):
        return fail("未接收到文件")
    saved = []
    from config import UPLOAD_TMP_DIR
    for f in files:
        if not f.filename.lower().endswith(".xlsx"):
            continue
        save_name = f"{uuid.uuid4().hex}_{f.filename}"
        fp = os.path.join(UPLOAD_TMP_DIR, save_name)
        f.save(fp)
        saved.append(fp)
    if not saved:
        return fail("仅支持 .xlsx 文件")
    result = process_uploaded_files(saved)
    return ok(result, f"处理完成: 插入{result['inserted']}行")


@app.route("/api/summary")
def api_summary():
    """汇总：城市×月份金额矩阵 + 销账完成状态"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT city_company, occurrence_month, SUM(billing_amount) AS amount
            FROM customer_billing
            WHERE attribute_16 = ?
            GROUP BY city_company, occurrence_month
            ORDER BY city_company ASC, occurrence_month ASC
        """, (FILTER_ATTRIBUTE_16,)).fetchall()

        settle_rows = conn.execute("""
            SELECT city_company, occurrence_month, 
                   COUNT(*) AS total_count,
                   SUM(CASE WHEN is_settled = 1 THEN 1 ELSE 0 END) AS settled_count
            FROM customer_billing
            WHERE attribute_16 = ?
            GROUP BY city_company, occurrence_month
            ORDER BY city_company ASC, occurrence_month ASC
        """, (FILTER_ATTRIBUTE_16,)).fetchall()
    finally:
        conn.close()

    cities = sorted({r["city_company"] for r in rows})
    months = sorted({r["occurrence_month"] for r in rows})
    matrix = {}
    settled_matrix = {}
    for r in rows:
        matrix.setdefault(r["city_company"], {})[r["occurrence_month"]] = round(r["amount"], 2)
    for r in settle_rows:
        settled = r["settled_count"] == r["total_count"] and r["total_count"] > 0
        settled_matrix.setdefault(r["city_company"], {})[r["occurrence_month"]] = settled
    return ok({"cities": cities, "months": months, "matrix": matrix, "settled_matrix": settled_matrix})


@app.route("/api/detail")
def api_detail():
    city = request.args.get("city", "全部")
    month = request.args.get("month", "")

    where = ["attribute_16 = ?"]
    params = [FILTER_ATTRIBUTE_16]
    if month:
        where.append("occurrence_month = ?")
        params.append(month)
    if city and city != "全部":
        where.append("city_company = ?")
        params.append(city)
    where_sql = " AND ".join(where)

    conn = get_conn()
    try:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM customer_billing WHERE {where_sql}", params).fetchone()["c"]
        rows = conn.execute(
            f"SELECT {','.join(DETAIL_COLUMNS)} FROM customer_billing WHERE {where_sql} "
            f"ORDER BY occurrence_month DESC, city_company ASC",
            params
        ).fetchall()
    finally:
        conn.close()

    data = [dict(r) for r in rows]
    return ok({
        "total": total,
        "rows": data,
        "columns": DETAIL_COLUMNS,
        "columns_cn": DETAIL_COLUMNS_CN,
    })


@app.route("/api/cities")
def api_cities():
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT DISTINCT city_company FROM customer_billing
            WHERE attribute_16 = ? ORDER BY city_company ASC
        """, (FILTER_ATTRIBUTE_16,)).fetchall()
    finally:
        conn.close()
    return ok([r["city_company"] for r in rows])


@app.route("/api/months")
def api_months():
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT DISTINCT occurrence_month FROM customer_billing
            WHERE attribute_16 = ? ORDER BY occurrence_month ASC
        """, (FILTER_ATTRIBUTE_16,)).fetchall()
    finally:
        conn.close()
    return ok([r["occurrence_month"] for r in rows])


@app.route("/api/settle", methods=["POST"])
def api_settle():
    data = request.get_json() or {}
    ids = data.get("ids", [])
    is_settled = data.get("is_settled", 1)
    if not ids:
        return fail("请选择要销账的记录")

    conn = get_conn()
    try:
        placeholders = ",".join("?" * len(ids))
        conn.execute(
            f"UPDATE customer_billing SET is_settled = ? WHERE id IN ({placeholders})",
            [is_settled] + ids
        )
        conn.commit()
        return ok({"updated": conn.total_changes})
    except Exception as e:
        return fail(f"更新失败: {e}")
    finally:
        conn.close()


# ---------- 错误处理 ----------
@app.errorhandler(413)
def _too_large(e):
    return fail("上传文件过大（上限200MB）", 413)


@app.errorhandler(500)
def _server_error(e):
    return fail(f"服务器错误: {e}", 500)


if __name__ == "__main__":
    init_db()
    print("启动: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
