import { streamDivination } from "./api.js";
import { renderHexagram, createBaguaSVG } from "./hexagram.js";
import { animateCoins } from "./coin-toss.js";
import {
  LOADING_MESSAGES, DAILY_QUOTES, SUGGESTIONS,
} from "./constants.js";
import {
  makeSection, makePara, makeList, renderParagraphs,
  renderTamHop, renderByField,
} from "./render.js";

// ─── Init: bát quái + quote + chips ───
const root = document.getElementById("kd-app");
if (root) init();

function init() {
  // Bát quái
  const baguaSlot = document.getElementById("kd-bagua-slot");
  if (baguaSlot) baguaSlot.appendChild(createBaguaSVG());

  // Quote ngẫu nhiên
  const quoteEl = document.getElementById("kd-quote");
  if (quoteEl) {
    quoteEl.textContent = DAILY_QUOTES[Math.floor(Math.random() * DAILY_QUOTES.length)];
  }

  // Chips
  const chipsEl = document.getElementById("kd-chips");
  if (chipsEl) {
    SUGGESTIONS.forEach(s => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "kd-chip";
      btn.textContent = `${s.icon} ${s.label}`;
      btn.addEventListener("click", () => {
        const ta = document.getElementById("kd-question");
        if (!ta) return;
        const cur = ta.value.trim();
        ta.value = cur ? `${cur} ${s.text}` : s.text;
        ta.focus();
        ta.setSelectionRange(ta.value.length, ta.value.length);
      });
      chipsEl.appendChild(btn);
    });
  }

  // Form submit
  const form = document.getElementById("kd-form");
  const ta = document.getElementById("kd-question");
  const submit = document.getElementById("kd-submit");
  const resultEl = document.getElementById("kd-result");

  if (!form || !ta || !submit || !resultEl) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = ta.value.trim();
    if (q.length < 5) {
      resultEl.replaceChildren();
      const err = document.createElement("div");
      err.className = "kd-error";
      err.textContent = "Câu hỏi cần từ 5 đến 500 ký tự.";
      resultEl.appendChild(err);
      return;
    }

    submit.disabled = true;
    resultEl.replaceChildren();
    await runDivination(q, resultEl);
    submit.disabled = false;
  });
}

