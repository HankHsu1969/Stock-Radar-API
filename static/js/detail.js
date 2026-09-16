/* /stock/<code> 獨立頁面 — 渲染邏輯共用 detail-view.js */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var view = StockDetail(document.getElementById("detailRoot"), { layout: "page" });
    view.load(document.body.dataset.code);
    window.addEventListener("resize", view.resize);
  });
})();
