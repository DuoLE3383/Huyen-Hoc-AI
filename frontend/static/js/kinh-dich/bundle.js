(function () {
  'use strict';
  var SVG_NS = 'http://www.w3.org/2000/svg';

  // Safe localStorage (chống extension lỗi)
  function safeGetToken() {
    try {
      return localStorage.getItem("token");
    } catch (e) {
      return null;
    }
  }
  var LOADING = ["Đang kết nối cõi vô hình…", "Đang gieo 3 đồng xu 6 lần…", "Đang tra cứu 64 quẻ Kinh Dịch…", "Đang luận giải ý nghĩa…", "Sắp xong rồi, bạn kiên nhẫn nhé…"];
  var QUOTES = ["Thiên hành kiện, quân tử dĩ tự cường bất tức.", "Địa thế khôn, quân tử dĩ hậu đức tái vật.", "Cùng tắc biến, biến tắc thông, thông tắc cửu.", "Tri nhân giả trí, tự tri giả minh.", "Thượng thiện nhược thủy, thủy thiện lợi vạn vật nhi bất tranh.", "Đại đạo chí giản, đại trí nhược ngu."];
  var CHIPS = [
    { icon: "💕", label: "Tình duyên", text: "Tôi có nên tiến tới mối quan hệ này không?" },
    { icon: "💼", label: "Sự nghiệp", text: "Công việc sắp tới của tôi sẽ như thế nào?" },
    { icon: "🌿", label: "Sức khỏe", text: "Sức khỏe của tôi trong thời gian tới ra sao?" },
    { icon: "💰", label: "Tài vận", text: "Tài chính của tôi nên đầu tư hay tiết kiệm?" },
    { icon: "🎓", label: "Học hành", text: "Tôi có nên theo đuổi ngành học này không?" },
    { icon: "🏠", label: "Gia đình", text: "Mối quan hệ gia đình tôi cần lưu ý điều gì?" },
    { icon: "✈️", label: "Xuất hành", text: "Tôi có nên thực hiện chuyến đi này không?" },
    { icon: "🤝", label: "Bạn bè", text: "Tôi nên chọn ai làm cộng sự tin cậy?" }
  ];
  function parseSSE(raw) {
    var lines = raw.split("\n"), ev = "message", data = "";
    for (var i = 0; i < lines.length; i++) {
      var l = lines[i];
      if (l.indexOf("event:") === 0) ev = l.slice(6).trim();
      else if (l.indexOf("data:") === 0) data += l.slice(5).trim();
    }
    if (!data) return null;
    try { return { event: ev, data: JSON.parse(data) }; } catch (e) { return { event: ev, data: {} }; }
  }
  function stream(question, h) {
    h = h || {};
    var tok = safeGetToken();
    var headers = { "Content-Type": "application/json", "Accept": "text/event-stream" };
    if (tok) headers.Authorization = "Bearer " + tok;
    return fetch("/api/kinh-dich-stream", { method: "POST", headers: headers, body: JSON.stringify({ cau_hoi: question }) }).then(function (res) {
      if (res.status === 401 && tok) { localStorage.clear(); location.replace("/"); return; }
      if (!res.ok) return res.text().catch(function () { return ""; }).then(function (t) { throw new Error(t || "Lỗi " + res.status); });
      var reader = res.body.getReader(), dec = new TextDecoder("utf-8"), buf = "";
      function pump() {
        return reader.read().then(function (r) {
          if (r.done) return;
          buf += dec.decode(r.value, { stream: true });
          var idx;
          while ((idx = buf.indexOf("\n\n")) !== -1) {
            var raw = buf.slice(0, idx); buf = buf.slice(idx + 2);
            var e = parseSSE(raw); if (!e) continue;
            if (e.event === "cast" && h.onCast) h.onCast(e.data);
            else if (e.event === "core" && h.onCore) h.onCore(e.data);
            else if (e.event === "tam_hop" && h.onTamHop) h.onTamHop(e.data);
            else if (e.event === "action" && h.onAction) h.onAction(e.data);
            else if (e.event === "error" && h.onError) h.onError(e.data);
            else if (e.event === "done" && h.onDone) h.onDone();
          }
          return pump();
        });
      }
      return pump();
    });
  }
  function haoSVG(duong, lao) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 100 14"); svg.setAttribute("preserveAspectRatio", "none");
    svg.classList.add("kd-hao-svg");
    var cls = "bar" + (lao ? " lao" : "");
    if (duong) {
      var r = document.createElementNS(SVG_NS, "rect");
      r.setAttribute("x","0"); r.setAttribute("y","0"); r.setAttribute("width","100");
      r.setAttribute("height","14"); r.setAttribute("rx","2"); r.setAttribute("class", cls);
      svg.appendChild(r);
    } else {
      [0, 60].forEach(function (x) {
        var r = document.createElementNS(SVG_NS, "rect");
        r.setAttribute("x", String(x)); r.setAttribute("y","0"); r.setAttribute("width","40");
        r.setAttribute("height","14"); r.setAttribute("rx","2"); r.setAttribute("class", cls);
        svg.appendChild(r);
      });
    }
    return svg;
  }
  function hexagram(container, hex, title) {
    container.innerHTML = ""; if (!hex) return;
    var block = document.createElement("div"); block.className = "kd-hex-block";
    var h = document.createElement("h3"); h.className = "kd-hex-title"; h.textContent = title; block.appendChild(h);
    var sub = document.createElement("div"); sub.className = "kd-hex-sub"; sub.textContent = "Quẻ " + hex.so + " · " + hex.ten; block.appendChild(sub);
    var box = document.createElement("div"); box.className = "kd-hexagram";
    var haos = document.createElement("div"); haos.className = "kd-haos";
    (hex.hao || []).forEach(function (hao) {
      var row = document.createElement("div"); row.className = "kd-hao";
      var n = document.createElement("div"); n.className = "kd-hao-num"; n.textContent = String(hao.vi_tri); row.appendChild(n);
      row.appendChild(haoSVG(hao.duong, hao.dong));
      var lbl = document.createElement("div");
      lbl.className = "kd-hao-label" + (hao.dong ? " dong" : "");
      lbl.textContent = hao.dong ? "động" : (hao.duong ? "dương" : "âm");
      row.appendChild(lbl); haos.appendChild(row);
    });
    box.appendChild(haos); block.appendChild(box);
    if (hex.thuong_quai && hex.ha_quai) {
      var info = document.createElement("div"); info.className = "kd-quai-info";
      info.innerHTML = "<span>Thượng: <b>" + hex.thuong_quai.ten + " " + hex.thuong_quai.tuong + "</b></span><span>Hạ: <b>" + hex.ha_quai.ten + " " + hex.ha_quai.tuong + "</b></span>";
      block.appendChild(info);
    }
    container.appendChild(block);
  }
  function bagua() {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 200 200"); svg.classList.add("kd-bagua");
    var c = document.createElementNS(SVG_NS, "circle");
    c.setAttribute("cx","100"); c.setAttribute("cy","100"); c.setAttribute("r","92");
    c.setAttribute("fill","none"); c.setAttribute("stroke","#C9A22755"); c.setAttribute("stroke-width","1");
    svg.appendChild(c);
    var tj = document.createElementNS(SVG_NS, "g"); tj.setAttribute("transform","translate(100,100)");
    var w = document.createElementNS(SVG_NS, "path");
    w.setAttribute("d","M 0 -30 A 30 30 0 0 1 0 30 A 15 15 0 0 1 0 0 A 15 15 0 0 0 0 -30 Z");
    w.setAttribute("fill","#E8C766"); tj.appendChild(w);
    var b = document.createElementNS(SVG_NS, "path");
    b.setAttribute("d","M 0 -30 A 30 30 0 0 0 0 30 A 15 15 0 0 0 0 0 A 15 15 0 0 1 0 -30 Z");
    b.setAttribute("fill","#0B0B0F"); b.setAttribute("stroke","#C9A22788"); b.setAttribute("stroke-width","1");
    tj.appendChild(b);
    var dw = document.createElementNS(SVG_NS, "circle");
    dw.setAttribute("cx","0"); dw.setAttribute("cy","15"); dw.setAttribute("r","5"); dw.setAttribute("fill","#E8C766");
    tj.appendChild(dw);
    var db = document.createElementNS(SVG_NS, "circle");
    db.setAttribute("cx","0"); db.setAttribute("cy","-15"); db.setAttribute("r","5"); db.setAttribute("fill","#0B0B0F");
    tj.appendChild(db); svg.appendChild(tj);
    var T = [[1,1,1,0],[1,1,0,45],[1,0,1,90],[1,0,0,135],[0,1,1,180],[0,1,0,225],[0,0,1,270],[0,0,0,315]];
    var R = 70, W = 22, H = 4, G = 6;
    T.forEach(function (t) {
      var rad = (t[3] - 90) * Math.PI / 180;
      var cx = 100 + R * Math.cos(rad), cy = 100 + R * Math.sin(rad);
      var g = document.createElementNS(SVG_NS, "g");
      g.setAttribute("transform","translate(" + cx + "," + cy + ") rotate(" + t[3] + ")");
      for (var i = 0; i < 3; i++) {
        var y = -((H*3 + G*2)/2) + i*(H+G);
        if (t[i] === 1) {
          var r = document.createElementNS(SVG_NS, "rect");
          r.setAttribute("x", String(-W/2)); r.setAttribute("y", String(y));
          r.setAttribute("width", String(W)); r.setAttribute("height", String(H));
          r.setAttribute("rx","1"); r.setAttribute("fill","#E8C766"); r.setAttribute("opacity","0.8");
          g.appendChild(r);
        } else {
          var w2 = (W-3)/2;
          [-W/2, 3/2].forEach(function (x) {
            var r = document.createElementNS(SVG_NS, "rect");
            r.setAttribute("x", String(x)); r.setAttribute("y", String(y));
            r.setAttribute("width", String(w2)); r.setAttribute("height", String(H));
            r.setAttribute("rx","1"); r.setAttribute("fill","#E8C766"); r.setAttribute("opacity","0.8");
            g.appendChild(r);
          });
        }
      }
      svg.appendChild(g);
    });
    return svg;
  }
  // Hiển thị loading trong tab
  function showTabLoading(panel, message) {
    panel.replaceChildren();
    var box = document.createElement("div");
    box.className = "kd-tab-loading";
    var bg = document.createElement("div");
    bg.className = "kd-tl-bagua";
    bg.appendChild(bagua());
    var txt = document.createElement("div");
    txt.className = "kd-tl-text";
    txt.textContent = message || "Đang diễn giải";
    var dots = document.createElement("span");
    dots.className = "kd-tl-dots";
    dots.innerHTML = "<span></span><span></span><span></span>";
    txt.appendChild(dots);
    box.append(bg, txt);
    panel.appendChild(box);
  }

  var TONG = { 6: "Lão Âm", 7: "Thiếu Dương", 8: "Thiếu Âm", 9: "Lão Dương" };
  function threeCoins(coins, landed) {
    var wrap = document.createElement("div"); wrap.className = "kd-coins";
    coins.forEach(function (c) {
      var coin = document.createElement("div");
      coin.className = "kd-coin" + (landed ? " landed" : "");
      if (landed) coin.style.transform = c ? "rotateY(0deg)" : "rotateY(180deg)";
      var f = document.createElement("div"); f.className = "face front"; f.textContent = "乾元";
      var b = document.createElement("div"); b.className = "face back"; b.textContent = "坤順";
      coin.append(f, b); wrap.appendChild(coin);
    });
    return wrap;
  }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function animateCoins(container, coinsLog, done) {
    container.innerHTML = "";
    var stage = document.createElement("div"); stage.className = "kd-coin-stage";
    var st = document.createElement("div"); st.className = "kd-coin-status"; stage.appendChild(st);
    var hold = document.createElement("div"); stage.appendChild(hold);
    container.appendChild(stage);
    function step(i) {
      if (i >= coinsLog.length) return Promise.resolve();
      var e = coinsLog[i];
      hold.innerHTML = ""; hold.appendChild(threeCoins(e.coins, false));
      st.innerHTML = "Hào " + (i + 1) + "/6 — đang gieo…";
      return sleep(700).then(function () {
        hold.innerHTML = ""; hold.appendChild(threeCoins(e.coins, true));
        var lbl = e.coins.map(function (c) { return c ? "Dương" : "Âm"; }).join(" · ");
        st.innerHTML = "Hào " + (i + 1) + "/6 — " + lbl + " → <b>" + (TONG[e.tong] || "?") + "</b>";
        if (done) done(i, e);
        return sleep(350).then(function () { return step(i + 1); });
      });
    }
    return step(0);
  }
  function section(title) {
    var s = document.createElement("section"); s.className = "kd-section";
    var h = document.createElement("h3"); h.textContent = title; s.appendChild(h); return s;
  }
  function para(t) { var p = document.createElement("p"); p.textContent = t; return p; }
  function list(items) {
    var ul = document.createElement("ul");
    items.forEach(function (it) {
      if (!it) return;
      var li = document.createElement("li");
      li.textContent = typeof it === "string" ? it : (it.hanh_dong || JSON.stringify(it));
      ul.appendChild(li);
    });
    return ul;
  }
  function paras(c, txt) {
    if (!txt) return;
    String(txt).split(/\n\n+|\n/).filter(function (x) { return x.trim(); }).forEach(function (p) { c.appendChild(para(p)); });
  }
  function byField(c, lv) {
    if (!lv) return;
    var map = [
      ["💕 Tình duyên", lv.tinh_duyen], ["💼 Sự nghiệp", lv.su_nghiep],
      ["🌿 Sức khỏe", lv.suc_khoe], ["💰 Tài vận", lv.tai_van], ["🎓 Học hành", lv.hoc_hanh]
    ];
    var has = map.some(function (kv) { return kv[1] && String(kv[1]).trim(); });
    if (!has) return;
    var s = section("🎯 Ứng dụng theo lĩnh vực");
    map.forEach(function (kv) { if (kv[1] && String(kv[1]).trim()) s.appendChild(para(kv[0] + ": " + kv[1])); });
    c.appendChild(s);
  }
  function panelCore(panel, d) {
    panel.replaceChildren();
    if (d.tong_quan) { var s1 = section("📖 Tổng quan"); paras(s1, d.tong_quan); panel.appendChild(s1); }
    if (d.y_nghia_cot_loi) { var s2 = section("💡 Ý nghĩa cốt lõi"); paras(s2, d.y_nghia_cot_loi); panel.appendChild(s2); }
    if (d.xu_huong_bien_hoa) { var s3 = section("🔄 Xu hướng biến hóa"); paras(s3, d.xu_huong_bien_hoa); panel.appendChild(s3); }
    if (d.phan_tich_theo_cau_hoi) { var s4 = section("🔍 Phân tích theo câu hỏi của bạn"); paras(s4, d.phan_tich_theo_cau_hoi); panel.appendChild(s4); }
    byField(panel, d.theo_linh_vuc);
  }
  function panelTamHop(panel, d) {
    panel.replaceChildren();
    if (!d || (!d.thien_thoi && !d.dia_loi && !d.nhan_hoa)) {
      var ph = document.createElement("p");
      ph.className = "kd-placeholder";
      ph.textContent = "Đang tải luận giải Tam Hợp…";
      panel.appendChild(ph);
      return;
    }
    var s = section("🌏 Thiên Thời · Địa Lợi · Nhân Hòa");
    var w = document.createElement("div"); w.className = "kd-tdn";
    [["thien","☀️ Thiên Thời",d.thien_thoi],["dia","🌍 Địa Lợi",d.dia_loi],["nhan","🤝 Nhân Hòa",d.nhan_hoa]].forEach(function (kv) {
      if (!kv[2] || !String(kv[2]).trim()) return;
      var it = document.createElement("div"); it.className = "kd-tdn-item"; it.dataset.kind = kv[0];
      var b = document.createElement("b"); b.textContent = kv[1];
      var p = document.createElement("p"); p.textContent = kv[2];
      it.append(b, p); w.appendChild(it);
    });
    s.appendChild(w);
    if (d.tong_ket) { var tk = para("💎 Tổng kết: " + d.tong_ket); tk.style.fontStyle = "italic"; s.appendChild(tk); }
    panel.appendChild(s);
  }
  function panelAction(panel, d) {
    panel.replaceChildren();
    if (d.goi_y_hanh_dong && d.goi_y_hanh_dong.length) { var s1 = section("📌 Hành động cụ thể"); s1.appendChild(list(d.goi_y_hanh_dong)); panel.appendChild(s1); }
    if (d.diem_can_can_nhac && d.diem_can_can_nhac.length) { var s2 = section("⚠️ Cần cân nhắc"); s2.appendChild(list(d.diem_can_can_nhac)); panel.appendChild(s2); }
    if (d.loi_khuyen_thoi_diem) { var s3 = section("⏰ Lời khuyên thời điểm"); paras(s3, d.loi_khuyen_thoi_diem); panel.appendChild(s3); }
  }
  function init() {
    var bSlot = document.getElementById("kd-bagua-slot");
    if (bSlot) bSlot.appendChild(bagua());
    var qEl = document.getElementById("kd-quote");
    if (qEl) qEl.textContent = QUOTES[Math.floor(Math.random() * QUOTES.length)];
    var cEl = document.getElementById("kd-chips");
    if (cEl) {
      CHIPS.forEach(function (s) {
        var btn = document.createElement("button");
        btn.type = "button"; btn.className = "kd-chip"; btn.textContent = s.icon + " " + s.label;
        btn.addEventListener("click", function () {
          var ta = document.getElementById("kd-question");
          if (!ta) return;
          var cur = ta.value.trim();
          ta.value = cur ? cur + " " + s.text : s.text;
          ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
        });
        cEl.appendChild(btn);
      });
    }
    var form = document.getElementById("kd-form");
    var ta = document.getElementById("kd-question");
    var sub = document.getElementById("kd-submit");
    var rEl = document.getElementById("kd-result");
    if (!form || !ta || !sub || !rEl) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var q = ta.value.trim();
      if (q.length < 5) {
        rEl.replaceChildren();
        var err = document.createElement("div"); err.className = "kd-error";
        err.textContent = "Câu hỏi cần từ 5 đến 500 ký tự.";
        rEl.appendChild(err); return;
      }
      sub.disabled = true; rEl.replaceChildren();
      runDiv(q, rEl).then(function () { sub.disabled = false; });
    });
  }
  function runDiv(question, rEl) {
    var load = document.createElement("div"); load.className = "kd-loading";
    var bg = document.createElement("div"); bg.className = "kd-bagua"; bg.appendChild(bagua());
    var msg = document.createElement("div"); msg.className = "kd-loading-msg"; msg.textContent = LOADING[0];
    var pr = document.createElement("div"); pr.className = "kd-progress";
    load.append(bg, msg, pr); rEl.appendChild(load);
    var mi = 0;
    var tmr = setInterval(function () { mi = (mi + 1) % LOADING.length; msg.textContent = LOADING[mi]; }, 2500);
    var cast = null, panels = null;
    function cleanup() { clearInterval(tmr); if (load.parentNode) load.remove(); }
    function buildLayout() {
      cleanup(); rEl.replaceChildren();
      var grid = document.createElement("div"); grid.className = "kd-result";
      var c1 = document.createElement("div"), c2 = document.createElement("div");
      if (cast) {
        hexagram(c1, cast.que_chinh, "Quẻ chủ");
        if (cast.que_bien) hexagram(c2, cast.que_bien, "Quẻ biến");
        else c2.innerHTML = '<p class="kd-placeholder">Không có hào động — quẻ không biến.</p>';
      }
      grid.append(c1, c2); rEl.appendChild(grid);
      var tabs = document.createElement("div"); tabs.className = "kd-tabs";
      var defs = [{id:"core",label:"📖 Quẻ từ"},{id:"tamhop",label:"🌏 Tam Hợp"},{id:"action",label:"📌 Hành động"}];
      var p = {};
      defs.forEach(function (t, i) {
        var tab = document.createElement("button");
        tab.className = "kd-tab" + (i === 0 ? " active" : "");
        tab.textContent = t.label; tab.dataset.tab = t.id;
        tabs.appendChild(tab);
        var panel = document.createElement("div");
        panel.className = "kd-panel"; panel.dataset.panel = t.id;
        if (i !== 0) panel.style.display = "none";
        p[t.id] = panel;
      });
      rEl.appendChild(tabs);
      Object.keys(p).forEach(function (k) { rEl.appendChild(p[k]); });

      // Hiện loading cho từng tab
      showTabLoading(p.core, "Đang luận giải Quẻ từ");
      showTabLoading(p.tamhop, "Đang luận giải Tam Hợp");
      showTabLoading(p.action, "Đang tổng hợp Hành động");
      tabs.addEventListener("click", function (e) {
        var t = e.target.closest(".kd-tab"); if (!t) return;
        tabs.querySelectorAll(".kd-tab").forEach(function (x) { x.classList.toggle("active", x === t); });
        var id = t.dataset.tab;
        Object.keys(p).forEach(function (k) { p[k].style.display = (k === id) ? "" : "none"; });
      });
      return p;
    }
    function ensure() { if (!panels && cast) panels = buildLayout(); return panels; }
    return stream(question, {
      onCast: function (c) {
        cast = c;
        var cs = document.createElement("div");
        load.appendChild(cs);
        animateCoins(cs, c.coins_log, function () {});
      },
      onCore: function (c) { var p = ensure(); if (p) panelCore(p.core, c); },
      onTamHop: function (c) { var p = ensure(); if (p) panelTamHop(p.tamhop, c); },
      onAction: function (c) { var p = ensure(); if (p) panelAction(p.action, c); },
      onError: function (e) {
        var msg = (e && e.message) || "Có lỗi xảy ra.";
        // Bỏ qua lỗi từ Chrome extension
        if (/chrome-extension|stack size/i.test(msg)) {
          console.warn("Bỏ qua lỗi không nghiêm trọng:", msg);
          return;
        }
        cleanup();
        var b = document.createElement("div"); b.className = "kd-error";
        b.textContent = msg;
        rEl.appendChild(b);
      },
      onDone: function () {
        cleanup();
        if (!panels && cast) ensure();
        var n = document.createElement("p"); n.className = "kd-note";
        n.textContent = "Diễn giải mang tính tham khảo văn hóa — không phải lời khuyên chuyên môn.";
        rEl.appendChild(n);
      }
    }).catch(function (e) {
      cleanup();
      var b = document.createElement("div"); b.className = "kd-error";
      b.textContent = e.message || "Không thể hoàn tất yêu cầu.";
      rEl.appendChild(b);
    });
  }
  function boot() { if (document.getElementById("kd-app")) init(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