async function runDivination(question, resultEl) {
  // ── Loading ──
  const loading = document.createElement("div");
  loading.className = "kd-loading";
  const bagua = document.createElement("div");
  bagua.className = "kd-bagua";
  bagua.appendChild(createBaguaSVG());
  const msg = document.createElement("div");
  msg.className = "kd-loading-msg";
  msg.textContent = LOADING_MESSAGES[0];
  const prog = document.createElement("div");
  prog.className = "kd-progress";
  loading.append(bagua, msg, prog);
  resultEl.appendChild(loading);

  let msgIdx = 0;
  const msgTimer = setInterval(() => {
    msgIdx = (msgIdx + 1) % LOADING_MESSAGES.length;
    msg.textContent = LOADING_MESSAGES[msgIdx];
  }, 2500);

  let castData = null;
  let coreData = null;
  let tamHopData = null;
  let actionData = null;
  let loadAnimDone = false;

  const cleanupLoading = () => {
    clearInterval(msgTimer);
    loading.remove();
  };

  // ── Layout kết quả ──
  const buildLayout = () => {
    cleanupLoading();

    resultEl.replaceChildren();

    // Grid 2 cột hexagram
    const grid = document.createElement("div");
    grid.className = "kd-result";

    const col1 = document.createElement("div");
    const col2 = document.createElement("div");
    if (castData) {
      renderHexagram(col1, castData.que_chinh, "Quẻ chủ");
      if (castData.que_bien) {
        renderHexagram(col2, castData.que_bien, "Quẻ biến");
      } else {
        col2.innerHTML = '<p class="kd-placeholder">Không có hào động — quẻ không biến.</p>';
      }
    }
    grid.append(col1, col2);
    resultEl.appendChild(grid);

    // Tabs
    const tabs = document.createElement("div");
    tabs.className = "kd-tabs";
    const tabDefs = [
      { id: "core", label: "📖 Quẻ từ" },
      { id: "tamhop", label: "🌏 Tam Hợp" },
      { id: "action", label: "📌 Hành động" },
    ];
    const panels = {};
    tabDefs.forEach((t, i) => {
      const tab = document.createElement("button");
      tab.className = "kd-tab" + (i === 0 ? " active" : "");
      tab.textContent = t.label;
      tab.dataset.tab = t.id;
      tabs.appendChild(tab);

      const panel = document.createElement("div");
      panel.className = "kd-panel";
      panel.dataset.panel = t.id;
      if (i !== 0) panel.style.display = "none";
      panels[t.id] = panel;
    });
    resultEl.appendChild(tabs);
    Object.values(panels).forEach(p => resultEl.appendChild(p));

    tabs.addEventListener("click", (e) => {
      const t = e.target.closest(".kd-tab");
      if (!t) return;
      tabs.querySelectorAll(".kd-tab").forEach(x => x.classList.toggle("active", x === t));
      const id = t.dataset.tab;
      Object.entries(panels).forEach(([k, p]) => {
        p.style.display = (k === id) ? "" : "none";
      });
    });

    return panels;
  };

  let panels = null;

  const ensureLayout = () => {
    if (!panels && castData) panels = buildLayout();
    return panels;
  };

  // ── Gọi API ──
  try {
    await streamDivination(question, {
      onCast(cast) {
        castData = cast;
        // Đợi animation đồng xu xong rồi mới build layout
        // (animation chạy trong loading area)
        const coinStage = document.createElement("div");
        loading.appendChild(coinStage);

        animateCoins(coinStage, cast.coins_log, () => {}).then(() => {
          // Không build ngay, đợi có ít nhất core data
          loadAnimDone = true;
          if (coreData) ensureLayout();
        });
      },

      onCore(core) {
        coreData = core;
        if (loadAnimDone) {
          const p = ensureLayout();
          if (p) renderCore(p.core, core);
        }
      },

      onTamHop(tamhop) {
        tamHopData = tamhop;
        const p = ensureLayout();
        if (p) renderTamHopPanel(p.tamhop, tamhop);
      },

      onAction(action) {
        actionData = action;
        const p = ensureLayout();
        if (p) renderAction(p.action, action);
      },

      onError(err) {
        cleanupLoading();
        const box = document.createElement("div");
        box.className = "kd-error";
        box.textContent = err.message || "Có lỗi xảy ra.";
        resultEl.appendChild(box);
      },

      onDone() {
        cleanupLoading();
        // Nếu vì lý do nào đó layout chưa build
        if (!panels && castData) ensureLayout();
        // Note chung
        const note = document.createElement("p");
        note.className = "kd-note";
        note.textContent = "Diễn giải mang tính tham khảo văn hóa — không phải lời khuyên chuyên môn.";
        resultEl.appendChild(note);
      },
    });
  } catch (err) {
    cleanupLoading();
    const box = document.createElement("div");
    box.className = "kd-error";
    box.textContent = err.message || "Không thể hoàn tất yêu cầu.";
    resultEl.appendChild(box);
  }
}

// ── Panel renderers ──

function renderCore(panel, d) {
  panel.replaceChildren();
  if (d.tong_quan) {
    const s = makeSection("📖 Tổng quan");
    renderParagraphs(s, d.tong_quan);
    panel.appendChild(s);
  }
  if (d.y_nghia_cot_loi) {
    const s = makeSection("💡 Ý nghĩa cốt lõi");
    renderParagraphs(s, d.y_nghia_cot_loi);
    panel.appendChild(s);
  }
  if (d.xu_huong_bien_hoa) {
    const s = makeSection("🔄 Xu hướng biến hóa");
    renderParagraphs(s, d.xu_huong_bien_hoa);
    panel.appendChild(s);
  }
  if (d.phan_tich_theo_cau_hoi) {
    const s = makeSection("🔍 Phân tích theo câu hỏi của bạn");
    renderParagraphs(s, d.phan_tich_theo_cau_hoi);
    panel.appendChild(s);
  }
  renderByField(panel, d.theo_linh_vuc);
}

function renderTamHopPanel(panel, d) {
  panel.replaceChildren();
  renderTamHop(panel, d);
}

function renderAction(panel, d) {
  panel.replaceChildren();
  if (d.goi_y_hanh_dong?.length) {
    const s = makeSection("📌 Hành động cụ thể");
    s.appendChild(makeList(d.goi_y_hanh_dong, "→"));
    panel.appendChild(s);
  }
  if (d.diem_can_can_nhac?.length) {
    const s = makeSection("⚠️ Cần cân nhắc");
    s.appendChild(makeList(d.diem_can_can_nhac, "•"));
    panel.appendChild(s);
  }
  if (d.loi_khuyen_thoi_diem) {
    const s = makeSection("⏰ Lời khuyên thời điểm");
    renderParagraphs(s, d.loi_khuyen_thoi_diem);
    panel.appendChild(s);
  }
}
