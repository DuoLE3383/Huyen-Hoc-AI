// Render từng section của luận giải

export function makeSection(title) {
  const s = document.createElement("section");
  s.className = "kd-section";
  const h = document.createElement("h3");
  h.textContent = title;
  s.appendChild(h);
  return s;
}

export function makePara(text) {
  const p = document.createElement("p");
  p.textContent = text;
  return p;
}

export function makeList(items, prefix = "▸") {
  const ul = document.createElement("ul");
  for (const it of items) {
    if (!it) continue;
    const li = document.createElement("li");
    li.textContent = typeof it === "string" ? it : (it.hanh_dong || JSON.stringify(it));
    ul.appendChild(li);
  }
  return ul;
}

export function renderParagraphs(container, content) {
  if (!content) return;
  const paras = String(content).split(/\n\n+|\n/).filter(x => x.trim());
  paras.forEach(p => container.appendChild(makePara(p)));
}

export function renderTamHop(container, tdn) {
  if (!tdn || (!tdn.thien_thoi && !tdn.dia_loi && !tdn.nhan_hoa)) return;

  const sec = makeSection("🌏 Thiên Thời · Địa Lợi · Nhân Hòa");
  const wrap = document.createElement("div");
  wrap.className = "kd-tdn";

  const map = [
    ["thien", "☀️ Thiên Thời", tdn.thien_thoi],
    ["dia",   "🌍 Địa Lợi",   tdn.dia_loi],
    ["nhan",  "🤝 Nhân Hòa",  tdn.nhan_hoa],
  ];
  for (const [kind, name, val] of map) {
    if (!val || !String(val).trim()) continue;
    const item = document.createElement("div");
    item.className = "kd-tdn-item";
    item.dataset.kind = kind;
    const b = document.createElement("b");
    b.textContent = name;
    const p = document.createElement("p");
    p.textContent = val;
    item.append(b, p);
    wrap.appendChild(item);
  }
  sec.appendChild(wrap);

  if (tdn.tong_ket) {
    const tk = document.createElement("p");
    tk.style.fontStyle = "italic";
    tk.textContent = `💎 Tổng kết: ${tdn.tong_ket}`;
    sec.appendChild(tk);
  }

  container.appendChild(sec);
}

export function renderByField(container, lv) {
  if (!lv) return;
  const map = [
    ["💕 Tình duyên", lv.tinh_duyen],
    ["💼 Sự nghiệp", lv.su_nghiep],
    ["🌿 Sức khỏe", lv.suc_khoe],
    ["💰 Tài vận", lv.tai_van],
    ["🎓 Học hành", lv.hoc_hanh],
  ];
  const has = map.some(([_, v]) => v && String(v).trim());
  if (!has) return;

  const sec = makeSection("🎯 Ứng dụng theo lĩnh vực");
  map.forEach(([name, val]) => {
    if (val && String(val).trim()) {
      sec.appendChild(makePara(`${name}: ${val}`));
    }
  });
  container.appendChild(sec);
}
