/* nav.js — Sidebar dùng chung cho mọi trang Huyền Học AI */
(function () {
  "use strict";

  const NAV_ITEMS = [
    { group: "Chính", links: [
      { href: "/app",       icon: "🏠", label: "Tổng quan" },
      { href: "/dashboard", icon: "📊", label: "Dashboard" },
    ]},
    { group: "Bản mệnh", links: [
      { href: "/tu-vi",     icon: "🀄", label: "Tử Vi" },
      { href: "/hop-tuoi",  icon: "💕", label: "Hợp tuổi" },
      { href: "/so-sanh",   icon: "🔮", label: "Đông–Tây" },
    ]},
    { group: "Tâm linh", links: [
      { href: "/tarot",     icon: "🃏", label: "Tarot" },
      { href: "/kinh-dich", icon: "☯️", label: "Kinh Dịch" },
      { href: "/tam-linh",  icon: "🕉️", label: "Tâm linh" },
    ]},
    { group: "Công cụ", links: [
      { href: "/phong-thuy", icon: "🏠", label: "Phong thủy" },
      { href: "/su-kien",    icon: "📅", label: "Sự kiện" },
      { href: "/timeline-vi-mo", icon: "🌏", label: "Timeline" },
      { href: "/ban-do",     icon: "🗺️", label: "Bản đồ" },
      { href: "/gia-dao",    icon: "👨‍👩‍👧", label: "Gia đạo" },
      { href: "/kinh-te",    icon: "📊", label: "Kinh tế" },
      { href: "/trach-cat",  icon: "🏯", label: "Trạch cát" },
      { href: "/video",      icon: "🎥", label: "Video" },
    ]},
  ];

  const CSS = `
    :root {
      --sb-width: 240px;
      --sb-width-collapsed: 68px;
      --sb-bg: #1a0b2e;
      --sb-bg2: #241038;
      --sb-border: rgba(196,163,255,0.15);
      --sb-text: #b6a1d2;
      --sb-text-hover: #e8dff5;
      --sb-accent: #a78bfa;
      --sb-active-bg: rgba(124,58,237,0.25);
    }
    body { margin: 0; padding: 0 !important; transition: padding-left .2s; }
    body.has-sb { padding-left: var(--sb-width); }

    .sb {
      position: fixed; top: 0; left: 0; bottom: 0;
      width: var(--sb-width);
      background: var(--sb-bg);
      border-right: 1px solid var(--sb-border);
      display: flex; flex-direction: column;
      z-index: 1000;
      transition: width .2s, transform .25s;
      font-family: "Segoe UI", system-ui, sans-serif;
      font-size: 14px;
      color: var(--sb-text);
      overflow: hidden;
    }

    .sb-header {
      display: flex; align-items: center; gap: 10px;
      padding: 18px 16px 14px;
      border-bottom: 1px solid var(--sb-border);
      flex-shrink: 0;
    }
    .sb-logo {
      font-size: 22px; line-height: 1;
      flex-shrink: 0;
    }
    .sb-brand {
      font-weight: 700; color: #e8dff5; font-size: 15px;
      white-space: nowrap; overflow: hidden;
      transition: opacity .15s;
    }

    aside.sb .sb-nav {
      flex: 1; overflow-y: auto; overflow-x: hidden;
      padding: 10px 8px;
      scrollbar-width: thin;
      scrollbar-color: rgba(196,163,255,0.3) transparent;
    }
    aside.sb .sb-nav::-webkit-scrollbar { width: 6px; }
    aside.sb .sb-nav::-webkit-scrollbar-thumb { background: rgba(196,163,255,0.3); border-radius: 3px; }

    aside.sb .sb-group-label {
      display: block !important;
      padding: 14px 12px 6px !important;
      margin: 0 !important;
      font-size: 10px !important;
      font-weight: 700 !important;
      letter-spacing: 0.1em !important;
      text-transform: uppercase !important;
      color: rgba(182,161,210,0.55) !important;
      white-space: nowrap;
      overflow: hidden;
      transition: opacity .15s;
    }

    aside.sb .sb-link {
      display: flex !important;
      align-items: center !important;
      gap: 12px !important;
      padding: 9px 12px !important;
      margin: 2px 0 !important;
      border-radius: 8px !important;
      color: var(--sb-text) !important;
      text-decoration: none !important;
      white-space: nowrap;
      transition: background .12s, color .12s;
      font-size: 14px !important;
      font-weight: 400 !important;
      border: 0 !important;
      background: transparent !important;
    }
    aside.sb .sb-link:hover { background: rgba(255,255,255,0.05) !important; color: var(--sb-text-hover) !important; }
    aside.sb .sb-link.active { background: var(--sb-active-bg) !important; color: #fff !important; font-weight: 600 !important; }
    aside.sb .sb-link-icon { font-size: 18px !important; line-height: 1 !important; flex-shrink: 0 !important; width: 22px !important; text-align: center !important; display: inline-block !important; }
    aside.sb .sb-link-label { overflow: hidden; text-overflow: ellipsis; transition: opacity .15s; display: inline !important; }

    aside.sb .sb-footer {
      border-top: 1px solid var(--sb-border);
      padding: 10px 8px;
      flex-shrink: 0;
    }
    aside.sb .sb-footer .sb-link { font-size: 13px !important; }

    @media (max-width: 820px) {
      body.has-sb { padding-left: 0 !important; }
      .sb { transform: translateX(-100%); width: var(--sb-width) !important; }
      body.sb-open .sb { transform: translateX(0); }
      body.sb-open .sb-overlay { display: block; }
      .sb-hamburger { display: block; }
      .sb-toggle { display: none; }
      body.sb-collapsed .sb-link-label,
        }
  `;

  function injectStyle() {
    if (document.getElementById("sb-style")) return;
    const style = document.createElement("style");
    style.id = "sb-style";
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  function buildSidebar() {
    const currentPath = window.location.pathname;
    const groupsHtml = NAV_ITEMS.map(g => `
      <div class="sb-group-label">${g.group}</div>
      ${g.links.map(l => `
        <a class="sb-link ${l.href === currentPath ? "active" : ""}" href="${l.href}" title="${l.label}">
          <span class="sb-link-icon">${l.icon}</span>
          <span class="sb-link-label">${l.label}</span>
        </a>
      `).join("")}
    `).join("");

    const html = `
      <button class="sb-hamburger" id="sb-hamburger" aria-label="Mở menu">☰</button>
      <div class="sb-overlay" id="sb-overlay"></div>
      <aside class="sb" id="sb">
        <div class="sb-header">
          <span class="sb-logo">🔮</span>
          <span class="sb-brand">Huyền Học AI</span>
        </div>
        <nav class="sb-nav">${groupsHtml}</nav>
        <div class="sb-footer">
          <a class="sb-link" href="#" id="sb-logout" title="Đăng xuất">
            <span class="sb-link-icon">🚪</span>
            <span class="sb-link-label">Đăng xuất</span>
          </a>
        </div>
      </aside>
    `;
    document.body.insertAdjacentHTML("afterbegin", html);
  }

  function wireEvents() {
    const body = document.body;
    const hamburger = document.getElementById("sb-hamburger");
    const overlay = document.getElementById("sb-overlay");
    const logout = document.getElementById("sb-logout");

    hamburger?.addEventListener("click", () => body.classList.add("sb-open"));
    overlay?.addEventListener("click", () => body.classList.remove("sb-open"));

    logout?.addEventListener("click", (e) => {
      e.preventDefault();
      if (confirm("Đăng xuất?")) {
        localStorage.clear();
        window.location.replace("/");
      }
    });
  }

  function init() {
    document.body.classList.add("has-sb");
    injectStyle();
    buildSidebar();
    wireEvents();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
