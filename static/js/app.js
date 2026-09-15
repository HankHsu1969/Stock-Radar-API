/* 台股智慧篩選雷達 — 觀察清單首頁 */
(function () {
  "use strict";

  var stocks = [];
  var sortKey = "score";

  var $ = function (id) { return document.getElementById(id); };

  // ---------------------------------------------------------- 工具
  function fmt(n, d) {
    if (n === null || n === undefined || isNaN(n)) return "—";
    return Number(n).toLocaleString("zh-TW", {
      minimumFractionDigits: d === undefined ? 2 : d,
      maximumFractionDigits: d === undefined ? 2 : d
    });
  }
  function signCls(v) { return v > 0 ? "up" : (v < 0 ? "down" : "flat"); }
  function signTxt(v, d) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return (v > 0 ? "+" : "") + fmt(v, d === undefined ? 2 : d);
  }
  function gradeCls(g) {
    return "g-" + g.replace("+", "p");
  }
  function toast(msg, type) {
    var box = document.createElement("div");
    box.className = type || "";
    box.textContent = msg;
    $("toast").appendChild(box);
    setTimeout(function () { box.remove(); }, 3600);
  }

  // ---------------------------------------------------------- 載入與繪製
  function load(forceRefresh) {
    var btn = $("btnRefresh");
    btn.disabled = true;
    btn.textContent = "載入中…";
    $("tbody").innerHTML =
      '<tr><td colspan="15"><div class="loading"><div class="spin"></div>' +
      (forceRefresh ? "正在重新抓取最新行情…" : "正在向 Yahoo Finance 與證交所取得即時資料…") +
      "</div></td></tr>";

    fetch("/api/watchlist" + (forceRefresh ? "?refresh=1" : ""))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        stocks = data.stocks || [];
        render();
        $("updatedAt").textContent = new Date().toLocaleTimeString("zh-TW", { hour12: false });
        var first = stocks.find(function (s) { return s.ok; });
        $("dataDate").textContent = first ? first.quote.date : "—";
      })
      .catch(function (e) {
        $("tbody").innerHTML = '<tr><td colspan="15"><div class="empty">載入失敗：' + e + "</div></td></tr>";
      })
      .finally(function () {
        btn.disabled = false;
        btn.textContent = "↻ 重新整理";
      });
  }

  function sorted() {
    var ok = stocks.filter(function (s) { return s.ok; });
    var bad = stocks.filter(function (s) { return !s.ok; });
    var pick = function (s, key) {
      var b = s.rating.breakdown.find(function (x) { return x.key === key; });
      return b ? b.score / b.max : 0;
    };
    ok.sort(function (a, b) {
      switch (sortKey) {
        case "change": return b.quote.change_pct - a.quote.change_pct;
        case "trend": return pick(b, "trend") - pick(a, "trend");
        case "value": return pick(b, "value") - pick(a, "value");
        case "code": return a.code.localeCompare(b.code);
        default: return b.rating.total - a.rating.total;
      }
    });
    return ok.concat(bad);
  }

  function renderStats() {
    var ok = stocks.filter(function (s) { return s.ok; });
    if (!ok.length) { $("stats").innerHTML = ""; return; }
    var up = ok.filter(function (s) { return s.quote.change_pct > 0; }).length;
    var down = ok.filter(function (s) { return s.quote.change_pct < 0; }).length;
    var avg = ok.reduce(function (a, s) { return a + s.rating.total; }, 0) / ok.length;
    var strong = ok.filter(function (s) { return s.rating.total >= 66; }).length;
    var best = ok.reduce(function (a, s) { return s.rating.total > a.rating.total ? s : a; }, ok[0]);

    var cells = [
      ["觀察檔數", ok.length + (stocks.length > ok.length ? " / " + stocks.length : ""), ""],
      ["上漲 / 下跌", up + " / " + down, up >= down ? "up" : "down"],
      ["平均評分", fmt(avg, 1), ""],
      ["偏多以上(B+)", strong + " 檔", "up"],
      ["評分之最", best.code + " " + best.name, ""]
    ];
    $("stats").innerHTML = cells.map(function (c) {
      return '<div class="stat"><div class="k">' + c[0] + '</div><div class="v ' + c[2] + '">' + c[1] + "</div></div>";
    }).join("");
  }

  function barsHTML(rt) {
    return '<div class="bars">' + rt.breakdown.map(function (b) {
      var pct = Math.max(4, Math.round(b.score / b.max * 100));
      return '<span class="bar b-' + b.key + '" title="' + b.name + " " + b.score + "/" + b.max +
        '"><i style="height:' + pct + '%"></i></span>';
    }).join("") + "</div>";
  }

  function render() {
    renderStats();
    var list = sorted();
    if (!list.length) {
      $("tbody").innerHTML = '<tr><td colspan="15"><div class="empty">觀察清單是空的，請於上方輸入代碼新增。</div></td></tr>';
      return;
    }

    $("tbody").innerHTML = list.map(function (s, i) {
      if (!s.ok) {
        return '<tr class="bad" data-code="' + s.code + '"><td class="rank">–</td>' +
          '<td class="code">' + s.code + '</td><td class="nm">' + s.name + "</td>" +
          '<td colspan="11" style="text-align:left;color:var(--muted)">' + (s.error || "無資料") + "</td>" +
          '<td><div class="act"><button class="iconbtn del" data-del="' + s.code + '" title="移除">✕</button></div></td></tr>';
      }
      var q = s.quote, rt = s.rating;
      var bias = q.ma20 ? (q.close / q.ma20 - 1) * 100 : null;
      var rank = i + 1;
      return '<tr data-code="' + s.code + '">' +
        '<td class="rank' + (rank <= 3 ? " top" : "") + '">' + rank + "</td>" +
        '<td class="code">' + s.code + "</td>" +
        '<td class="nm">' + s.name + '<span class="mk">' + (s.market === "TPEX" ? "上櫃" : "上市") + "</span></td>" +
        '<td class="' + signCls(q.change) + '"><b>' + fmt(q.close) + "</b></td>" +
        '<td class="' + signCls(q.change) + '">' + signTxt(q.change) + "</td>" +
        '<td class="' + signCls(q.change) + '">' + signTxt(q.change_pct) + "%</td>" +
        "<td>" + fmt(q.volume_lots, 0) + "</td>" +
        '<td class="' + signCls(q.ret_5d) + '">' + signTxt(q.ret_5d, 1) + "%</td>" +
        '<td class="' + signCls(q.ret_20d) + '">' + signTxt(q.ret_20d, 1) + "%</td>" +
        "<td>" + fmt(q.rsi14, 0) + "</td>" +
        '<td class="' + signCls(bias) + '">' + signTxt(bias, 1) + "%</td>" +
        "<td>" + barsHTML(rt) + "</td>" +
        '<td class="score">' + fmt(rt.total, 1) + "</td>" +
        '<td><span class="grade ' + gradeCls(rt.grade) + '">' + rt.grade + "</span> " +
        '<span style="color:var(--muted);font-size:11.5px">' + rt.label + "</span></td>" +
        '<td><div class="act">' +
        '<button class="iconbtn" data-open="' + s.code + '" title="開新視窗看詳細資料">⤢</button>' +
        '<button class="iconbtn del" data-del="' + s.code + '" title="從清單移除">✕</button>' +
        "</div></td></tr>";
    }).join("");
  }

  function openDetail(code) {
    window.open("/stock/" + code, "stock_" + code,
      "width=1380,height=940,menubar=no,toolbar=no,location=no,resizable=yes,scrollbars=yes");
  }

  // ---------------------------------------------------------- 新增 / 刪除
  function addStock(code) {
    code = (code || $("addInput").value).trim();
    if (!code) { toast("請先輸入股票代碼", "err"); return; }
    $("btnAdd").disabled = true;
    fetch("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code })
    })
      .then(function (r) { return r.json().then(function (d) { return { st: r.ok, d: d }; }); })
      .then(function (res) {
        if (!res.st) { toast(res.d.error || "新增失敗", "err"); return; }
        toast("已加入 " + res.d.added.code + " " + res.d.added.name, "ok");
        $("addInput").value = "";
        hideSuggest();
        load(false);
      })
      .catch(function (e) { toast("新增失敗：" + e, "err"); })
      .finally(function () { $("btnAdd").disabled = false; });
  }

  function delStock(code) {
    var s = stocks.find(function (x) { return x.code === code; });
    if (!confirm("確定要從觀察清單移除 " + code + " " + (s ? s.name : "") + " 嗎？")) return;
    fetch("/api/watchlist/" + code, { method: "DELETE" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) { toast(d.error || "移除失敗", "err"); return; }
        toast("已移除 " + code, "ok");
        stocks = stocks.filter(function (x) { return x.code !== code; });
        render();
      });
  }

  // ---------------------------------------------------------- 搜尋建議
  var sugTimer = null, sugItems = [], sugIdx = -1;

  function hideSuggest() {
    $("suggest").hidden = true;
    sugItems = []; sugIdx = -1;
  }

  function showSuggest(items) {
    sugItems = items; sugIdx = -1;
    if (!items.length) { hideSuggest(); return; }
    $("suggest").innerHTML = items.map(function (it, i) {
      return '<div data-i="' + i + '"><span class="c">' + it.code + "</span><span>" + it.name +
        '</span><span class="m">' + (it.market === "TPEX" ? "上櫃" : "上市") + "</span></div>";
    }).join("");
    $("suggest").hidden = false;
  }

  function querySuggest() {
    var q = $("addInput").value.trim();
    clearTimeout(sugTimer);
    if (q.length < 1) { hideSuggest(); return; }
    sugTimer = setTimeout(function () {
      fetch("/api/search?q=" + encodeURIComponent(q))
        .then(function (r) { return r.json(); })
        .then(function (d) { showSuggest(d.results || []); })
        .catch(hideSuggest);
    }, 220);
  }

  // ---------------------------------------------------------- 事件綁定
  document.addEventListener("DOMContentLoaded", function () {
    load(false);

    $("btnRefresh").onclick = function () { load(true); };
    $("btnAdd").onclick = function () { addStock(); };
    $("btnReset").onclick = function () {
      if (!confirm("將觀察清單回復為預設的 20 支熱門股票？目前自訂的內容會被覆蓋。")) return;
      fetch("/api/watchlist/reset", { method: "POST" })
        .then(function (r) { return r.json(); })
        .then(function () { toast("已回復預設清單", "ok"); load(false); });
    };

    $("addInput").addEventListener("input", querySuggest);
    $("addInput").addEventListener("keydown", function (e) {
      if (!$("suggest").hidden && sugItems.length) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
          e.preventDefault();
          sugIdx += e.key === "ArrowDown" ? 1 : -1;
          if (sugIdx < 0) sugIdx = sugItems.length - 1;
          if (sugIdx >= sugItems.length) sugIdx = 0;
          Array.prototype.forEach.call($("suggest").children, function (el, i) {
            el.classList.toggle("active", i === sugIdx);
          });
          return;
        }
        if (e.key === "Enter" && sugIdx >= 0) {
          e.preventDefault();
          addStock(sugItems[sugIdx].code);
          return;
        }
        if (e.key === "Escape") { hideSuggest(); return; }
      }
      if (e.key === "Enter") addStock();
    });

    $("suggest").addEventListener("click", function (e) {
      var row = e.target.closest("div[data-i]");
      if (row) addStock(sugItems[+row.dataset.i].code);
    });

    document.addEventListener("click", function (e) {
      if (!e.target.closest(".searchbox")) hideSuggest();
    });

    $("sortGroup").addEventListener("click", function (e) {
      var b = e.target.closest("button[data-sort]");
      if (!b) return;
      sortKey = b.dataset.sort;
      Array.prototype.forEach.call($("sortGroup").children, function (el) {
        el.classList.toggle("on", el === b);
      });
      render();
    });

    $("tbody").addEventListener("click", function (e) {
      var del = e.target.closest("button[data-del]");
      if (del) { e.stopPropagation(); delStock(del.dataset.del); return; }
      var op = e.target.closest("button[data-open]");
      if (op) { e.stopPropagation(); openDetail(op.dataset.open); return; }
      var tr = e.target.closest("tr[data-code]");
      if (tr) openDetail(tr.dataset.code);
    });
  });
})();
