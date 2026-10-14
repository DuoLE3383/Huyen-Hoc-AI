// Animation gieo 3 đồng xu — animate THEO coins_log từ backend

const TONG_LABEL = {
  6: "Lão Âm",
  7: "Thiếu Dương",
  8: "Thiếu Âm",
  9: "Lão Dương",
};

/** Tạo DOM 3 đồng xu trong 1 wrap */
function make3Coins(coins, landed) {
  const wrap = document.createElement("div");
  wrap.className = "kd-coins";
  coins.forEach(c => {
    const coin = document.createElement("div");
    coin.className = "kd-coin" + (landed ? " landed" : "");
    if (landed) {
      coin.style.transform = c ? "rotateY(0deg)" : "rotateY(180deg)";
    }
    const front = document.createElement("div");
    front.className = "face front";
    front.textContent = "乾元";
    const back = document.createElement("div");
    back.className = "face back";
    back.textContent = "坤順";
    coin.append(front, back);
    wrap.appendChild(coin);
  });
  return wrap;
}

/** Animate 6 hào theo coins_log, callback mỗi hào xong */
export async function animateCoins(container, coinsLog, onHaoDone) {
  container.innerHTML = "";
  const stage = document.createElement("div");
  stage.className = "kd-coin-stage";

  const status = document.createElement("div");
  status.className = "kd-coin-status";
  stage.appendChild(status);

  const holder = document.createElement("div");
  stage.appendChild(holder);

  container.appendChild(stage);

  for (let i = 0; i < coinsLog.length; i++) {
    const entry = coinsLog[i];
    // 1. Xoay
    holder.innerHTML = "";
    holder.appendChild(make3Coins(entry.coins, false));
    status.innerHTML = `Hào ${i + 1}/6 — đang gieo…`;

    await sleep(700);

    // 2. Dừng, lật kết quả
    holder.innerHTML = "";
    holder.appendChild(make3Coins(entry.coins, true));
    const label = entry.coins.map(c => c ? "Dương" : "Âm").join(" · ");
    const tongLabel = TONG_LABEL[entry.tong] || "?";
    status.innerHTML = `Hào ${i + 1}/6 — ${label} → <b>${tongLabel}</b>`;

    onHaoDone?.(i, entry);
    await sleep(350);
  }
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
