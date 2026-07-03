// 汇总页逻辑：表格 + ECharts + 上传弹窗
const chart = echarts.init(document.getElementById("chart"));
const summaryTable = document.getElementById("summaryTable");
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileList = document.getElementById("fileList");
const submitUpload = document.getElementById("submitUpload");
const progressBox = document.getElementById("progressBox");
const resultBox = document.getElementById("resultBox");
const modalBody = document.querySelector("#uploadModal .modal-body");
const modalFooter = document.querySelector("#uploadModal .modal-footer");

let selectedFiles = [];
let summaryData = null;

function fmtMoney(v) {
    if (v == null || isNaN(v)) return "0.00";
    return Number(v).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function renderFileList() {
    fileList.innerHTML = "";
    selectedFiles.forEach((f, idx) => {
        const item = document.createElement("div");
        item.className = "file-item";
        item.innerHTML = `<span>${idx + 1}. ${f.name}</span><span>${(f.size/1024).toFixed(1)} KB</span>`;
        fileList.appendChild(item);
    });
    submitUpload.disabled = selectedFiles.length === 0;
}

dropZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => {
    selectedFiles = Array.from(e.target.files);
    renderFileList();
});
dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    selectedFiles = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith(".xlsx"));
    renderFileList();
});

submitUpload.addEventListener("click", async () => {
    if (selectedFiles.length === 0) return;
    modalBody.style.display = "none";
    modalFooter.style.display = "none";
    progressBox.style.display = "flex";
    resultBox.style.display = "none";

    const fd = new FormData();
    selectedFiles.forEach(f => fd.append("files", f));

    try {
        const resp = await fetch("/upload", { method: "POST", body: fd });
        const data = await resp.json();
        progressBox.style.display = "none";
        resultBox.style.display = "block";
        if (data.code === 0) {
            const d = data.data;
            const monthsStr = d.months && d.months.length ? d.months.join("、") : "无";
            const errStr = d.errors && d.errors.length
                ? `<div style="color:#dc2626;margin-top:8px;">失败文件:<br>${d.errors.map(e => `· ${e}`).join("<br>")}</div>`
                : "";
            resultBox.innerHTML = `
                <h4>上传成功</h4>
                <p>插入数据：<strong>${d.inserted}</strong> 行</p>
                <p>覆盖月份：${monthsStr}</p>
                ${errStr}
                <div style="margin-top:16px;">
                    <button class="btn" onclick="window.uploadSuccess()">确定</button>
                </div>
            `;
        } else {
            resultBox.innerHTML = `
                <h4 style="color:#dc2626;">上传失败</h4>
                <p>${data.msg}</p>
                <div style="margin-top:16px;">
                    <button class="btn" onclick="window.location.reload()">重试</button>
                </div>
            `;
        }
    } catch (err) {
        progressBox.style.display = "none";
        resultBox.style.display = "block";
        resultBox.innerHTML = `
            <h4 style="color:#dc2626;">请求失败</h4>
            <p>${err.message}</p>
            <div style="margin-top:16px;">
                <button class="btn" onclick="window.location.reload()">重试</button>
            </div>
        `;
    }
});

async function loadSummary() {
    const resp = await fetch("/api/summary");
    const json = await resp.json();
    if (json.code !== 0) {
        summaryTable.innerHTML = `<tr><td class="empty">${json.msg}</td></tr>`;
        chart.clear();
        return;
    }
    summaryData = json.data;
    const { cities, months, matrix } = summaryData;
    if (!cities.length || !months.length) {
        summaryTable.innerHTML = `<tr><td class="empty">暂无数据，请点击右上角"上传数据"</td></tr>`;
        chart.clear();
        return;
    }

    renderTable();
    renderChart();
}

function renderTable() {
    const { cities, months, matrix, settled_matrix } = summaryData;
    let thead = "<thead><tr><th>发生月份 \\ 市公司</th>" +
        cities.map(c => `<th>${c}</th>`).join("") +
        "<th>合计</th></tr></thead>";
    let tbody = "<tbody>";
    months.forEach(month => {
        let rowTotal = 0;
        let tds = cities.map(city => {
            const v = (matrix[city] && matrix[city][month]) || 0;
            rowTotal += v;
            const settled = (settled_matrix[city] && settled_matrix[city][month]) || false;
            const bgClass = settled ? " settled" : "";
            return `<td class="clickable${bgClass}" data-city="${city}" data-month="${month}">${fmtMoney(v)}</td>`;
        }).join("");
        tbody += `<tr><td>${month}</td>${tds}<td>${fmtMoney(rowTotal)}</td></tr>`;
    });
    let cityTotals = cities.map(city => {
        let t = 0;
        months.forEach(m => { t += (matrix[city] && matrix[city][m]) || 0; });
        return t;
    });
    let grandTotal = cityTotals.reduce((a, b) => a + b, 0);
    tbody += `<tr><td>合计</td>${cityTotals.map(t => `<td>${fmtMoney(t)}</td>`).join("")}<td>${fmtMoney(grandTotal)}</td></tr>`;
    tbody += "</tbody>";
    summaryTable.innerHTML = thead + tbody;

    summaryTable.querySelectorAll("td.clickable").forEach(td => {
        td.addEventListener("click", () => {
            const c = td.dataset.city;
            const m = td.dataset.month;
            window.location.href = `/detail?city=${encodeURIComponent(c)}&month=${encodeURIComponent(m)}`;
        });
    });
}

function renderChart() {
    const { cities, months, matrix } = summaryData;
    // 计算每个市公司的全年累计金额
    const cityTotals = cities.map(city => {
        let total = 0;
        months.forEach(m => { total += (matrix[city] && matrix[city][m]) || 0; });
        return total;
    });

    const series = [{
        name: "全年累计",
        type: "bar",
        data: cityTotals,
        itemStyle: { color: "#1890ff" },
        label: {
            show: true,
            position: "top",
            formatter: params => fmtMoney(params.value)
        }
    }];

    chart.setOption({
        tooltip: {
            trigger: "axis",
            axisPointer: { type: "shadow" },
            formatter: params => {
                const p = params[0];
                return `${p.name}<br>全年累计: ${fmtMoney(p.value)}`;
            }
        },
        grid: { left: 60, right: 30, top: 50, bottom: 60 },
        xAxis: { 
            type: "category", 
            data: cities, 
            axisLabel: { interval: 0, rotate: cities.length > 8 ? 30 : 0 }
        },
        yAxis: { type: "value", name: "金额" },
        series: series,
    }, true);
}

window.addEventListener("resize", () => chart.resize());
loadSummary();
