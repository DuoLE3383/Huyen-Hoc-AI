// SVG 6 hào + bát quái

const SVG_NS = "http://www.w3.org/2000/svg";

/** Vẽ 1 hào (âm hoặc dương), trả về <svg> */
function haoSVG(isDuong, isLao) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 100 14");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.classList.add("kd-hao-svg");

  const cls = "bar" + (isLao ? " lao" : "");

  if (isDuong) {
    // Dương: 1 thanh liền
    const rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("x", "0");
    rect.setAttribute("y", "0");
    rect.setAttribute("width", "100");
    rect.setAttribute("height", "14");
    rect.setAttribute("rx", "2");
    rect.setAttribute("class", cls);
    svg.appendChild(rect);
  } else {
    // Âm: 2 thanh, khoảng giữa 20%
    const gap = 20;
    const w = (100 - gap) / 2;
    for (const x of [0, w + gap]) {
      const rect = document.createElementNS(SVG_NS, "rect");
      rect.setAttribute("x", String(x));
      rect.setAttribute("y", "0");
      rect.setAttribute("width", String(w));
      rect.setAttribute("height", "14");
      rect.setAttribute("rx", "2");
      rect.setAttribute("class", cls);
      svg.appendChild(rect);
    }
  }
  return svg;
}

/** Render block hexagram vào container */
export function renderHexagram(container, hex, title) {
  container.innerHTML = "";
  if (!hex) return;

  const block = document.createElement("div");
  block.className = "kd-hex-block";

  const h = document.createElement("h3");
  h.className = "kd-hex-title";
  h.textContent = title;
  block.appendChild(h);

  const sub = document.createElement("div");
  sub.className = "kd-hex-sub";
  sub.textContent = `Quẻ ${hex.so} · ${hex.ten}`;
  block.appendChild(sub);

  const box = document.createElement("div");
  box.className = "kd-hexagram";
  const haos = document.createElement("div");
  haos.className = "kd-haos";

  for (const hao of hex.hao || []) {
    const row = document.createElement("div");
    row.className = "kd-hao";

    const num = document.createElement("div");
    num.className = "kd-hao-num";
    num.textContent = String(hao.vi_tri);
    row.appendChild(num);

    row.appendChild(haoSVG(hao.duong, hao.dong));

    const lbl = document.createElement("div");
    lbl.className = "kd-hao-label" + (hao.dong ? " dong" : "");
    lbl.textContent = hao.dong ? "động" : (hao.duong ? "dương" : "âm");
    row.appendChild(lbl);

    haos.appendChild(row);
  }
  box.appendChild(haos);
  block.appendChild(box);

  if (hex.thuong_quai && hex.ha_quai) {
    const info = document.createElement("div");
    info.className = "kd-quai-info";
    info.innerHTML =
      `<span>Thượng: <b>${hex.thuong_quai.ten} ${hex.thuong_quai.tuong}</b></span>` +
      `<span>Hạ: <b>${hex.ha_quai.ten} ${hex.ha_quai.tuong}</b></span>`;
    block.appendChild(info);
  }

  container.appendChild(block);
}

/** Tạo SVG bát quái 8 quái xung quanh */
export function createBaguaSVG() {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 200 200");
  svg.classList.add("kd-bagua");

  // Vòng tròn ngoài
  const circle = document.createElementNS(SVG_NS, "circle");
  circle.setAttribute("cx", "100");
  circle.setAttribute("cy", "100");
  circle.setAttribute("r", "92");
  circle.setAttribute("fill", "none");
  circle.setAttribute("stroke", "#C9A22755");
  circle.setAttribute("stroke-width", "1");
  svg.appendChild(circle);

  // Thái cực ở giữa
  const taiji = document.createElementNS(SVG_NS, "g");
  taiji.setAttribute("transform", "translate(100,100)");
  // Nửa trắng
  const white = document.createElementNS(SVG_NS, "path");
  white.setAttribute("d", "M 0 -30 A 30 30 0 0 1 0 30 A 15 15 0 0 1 0 0 A 15 15 0 0 0 0 -30 Z");
  white.setAttribute("fill", "#E8C766");
  taiji.appendChild(white);
  // Nửa đen
  const black = document.createElementNS(SVG_NS, "path");
  black.setAttribute("d", "M 0 -30 A 30 30 0 0 0 0 30 A 15 15 0 0 0 0 0 A 15 15 0 0 1 0 -30 Z");
  black.setAttribute("fill", "#0B0B0F");
  black.setAttribute("stroke", "#C9A22788");
  black.setAttribute("stroke-width", "1");
  taiji.appendChild(black);
  // Chấm trắng trong đen
  const dotW = document.createElementNS(SVG_NS, "circle");
  dotW.setAttribute("cx", "0"); dotW.setAttribute("cy", "15");
  dotW.setAttribute("r", "5"); dotW.setAttribute("fill", "#E8C766");
  taiji.appendChild(dotW);
  // Chấm đen trong trắng
  const dotB = document.createElementNS(SVG_NS, "circle");
  dotB.setAttribute("cx", "0"); dotB.setAttribute("cy", "-15");
  dotB.setAttribute("r", "5"); dotB.setAttribute("fill", "#0B0B0F");
  taiji.appendChild(dotB);
  svg.appendChild(taiji);

  // 8 quái xung quanh (vẽ hào 3 vạch)
  const TRIGRAMS_8 = [
    { name: "Càn",  lines: [1, 1, 1], angle: 0 },
    { name: "Đoài", lines: [1, 1, 0], angle: 45 },
    { name: "Ly",   lines: [1, 0, 1], angle: 90 },
    { name: "Chấn", lines: [1, 0, 0], angle: 135 },
    { name: "Tốn",  lines: [0, 1, 1], angle: 180 },
    { name: "Khảm", lines: [0, 1, 0], angle: 225 },
    { name: "Cấn",  lines: [0, 0, 1], angle: 270 },
    { name: "Khôn", lines: [0, 0, 0], angle: 315 },
  ];

  const R = 70;
  const W = 22;
  const H = 4;
  const GAP = 6;

  for (const t of TRIGRAMS_8) {
    const rad = (t.angle - 90) * Math.PI / 180;
    const cx = 100 + R * Math.cos(rad);
    const cy = 100 + R * Math.sin(rad);

    const g = document.createElementNS(SVG_NS, "g");
    // Xoay hướng ra ngoài
    g.setAttribute("transform", `translate(${cx},${cy}) rotate(${t.angle})`);

    // 3 hào từ dưới lên
    for (let i = 0; i < 3; i++) {
      const y = -((H * 3 + GAP * 2) / 2) + i * (H + GAP);
      if (t.lines[i] === 1) {
        const r = document.createElementNS(SVG_NS, "rect");
        r.setAttribute("x", String(-W / 2));
        r.setAttribute("y", String(y));
        r.setAttribute("width", String(W));
        r.setAttribute("height", String(H));
        r.setAttribute("rx", "1");
        r.setAttribute("fill", "#E8C766");
        r.setAttribute("opacity", "0.8");
        g.appendChild(r);
      } else {
        const w2 = (W - 3) / 2;
        for (const x of [-W / 2, 3 / 2]) {
          const r = document.createElementNS(SVG_NS, "rect");
          r.setAttribute("x", String(x));
          r.setAttribute("y", String(y));
          r.setAttribute("width", String(w2));
          r.setAttribute("height", String(H));
          r.setAttribute("rx", "1");
          r.setAttribute("fill", "#E8C766");
          r.setAttribute("opacity", "0.8");
          g.appendChild(r);
        }
      }
    }
    svg.appendChild(g);
  }

  return svg;
}
