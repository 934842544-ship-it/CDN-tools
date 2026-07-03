// 详情页逻辑：月份 + 市公司筛选 + 自动保存销账状态
const monthPicker = document.getElementById("monthPicker");
const citySelect = document.getElementById("citySelect");
const queryBtn = document.getElementById("queryBtn");
const detailTable = document.getElementById("detailTable");
const pager = document.getElementById("pager");

let currentRows = [];

function fmtMoney(v) {
    if (v == null || isNaN(v)) return "";
    return Number(v).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function loadCities() {
    const resp = await fetch("/api/cities");
    const json = await resp.json();
    if (json.code !== 0) return;
    json.data.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c;
        opt.textContent = c;
        citySelect.appendChild(opt);
    });
}

async function loadMonths() {
    const resp = await fetch("/api/months");
    const json = await resp.json();
    if (json.code !== 0) return;
    return json.data;
}

function setCity(val) {
    for (const opt of citySelect.options) {
        if (opt.value === val) { opt.selected = true; return; }
    }
    if (val !== "全部") {
        const opt = document.createElement("option");
        opt.value = val; opt.textContent = val;
        citySelect.appendChild(opt);
        opt.selected = true;
    }
}

function setAllChecked(checked) {
    const checkboxes = detailTable.querySelectorAll("tbody input[type='checkbox']");
    checkboxes.forEach(cb => { cb.checked = checked; });
    updateHeaderCheckbox();
}

function updateHeaderCheckbox() {
    const checkboxes = detailTable.querySelectorAll("tbody input[type='checkbox']");
    const checked = Array.from(checkboxes).filter(cb => cb.checked);
    const headerCb = document.getElementById("headerSelectAll");
    if (headerCb) {
        headerCb.checked = checkboxes.length > 0 && checked.length === checkboxes.length;
    }
}

async function autoSaveSettle(id, isSettled) {
    await fetch("/api/settle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: [id], is_settled: isSettled ? 1 : 0 })
    });
}

async function autoSaveAllSettle() {
    const checkboxes = detailTable.querySelectorAll("tbody input[type='checkbox']");
    const settledIds = [];
    const unsettledIds = [];
    checkboxes.forEach(cb => {
        const id = parseInt(cb.dataset.id);
        if (cb.checked) settledIds.push(id);
        else unsettledIds.push(id);
    });
    if (settledIds.length > 0) {
        await fetch("/api/settle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ids: settledIds, is_settled: 1 })
        });
    }
    if (unsettledIds.length > 0) {
        await fetch("/api/settle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ids: unsettledIds, is_settled: 0 })
        });
    }
}

async function loadDetail() {
    const city = citySelect.value || "全部";
    const month = monthPicker.value || "";
    const url = `/api/detail?city=${encodeURIComponent(city)}&month=${encodeURIComponent(month)}`;
    const resp = await fetch(url);
    const json = await resp.json();
    if (json.code !== 0) {
        detailTable.innerHTML = `<tr><td class="empty">${json.msg}</td></tr>`;
        pager.innerHTML = "";
        return;
    }
    const { rows, columns, columns_cn, total } = json.data;
    currentRows = rows;
    if (!rows.length) {
        detailTable.innerHTML = `<tr><td class="empty">暂无数据</td></tr>`;
        pager.innerHTML = "";
        return;
    }

    let thead = "<thead><tr>";
    columns.forEach(c => {
        if (c === "id") return;
        if (c === "is_settled") {
            thead += `<th>${columns_cn[c] || c}<br><input type="checkbox" id="headerSelectAll" style="margin-top:4px;"></th>`;
        } else {
            thead += `<th>${columns_cn[c] || c}</th>`;
        }
    });
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    rows.forEach(r => {
        tbody += "<tr>";
        columns.forEach(c => {
            if (c === "id") return;
            let v = r[c];
            if (c === "billing_amount" || c === "usage_volume") {
                v = fmtMoney(v);
            } else if (c === "is_settled") {
                v = `<input type="checkbox" data-id="${r.id}" ${v ? "checked" : ""}>`;
            }
            tbody += `<td>${v == null || v === "" ? "" : v}</td>`;
        });
        tbody += "</tr>";
    });
    tbody += "</tbody>";
    detailTable.innerHTML = thead + tbody;

    const headerCb = document.getElementById("headerSelectAll");
    if (headerCb) {
        headerCb.addEventListener("change", async () => {
            setAllChecked(headerCb.checked);
            await autoSaveAllSettle();
        });
    }
    detailTable.querySelectorAll("tbody input[type='checkbox']").forEach(cb => {
        cb.addEventListener("change", async (e) => {
            const id = parseInt(e.target.dataset.id);
            await autoSaveSettle(id, e.target.checked);
            updateHeaderCheckbox();
        });
    });
    updateHeaderCheckbox();

    pager.innerHTML = `<span class="tip">共 ${total} 条记录</span>`;
}

queryBtn.addEventListener("click", () => loadDetail());

(async function init() {
    await loadCities();
    const months = await loadMonths();
    const initMonth = window.INIT_PARAMS.month || (months.length ? months[months.length - 1] : "");
    monthPicker.value = initMonth;
    setCity(window.INIT_PARAMS.city);
    loadDetail();
})();