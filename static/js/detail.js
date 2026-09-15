/* 個股詳細資料 + K 線圖（ECharts） */
(function () {
  "use strict";

  var UP = "#ff4d4f", DOWN = "#00c48c";      // 台股慣例：紅漲綠跌
  var CODE = document.body.dataset.code;
  var chart = null, period = "1y", payload = null;

  var $ = function (id) { return document.getElementById(id); };

  function fmt(n, d) {
    if (n === null || n === undefined || isNaN(n)) return "—";
    return Number(n).toLocaleString("zh-TW", {
      minimumFractionDigits: d === undefined ? 2 : d,
      maximumFractionDigits: d === undefined ? 2 : d
    });
  }
  function sign(v, d, suffix) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return (v > 0 ? "+" : "") + fmt(v, d === undefined ? 2 : d) + (suffix || "");
  }
  function cls(v) { return v > 0 ? "up" : (v < 0 ? "down" : "flat"); }
  function bigNum(v) {
    if (!v) return "—";
    if (v >= 1e12) return fmt(v / 1e12, 2) + " 兆";
    if (v >= 1e8) return fmt(v / 1e8, 1) + " 億";
    return fmt(v, 0);
  }
  function pctOf(v) {
    return (v === null || v === undefined || isNaN(v)) ? "—" : fmt(v * 100, 2) + "%";
  }

  // ------------------------------------------------------------- 載入
  function load() {
    fetch("/api/stock/" + CODE + "?period=" + period)
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (!res.ok) {
          $("subInfo").textContent = res.d.error || "載入失敗";
          document.getElementById("kchart").innerHTML =
            '<div class="chartfail">' + (res.d.error || "無法取得行情資料") + "</div>";
          return;
        }
        payload = res.d;
        renderHead();
        renderBreakdown();
        renderTech();
        renderFund();
        renderRecent();
        renderChart();
      })
      .catch(function (e) { $("subInfo").textContent = "載入失敗：" + e; });
  }

  // ------------------------------------------------------------- 區塊繪製
  function renderHead() {
    var q = payload.quote, rt = payload.rating, f = payload.fundamentals || {};
    $("px").textContent = fmt(q.close);
    $("px").className = "px " + cls(q.change);
    $("chg").textContent = sign(q.change) + "  (" + sign(q.change_pct, 2, "%") + ")";
    $("chg").className = "chg " + cls(q.change);
    $("subInfo").innerHTML =
      (payload.stock.market === "TPEX" ? "上櫃" : "上市") +
      " · 資料日 " + q.date +
      (f.sector ? " · " + f.sector : "") +
      " · 開 " + fmt(q.open) + " 高 " + fmt(q.high) + " 低 " + fmt(q.low) +
      " · 量 " + fmt(q.volume_lots, 0) + " 張";
    $("grade").textContent = rt.grade;
    $("grade").className = "g " + cls(rt.total - 58);
    $("gradeTxt").textContent = rt.label + " · " + fmt(rt.total, 1) + " 分";
    document.title = payload.stock.code + " " + payload.stock.name + " " + fmt(q.close) +
      " (" + sign(q.change_pct, 2, "%") + ")";
  }

  var COLORS = { trend: "#4c9aff", momentum: "#7b61ff", volume: "#ffb020", risk: "#00c48c", value: "#ff7875" };

  function renderBreakdown() {
    var rt = payload.rating;
    $("totalTag").textContent = "總分 " + fmt(rt.total, 1) + " / 100";
    $("breakdown").innerHTML = rt.breakdown.map(function (b) {
      var pct = Math.round(b.score / b.max * 100);
      return '<div class="row">' +
        '<div class="lbl"><span>' + b.name + '</span><b>' + fmt(b.score, 1) + " / " + b.max + "</b></div>" +
        '<div class="track"><i style="width:' + pct + "%;background:" + COLORS[b.key] + '"></i></div>' +
        '<div class="why">' + b.reasons.map(function (r) { return "<span>" + r + "</span>"; }).join("") + "</div>" +
        "</div>";
    }).join("");
  }

  function kvHTML(rows) {
    return rows.map(function (r) {
      return '<div class="k">' + r[0] + '</div><div class="v ' + (r[2] || "") + '">' + r[1] + "</div>";
    }).join("");
  }

  function renderTech() {
    var q = payload.quote;
    var bias20 = q.ma20 ? (q.close / q.ma20 - 1) * 100 : null;
    var bias60 = q.ma60 ? (q.close / q.ma60 - 1) * 100 : null;
    $("tech").innerHTML = kvHTML([
      ["5 日均線 MA5", fmt(q.ma5), q.close >= q.ma5 ? "up" : "down"],
      ["20 日均線 MA20", fmt(q.ma20), q.close >= q.ma20 ? "up" : "down"],
      ["60 日均線 MA60", fmt(q.ma60), q.close >= q.ma60 ? "up" : "down"],
      ["月線乖離率", sign(bias20, 2, "%"), cls(bias20)],
      ["季線乖離率", sign(bias60, 2, "%"), cls(bias60)],
      ["RSI (14)", fmt(q.rsi14, 1), q.rsi14 >= 70 ? "up" : (q.rsi14 <= 30 ? "down" : "")],
      ["KD 值", fmt(q.k, 1) + " / " + fmt(q.d, 1), q.k >= q.d ? "up" : "down"],
      ["MACD 柱狀", fmt(q.macd_hist, 3), cls(q.macd_hist)],
      ["布林上 / 下軌", fmt(q.bb_up) + " / " + fmt(q.bb_low), ""],
      ["日均波幅 ATR%", q.atr14 ? fmt(q.atr14 / q.close * 100, 2) + "%" : "—", ""],
      ["近 5 / 20 日報酬", sign(q.ret_5d, 1, "%") + " / " + sign(q.ret_20d, 1, "%"), cls(q.ret_20d)],
      ["近 60 日最大回撤", "-" + fmt(q.mdd_60d, 1) + "%", "down"],
      ["近一年高 / 低", fmt(q.high_252d) + " / " + fmt(q.low_252d), ""],
      ["5 / 20 日均量(張)", fmt(Math.floor(q.vol_ma5 / 1000), 0) + " / " + fmt(Math.floor(q.vol_ma20 / 1000), 0), ""]
    ]);
  }

  function renderFund() {
    var f = payload.fundamentals || {};
    $("fund").innerHTML = kvHTML([
      ["公司全名", f.long_name || "—", ""],
      ["產業別", (f.sector || "—") + (f.industry ? " / " + f.industry : ""), ""],
      ["市值", bigNum(f.market_cap), ""],
      ["本益比 PE", f.pe ? fmt(f.pe, 2) + " 倍" : "—", ""],
      ["預估本益比", f.forward_pe ? fmt(f.forward_pe, 2) + " 倍" : "—", ""],
      ["股價淨值比 PB", f.pb ? fmt(f.pb, 2) : "—", ""],
      ["現金殖利率", f.dividend_yield ? fmt(f.dividend_yield, 2) + "%" : "—", "up"],
      ["股東權益報酬率 ROE", pctOf(f.roe), ""],
      ["淨利率", pctOf(f.profit_margin), ""],
      ["營收年增率", pctOf(f.revenue_growth), cls(f.revenue_growth)],
      ["盈餘年增率", pctOf(f.earnings_growth), cls(f.earnings_growth)],
      ["Beta 係數", f.beta ? fmt(f.beta, 2) : "—", ""],
      ["52 週高 / 低", f.week52_high ? fmt(f.week52_high) + " / " + fmt(f.week52_low) : "—", ""]
    ]);
  }

  function renderRecent() {
    var c = payload.chart;
    var n = c.dates.length;
    var rows = [];
    for (var i = n - 1; i >= Math.max(0, n - 10); i--) {
      var o = c.candles[i][0], close = c.candles[i][1], lo = c.candles[i][2], hi = c.candles[i][3];
      var prev = i > 0 ? c.candles[i - 1][1] : close;
      var pct = prev ? (close / prev - 1) * 100 : 0;
      rows.push('<tr><td style="text-align:left">' + c.dates[i] + "</td><td>" + fmt(o) +
        "</td><td>" + fmt(hi) + "</td><td>" + fmt(lo) +
        '</td><td class="' + cls(pct) + '"><b>' + fmt(close) + "</b></td>" +
        '<td class="' + cls(pct) + '">' + sign(pct, 2, "%") + "</td>" +
        "<td>" + fmt(Math.floor(c.volume[i] / 1000), 0) + "</td></tr>");
    }
    $("recent").innerHTML = rows.join("");
  }

  // ------------------------------------------------------------- K 線圖
  function renderChart() {
    var c = payload.chart;
    if (typeof echarts === "undefined") {
      $("kchart").innerHTML = '<div class="chartfail">圖表函式庫載入失敗</div>';
      return;
    }
    if (!chart) chart = echarts.init($("kchart"), null, { renderer: "canvas" });

    var volColors = c.candles.map(function (k) { return k[1] >= k[0] ? UP : DOWN; });
    var startPct = Math.max(0, 100 - 12000 / Math.max(c.dates.length, 1));

    var axisBase = {
      type: "category", data: c.dates, boundaryGap: true,
      axisLine: { lineStyle: { color: "#2a3442" } },
      axisLabel: { color: "#8a97a8", fontSize: 11 },
      splitLine: { show: false }
    };
    var yBase = {
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: "#8a97a8", fontSize: 11 },
      splitLine: { lineStyle: { color: "#1d2531" } }
    };

    chart.setOption({
      backgroundColor: "transparent",
      animation: false,
      legend: {
        top: 6, left: 12, textStyle: { color: "#8a97a8", fontSize: 11 }, itemGap: 14,
        icon: "roundRect", itemWidth: 14, itemHeight: 3,
        data: ["K線", "MA5", "MA20", "MA60", "布林上軌", "布林下軌"]
      },
      tooltip: {
        trigger: "axis", axisPointer: { type: "cross", link: [{ xAxisIndex: "all" }] },
        backgroundColor: "rgba(20,26,35,.96)", borderColor: "#26303d",
        textStyle: { color: "#e6edf5", fontSize: 12 },
        formatter: function (ps) {
          var i = ps[0].dataIndex;
          var k = c.candles[i];
          var prev = i > 0 ? c.candles[i - 1][1] : k[1];
          var pct = prev ? (k[1] / prev - 1) * 100 : 0;
          var col = pct >= 0 ? UP : DOWN;
          var line = function (k2, v) { return '<div style="display:flex;gap:16px;justify-content:space-between"><span style="color:#8a97a8">' + k2 + '</span><span>' + v + "</span></div>"; };
          return "<b>" + c.dates[i] + "</b>" +
            line("開盤", fmt(k[0])) + line("最高", fmt(k[3])) + line("最低", fmt(k[2])) +
            line("收盤", '<b style="color:' + col + '">' + fmt(k[1]) + " (" + sign(pct, 2, "%") + ")</b>") +
            line("成交量", fmt(Math.floor(c.volume[i] / 1000), 0) + " 張") +
            line("MA5 / MA20 / MA60", fmt(c.ma5[i]) + " / " + fmt(c.ma20[i]) + " / " + fmt(c.ma60[i])) +
            line("MACD (DIF/DEA)", fmt(c.dif[i], 2) + " / " + fmt(c.dea[i], 2)) +
            line("KD", fmt(c.k[i], 1) + " / " + fmt(c.d[i], 1)) +
            line("RSI14", fmt(c.rsi[i], 1));
        }
      },
      axisPointer: { link: [{ xAxisIndex: "all" }], label: { backgroundColor: "#2a3442" } },
      grid: [
        { left: 62, right: 22, top: 34, height: "44%" },
        { left: 62, right: 22, top: "56%", height: "10%" },
        { left: 62, right: 22, top: "69%", height: "11%" },
        { left: 62, right: 22, top: "83%", height: "11%" }
      ],
      xAxis: [
        Object.assign({}, axisBase, { gridIndex: 0, axisLabel: { show: false } }),
        Object.assign({}, axisBase, { gridIndex: 1, axisLabel: { show: false } }),
        Object.assign({}, axisBase, { gridIndex: 2, axisLabel: { show: false } }),
        Object.assign({}, axisBase, { gridIndex: 3 })
      ],
      yAxis: [
        Object.assign({}, yBase, { gridIndex: 0, scale: true }),
        Object.assign({}, yBase, { gridIndex: 1, splitNumber: 2, axisLabel: { color: "#8a97a8", fontSize: 10, formatter: function (v) { return Math.round(v / 1000) + "張"; } } }),
        Object.assign({}, yBase, { gridIndex: 2, scale: true, splitNumber: 2 }),
        Object.assign({}, yBase, { gridIndex: 3, min: 0, max: 100, splitNumber: 2 })
      ],
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1, 2, 3], start: startPct, end: 100 },
        {
          type: "slider", xAxisIndex: [0, 1, 2, 3], start: startPct, end: 100,
          bottom: 4, height: 18, borderColor: "#26303d", fillerColor: "rgba(76,154,255,.12)",
          handleStyle: { color: "#4c9aff" }, textStyle: { color: "#5f6b7c", fontSize: 10 },
          dataBackground: { lineStyle: { color: "#2a3442" }, areaStyle: { color: "#1b2430" } }
        }
      ],
      series: [
        {
          name: "K線", type: "candlestick", data: c.candles,
          itemStyle: { color: UP, color0: DOWN, borderColor: UP, borderColor0: DOWN }
        },
        { name: "MA5", type: "line", data: c.ma5, smooth: true, showSymbol: false, itemStyle: { color: "#ffb020" }, lineStyle: { width: 1.2 } },
        { name: "MA20", type: "line", data: c.ma20, smooth: true, showSymbol: false, itemStyle: { color: "#4c9aff" }, lineStyle: { width: 1.2 } },
        { name: "MA60", type: "line", data: c.ma60, smooth: true, showSymbol: false, itemStyle: { color: "#7b61ff" }, lineStyle: { width: 1.2 } },
        { name: "布林上軌", type: "line", data: c.bb_up, showSymbol: false, itemStyle: { color: "#4a5768" }, lineStyle: { width: 1, type: "dashed" } },
        { name: "布林下軌", type: "line", data: c.bb_low, showSymbol: false, itemStyle: { color: "#4a5768" }, lineStyle: { width: 1, type: "dashed" } },
        {
          name: "成交量", type: "bar", xAxisIndex: 1, yAxisIndex: 1, data: c.volume,
          itemStyle: { color: function (p) { return volColors[p.dataIndex]; } }
        },
        {
          name: "MACD", type: "bar", xAxisIndex: 2, yAxisIndex: 2, data: c.macd_hist,
          itemStyle: { color: function (p) { return p.data >= 0 ? UP : DOWN; } }
        },
        { name: "DIF", type: "line", xAxisIndex: 2, yAxisIndex: 2, data: c.dif, showSymbol: false, itemStyle: { color: "#ffb020" }, lineStyle: { width: 1 } },
        { name: "DEA", type: "line", xAxisIndex: 2, yAxisIndex: 2, data: c.dea, showSymbol: false, itemStyle: { color: "#4c9aff" }, lineStyle: { width: 1 } },
        { name: "K", type: "line", xAxisIndex: 3, yAxisIndex: 3, data: c.k, showSymbol: false, itemStyle: { color: "#ffb020" }, lineStyle: { width: 1 } },
        { name: "D", type: "line", xAxisIndex: 3, yAxisIndex: 3, data: c.d, showSymbol: false, itemStyle: { color: "#4c9aff" }, lineStyle: { width: 1 } }
      ]
    }, true);
  }

  // ------------------------------------------------------------- 事件
  document.addEventListener("DOMContentLoaded", function () {
    load();
    $("periods").addEventListener("click", function (e) {
      var b = e.target.closest("button[data-p]");
      if (!b || b.classList.contains("on")) return;
      period = b.dataset.p;
      Array.prototype.forEach.call($("periods").children, function (el) {
        el.classList.toggle("on", el === b);
      });
      load();
    });
    window.addEventListener("resize", function () { if (chart) chart.resize(); });
  });
})();
