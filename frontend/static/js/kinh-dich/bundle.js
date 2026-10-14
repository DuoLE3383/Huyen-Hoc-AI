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
  var LOADING = [
    "AI đang phân tích diễn giải dựa trên Kinh Dịch huyền học và Bát Tự mệnh chủ…",
    "Đang kết nối vũ trụ…",
    "Đang gieo 3 đồng xu 6 lần…",
    "Đang tra cứu 64 quẻ Kinh Dịch…",    
    "Đang luận giải ý nghĩa cá nhân hoá…",
    "Đang đối chiếu quẻ chính · hào động · quẻ biến…",
    "Hãy kiên nhẫn nhé…"
  ];
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
  function getBatTu() {
    var ngay = document.getElementById("kd-ngay-sinh");
    var gio  = document.getElementById("kd-gio-sinh");
    var gt   = document.getElementById("kd-gioi-tinh");
    var ns   = document.getElementById("kd-noi-sinh");
    if (!ngay || !gio || !gt) return null;
    if (!ngay.value || !gio.value || !gt.value) return null;
    return {
      ngay_sinh: ngay.value,
      gio_sinh: gio.value,
      gioi_tinh: gt.value,
      noi_sinh: (ns && ns.value.trim()) || null
    };
  }

  function checkBatTuValid() {
    var bt = getBatTu();
    var sub = document.getElementById("kd-submit");
    var preview = document.getElementById("kd-battu-preview");
    if (sub) {
      sub.disabled = !bt;
      sub.title = bt ? "" : "Vui lòng điền đầy đủ Bát Tự";
    }
    if (bt && preview) {
      fetch("/api/bat-tu/lap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bt)
      })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
          if (!d) { preview.hidden = true; return; }
          var tt = d.tu_tru;
          preview.innerHTML =
            "<b>Tứ Trụ:</b> " + tt.nam.full + " / " + tt.thang.full + " / " + tt.ngay.full + " / " + tt.gio.full +
            "<br><b>Nhật chủ:</b> " + d.nhat_chu + " (" + d.nhat_chu_hanh + ")" +
            "<br><b>Ngũ hành:</b> Kim=" + d.hanh_count.Kim + " Mộc=" + d.hanh_count.Mộc +
            " Thủy=" + d.hanh_count.Thủy + " Hỏa=" + d.hanh_count.Hỏa + " Thổ=" + d.hanh_count.Thổ;
          preview.hidden = false;
        })
        .catch(function () { preview.hidden = true; });
    } else if (preview) {
      preview.hidden = true;
    }
  }

  function stream(question, h, batTu) {
    h = h || {};
    var tok = safeGetToken();
    var headers = { "Content-Type": "application/json", "Accept": "text/event-stream" };
    if (tok) headers.Authorization = "Bearer " + tok;
    var body = { cau_hoi: question };
    if (typeof batTu !== "undefined" && batTu) {
      body.ngay_sinh = batTu.ngay_sinh;
      body.gio_sinh  = batTu.gio_sinh;
      body.gioi_tinh = batTu.gioi_tinh;
      if (batTu.noi_sinh) body.noi_sinh = batTu.noi_sinh;
    }
    return fetch("/api/kinh-dich-stream", { method: "POST", headers: headers, body: JSON.stringify(body) }).then(function (res) {
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
            else if (e.event === "hao_chuyen" && h.onHaoChuyen) h.onHaoChuyen(e.data);
            else if (e.event === "que_bien" && h.onQueBien) h.onQueBien(e.data);
            else if (e.event === "unlock_token" && h.onUnlockToken) h.onUnlockToken(e.data);
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
  function showTabLoading(panel, message, estimateSec) {
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

    // Progress bar + đếm ngược nếu có estimate
    if (estimateSec && estimateSec > 0) {
      var pb = document.createElement("div");
      pb.className = "kd-tl-progress";
      var inner = document.createElement("div");
      inner.className = "kd-tl-progress-inner";
      inner.style.width = "0%";
      pb.appendChild(inner);
      var countEl = document.createElement("div");
      countEl.className = "kd-tl-count";
      countEl.textContent = "Ước tính " + estimateSec + "s";
      box.append(pb, countEl);

      var start = Date.now();
      var timer = setInterval(function () {
        var elapsed = (Date.now() - start) / 1000;
        var pct = Math.min(100, (elapsed / estimateSec) * 100);
        inner.style.width = pct + "%";
        var remain = Math.max(0, Math.round(estimateSec - elapsed));
        countEl.textContent = remain > 0
          ? "... " + remain + "s..."
          : "Sắp xong...";
        if (elapsed > estimateSec * 1.5) {
          clearInterval(timer);
          countEl.textContent = "Đang xử lý...";
        }
      }, 500);
      panel._kdLoadingTimer = timer;
    }
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
    if (panel._kdLoadingTimer) { clearInterval(panel._kdLoadingTimer); panel._kdLoadingTimer = null; }
    panel.replaceChildren();
    var hv = window._kdHanvanGoc || null;

    // ═══ 1. KẾT LUẬN — ĐẦU TIÊN ═══
    if (d.ket_luan) {
      var sK = section("🎯 Kết Luận");
      var kl = (d.ket_luan || "").toUpperCase().trim();
      var hanMap = { "CÁT": "吉", "HUNG": "凶", "TĨNH": "靜" };
      var clsMap = { "CÁT": "cat", "HUNG": "hung", "TĨNH": "tinh" };
      var descMap = {
        "CÁT": "Tốt lành — nên tiến hành",
        "HUNG": "Bất lợi — không nên hành động",
        "TĨNH": "Tĩnh lặng — giữ nguyên, chờ thời"
      };
      var cls = clsMap[kl] || "tinh";
      var han = hanMap[kl] || "";

      var box = document.createElement("div");
      box.className = "kd-ket-luan kd-ket-luan-" + cls;

      // Hán tự lớn
      if (han) {
        var hanEl = document.createElement("div");
        hanEl.className = "kd-ket-luan-han";
        hanEl.textContent = han;
        box.appendChild(hanEl);
      }

      // CÁT/HUNG/TĨNH
      var big = document.createElement("div");
      big.className = "kd-ket-luan-big";
      big.textContent = kl;
      box.appendChild(big);

      // Mô tả ngắn
      var desc = document.createElement("div");
      desc.className = "kd-ket-luan-desc";
      desc.textContent = descMap[kl] || "";
      box.appendChild(desc);

      sK.appendChild(box);

      // Ý nghĩa cụ thể cho câu hỏi
      if (d.ket_luan_y_nghia) {
        var yn = document.createElement("p");
        yn.className = "kd-ket-luan-yn";
        yn.innerHTML = "<b>Ý nghĩa:</b> " + d.ket_luan_y_nghia;
        sK.appendChild(yn);
      }

      // Lý do chi tiết
      if (d.ly_do) {
        var ld = document.createElement("p");
        ld.className = "kd-ly-do";
        ld.innerHTML = "<b>Lý do:</b> " + d.ly_do;
        sK.appendChild(ld);
      }
      panel.appendChild(sK);
    }

    // ═══ 2. THỜI ĐIỂM ═══
    if (d.thoi_diem_tot_nhat) {
      var s4 = section("✅ Thời Điểm Tốt Nhất");
      var p4 = document.createElement("p");
      p4.className = "kd-thoi-diem-tot";
      p4.textContent = d.thoi_diem_tot_nhat;
      s4.appendChild(p4);
      panel.appendChild(s4);
    }
    if (d.thoi_diem_nen_tranh && d.thoi_diem_nen_tranh.toLowerCase() !== "không có") {
      var s5 = section("⚠️ Thời Điểm Nên Tránh");
      var p5 = document.createElement("p");
      p5.className = "kd-thoi-diem-tranh";
      p5.textContent = d.thoi_diem_nen_tranh;
      s5.appendChild(p5);
      panel.appendChild(s5);
    }

    // ═══ 3. THOÁN TỪ ═══
    var thoan_goc = hv && hv.thoan_tu && (hv.thoan_tu.han_viet || hv.thoan_tu.han) ? hv.thoan_tu : null;
    if (thoan_goc) {
      var s1 = section("📜 Thoán Từ");
      if (thoan_goc.han) {
        var han = document.createElement("p");
        han.className = "kd-han";
        han.textContent = thoan_goc.han;
        s1.appendChild(han);
      }
      if (thoan_goc.han_viet) {
        var pa = document.createElement("p");
        pa.className = "kd-phien-am";
        pa.textContent = thoan_goc.han_viet;
        s1.appendChild(pa);
      }
      if (thoan_goc.dich) {
        var dv = document.createElement("p");
        dv.innerHTML = "<b>Dịch:</b> " + thoan_goc.dich;
        s1.appendChild(dv);
      }
      if (thoan_goc.giang) {
        var gg = document.createElement("p");
        gg.innerHTML = "<b>Giảng:</b> " + thoan_goc.giang;
        s1.appendChild(gg);
      }
      panel.appendChild(s1);
    } else if (d.thoan_tu && d.thoan_tu.dich) {
      var s1b = section("📜 Thoán Từ");
      var dvb = document.createElement("p");
      dvb.innerHTML = "<b>Dịch:</b> " + d.thoan_tu.dich;
      s1b.appendChild(dvb);
      if (d.thoan_tu.giang) {
        var ggb = document.createElement("p");
        ggb.innerHTML = "<b>Giảng:</b> " + d.thoan_tu.giang;
        s1b.appendChild(ggb);
      }
      panel.appendChild(s1b);
    }

    // ═══ 4. TƯỢNG TỪ ═══
    if (d.tuong_tu) {
      var s2 = section("🏔️ Tượng Từ");
      if (d.tuong_tu.dich) {
        var d2 = document.createElement("p");
        d2.innerHTML = "<b>Dịch:</b> " + d.tuong_tu.dich;
        s2.appendChild(d2);
      }
      if (d.tuong_tu.bai_hoc) {
        var b2 = document.createElement("p");
        b2.innerHTML = "<b>Bài học:</b> " + d.tuong_tu.bai_hoc;
        s2.appendChild(b2);
      }
      panel.appendChild(s2);
    }

    // ═══ 5. LỜI KHUYÊN ═══
    if (d.loi_khuyen) {
      var s7 = section("✅ Lời Khuyên");
      paras(s7, d.loi_khuyen);
      panel.appendChild(s7);
    }
  }
  function panelHaoChuyen(panel, d) {
    if (panel._kdLoadingTimer) { clearInterval(panel._kdLoadingTimer); panel._kdLoadingTimer = null; }
    panel.replaceChildren();
    if (!d) {
      var ph = document.createElement("p");
      ph.className = "kd-placeholder";
      ph.textContent = "Đang tải luận giải Hào Chuyển…";
      panel.appendChild(ph);
      return;
    }
    // Khái niệm
    if (d.khai_niem) {
      var s0 = section("🎋 Khái Niệm Hào Động");
      paras(s0, d.khai_niem);
      panel.appendChild(s0);
    }
    // Từng hào động
    if (d.hao_dong && d.hao_dong.length) {
      var s1 = section("⚡ Chi Tiết Từng Hào");
      d.hao_dong.forEach(function (h) {
        var box = document.createElement("div");
        box.className = "kd-hao-item";
        var title = document.createElement("div");
        title.className = "kd-hao-title";
        title.textContent = h.ten + (h.chuyen_hoa ? " — " + h.chuyen_hoa : "");
        box.appendChild(title);
        if (h.han) {
          var han = document.createElement("p");
          han.className = "kd-han";
          han.textContent = h.han;
          box.appendChild(han);
        }


        if (h.giang) {
          var gg = document.createElement("p");
          gg.innerHTML = "<b>Giảng:</b> " + h.giang;
          box.appendChild(gg);
        }
        if (h.ung_bat_tu) {
          var ubt = document.createElement("p");
          ubt.className = "kd-ung-bat-tu";
          ubt.innerHTML = "<b>Ứng Bát Tự:</b> " + h.ung_bat_tu;
          box.appendChild(ubt);
        }
        s1.appendChild(box);
      });
      panel.appendChild(s1);
    }
    // Tổng hợp
    if (d.tong_hop) {
      var s2 = section("🎯 Tổng Hợp");
      paras(s2, d.tong_hop);
      panel.appendChild(s2);
    }
  }
  function panelQueBien(panel, d) {
    if (panel._kdLoadingTimer) { clearInterval(panel._kdLoadingTimer); panel._kdLoadingTimer = null; }
    panel.replaceChildren();
    if (!d) {
      var ph = document.createElement("p");
      ph.className = "kd-placeholder";
      ph.textContent = "Đang tải luận giải Quẻ Biến…";
      panel.appendChild(ph);
      return;
    }
    // Xu hướng
    if (d.xu_huong) {
      var s1 = section("🔄 Xu Hướng Tương Lai");
      paras(s1, d.xu_huong);
      panel.appendChild(s1);
    }
    // Lời khuyên
    if (d.loi_khuyen) {
      var s2 = section("✅ Lời Khuyên");
      paras(s2, d.loi_khuyen);
      panel.appendChild(s2);
    }
    // ═══ PAYWALL: Diệu Nghĩa Cá Nhân ═══
    var s3 = section("🌟 Diệu Nghĩa Cá Nhân");
    s3.classList.add("kd-paywall-section");

    var lockBox = document.createElement("div");
    lockBox.className = "kd-paywall-box";
    lockBox.id = "kd-paywall-box";
    lockBox.innerHTML =
      "<div class='kd-paywall-icon'>🔒</div>" +
      "<div class='kd-paywall-text'>" +
      "<b>Lời quẻ dành riêng cho câu hỏi của bạn</b><br>" +
      "Luận giải chi tiết dựa trên quẻ chính, hào động, quẻ biến — " +
      "kết hợp Bát Tự mệnh chủ để cá nhân hoá." +
      "</div>" +
      "<button type='button' class='kd-unlock-btn' id='kd-unlock-btn'>" +
      "🎬 Xem quảng cáo để mở khoá" +
      "</button>" +
      "<div class='kd-paywall-note'>Miễn phí · Không cần đăng nhập</div>";

    s3.appendChild(lockBox);

    // Box chứa nội dung sau unlock (ẩn ban đầu)
    var contentBox = document.createElement("div");
    contentBox.id = "kd-personal-content";
    contentBox.style.display = "none";
    s3.appendChild(contentBox);

    panel.appendChild(s3);

    // Wire nút unlock
    setTimeout(function () {
      var btn = document.getElementById("kd-unlock-btn");
      if (btn) btn.addEventListener("click", kdShowAdModal);
    }, 50);
  }

  // ═══ Modal quảng cáo (fake) ═══
  function kdShowAdModal() {
    var modal = document.createElement("div");
    modal.className = "kd-ad-modal";
    modal.innerHTML =
      "<div class='kd-ad-content'>" +
      "<div class='kd-ad-title'>Đang phát quảng cáo…</div>" +
      "<div class='kd-ad-box'>" +
      "<div class='kd-ad-placeholder'>🎬 [Quảng cáo]</div>" +
      "<div class='kd-ad-count' id='kd-ad-count'>5</div>" +
      "</div>" +
      "<div class='kd-ad-note'>Vui lòng đợi hết quảng cáo để mở khoá</div>" +
      "</div>";
    document.body.appendChild(modal);

    var count = 5;
    var el = document.getElementById("kd-ad-count");
    var timer = setInterval(function () {
      count--;
      if (el) el.textContent = count;
      if (count <= 0) {
        clearInterval(timer);
        modal.remove();
        kdCallUnlock();
      }
    }, 1000);
  }

  // ═══ Gọi API unlock ═══
  var _kdUnlockSid = null;
  try { _kdUnlockSid = localStorage.getItem("kd_unlock_sid"); } catch (e) {}

  function kdCallUnlock() {
    if (!_kdUnlockSid) {
      alert("Không có session — vui lòng gieo quẻ lại.");
      return;
    }
    fetch("/api/kinh-dich/unlock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: _kdUnlockSid }),
    })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r); })
      .then(function (d) {
        var box = document.getElementById("kd-paywall-box");
        var content = document.getElementById("kd-personal-content");
        if (box) box.style.display = "none";
        if (content) {
          content.style.display = "";
          content.innerHTML =
            "<div class='kd-personal-inner'>" +
            parasHtml(d.dieu_nghia_ca_nhan || "") +
            "</div>";
        }
      })
      .catch(function () {
        alert("Không mở được khoá (session: " + (_kdUnlockSid || "null") + "). Session có thể đã hết hạn (48h) — vui lòng gieo quẻ lại.");
      });
  }

  function parasHtml(txt) {
    if (!txt) return "";
    return String(txt)
      .split(/\n\n+|\n/)
      .filter(function (x) { return x.trim(); })
      .map(function (p) { return "<p>" + p + "</p>"; })
      .join("");
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
    // Wire Bát Tự validation
    ["kd-ngay-sinh", "kd-gio-sinh", "kd-gioi-tinh", "kd-noi-sinh"].forEach(function(id) {
      var el = document.getElementById(id);
      if (el) {
        el.addEventListener("change", checkBatTuValid);
        el.addEventListener("input", checkBatTuValid);
      }
    });
    checkBatTuValid();

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var q = ta.value.trim();
      var bt = getBatTu();
      if (!bt) {
        rEl.replaceChildren();
        var err = document.createElement("div"); err.className = "kd-error";
        err.textContent = "Vui lòng điền đầy đủ Bát Tự (ngày/giờ sinh + giới tính) trước khi gieo quẻ.";
        rEl.appendChild(err); return;
      }
      if (q.length < 5) {
        rEl.replaceChildren();
        var err = document.createElement("div"); err.className = "kd-error";
        err.textContent = "Câu hỏi cần từ 5 đến 500 ký tự.";
        rEl.appendChild(err); return;
      }
      sub.disabled = true; rEl.replaceChildren();
      // Xoá session cũ để tránh unlock nhầm session hết hạn
      try { localStorage.removeItem("kd_unlock_sid"); } catch (e) {}
      _kdUnlockSid = null;
      runDiv(q, rEl, bt).then(function () { sub.disabled = false; });
    });
  }
  function runDiv(question, rEl, batTu) {
    var load = document.createElement("div"); load.className = "kd-loading";
    var bg = document.createElement("div"); bg.className = "kd-bagua"; bg.appendChild(bagua());
    var msg = document.createElement("div"); msg.className = "kd-loading-msg"; msg.textContent = LOADING[0];
    var pr = document.createElement("div"); pr.className = "kd-progress";
    load.append(bg, msg, pr); rEl.appendChild(load);
    var mi = 0;
    var tmr = setInterval(function () {
    if (mi < LOADING.length - 1) {
      mi++;
      msg.textContent = LOADING[mi];
    } else {
      // Dừng ở message cuối — không loop
      clearInterval(tmr);
    }
  }, 3500);
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
      var defs = [{id:"core",label:"📖 Quẻ Giảng"},{id:"tamhop",label:"⚡ Hào Chuyển"},{id:"action",label:"🔄 Quẻ Biến"}];
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
      showTabLoading(p.core, "AI đang luận giải Quẻ Giảng", 90);
      showTabLoading(p.tamhop, "AI đang luận giải Hào Chuyển", 80);
      showTabLoading(p.action, "AI đang tổng hợp Quẻ Biến", 70);
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
        if (c.hanvan) window._kdHanvanGoc = c.hanvan;
        var cs = document.createElement("div");
        load.appendChild(cs);
        animateCoins(cs, c.coins_log, function () {});
      },
      onCore: function (c) { var p = ensure(); if (p) panelCore(p.core, c); },
      onHaoChuyen: function (c) { var p = ensure(); if (p) panelHaoChuyen(p.tamhop, c); },
      onQueBien: function (c) { var p = ensure(); if (p) panelQueBien(p.action, c); },
      onUnlockToken: function (c) {
        _kdUnlockSid = c.session_id;
        try { localStorage.setItem("kd_unlock_sid", c.session_id); } catch (e) {}
      },
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
        // (đã xoá disclaimer tham khảo)
      }
    }, batTu).catch(function (e) {
      cleanup();
      var b = document.createElement("div"); b.className = "kd-error";
      b.textContent = e.message || "Không thể hoàn tất yêu cầu.";
      rEl.appendChild(b);
    });
  }
  function boot() {
    if (document.getElementById("kd-app")) init();
    var splash = document.getElementById("kd-splash");
    if (splash) {
      setTimeout(function () {
        splash.classList.add("hide");
        setTimeout(function () { splash.remove(); }, 600);
      }, 1500);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
