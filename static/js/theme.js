/* ==========================================================================
   深色模式 / 主题切换（2026-11-23 · 复现 DjangoBlog 第二批）
   --------------------------------------------------------------------------
   参考：frontend/src/features/darkMode.js（localStorage 键 dark-mode-enabled、
         data-theme 属性、跟随系统 prefers-color-scheme）
   约定：
     - 主题状态只认 <html data-theme="dark|light">，CSS 里两套变量都挂在它上面；
     - 内联在 base.html <head> 里的防闪烁脚本会先算一次并写 window.__THEME__，
       本文件接手交互（按钮、快捷键、跟随系统），判断逻辑与它保持一致；
     - 这是普通 Django static 脚本（不是打包构建），用 defer 加载、无任何依赖。
   ========================================================================== */

(function () {
  'use strict';

  var STORAGE_KEY = 'dark-mode-enabled';   // 与 base.html 内联脚本一致
  var root = document.documentElement;
  var toggleButton = document.getElementById('theme-toggle');

  // 浏览器界面颜色（手机地址栏等），与 style.css 的 --bg 对应
  var THEME_COLORS = { light: '#f7f4ee', dark: '#131715' };

  /* ---------- 读写偏好 ---------- */

  function systemPrefersDark() {
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  }

  /** 读用户手动选择；没选过返回 null（表示跟随系统）。 */
  function readSavedTheme() {
    try {
      var saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved === 'dark' || saved === 'light') return saved;
    } catch (e) {
      // 隐私模式 / 禁用 localStorage 时静默降级为跟随系统
    }
    return null;
  }

  function saveTheme(theme) {
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      // 存不了就算了，当前页面仍然生效
    }
  }

  /* ---------- 读取 / 应用主题 ---------- */

  /** 当前生效的主题：以 <html data-theme> 为准，没有属性时看系统。 */
  function getCurrentTheme() {
    var attr = root.getAttribute('data-theme');
    if (attr === 'dark' || attr === 'light') return attr;
    return systemPrefersDark() ? 'dark' : 'light';
  }

  function updateThemeColor(theme) {
    var meta = document.getElementById('theme-color');
    if (meta) meta.setAttribute('content', THEME_COLORS[theme]);
  }

  /** 同步按钮的无障碍状态和提示文案（图标显隐交给 CSS 按 data-theme 处理）。 */
  function updateToggleButton(theme) {
    if (!toggleButton) return;
    var isDark = theme === 'dark';
    var label = isDark ? '切换到浅色模式' : '切换到深色模式';
    toggleButton.setAttribute('aria-pressed', isDark ? 'true' : 'false');
    toggleButton.setAttribute('aria-label', label);
    toggleButton.setAttribute('title', label + '（Ctrl+Shift+D）');
  }

  function applyTheme(theme) {
    var next = theme === 'dark' ? 'dark' : 'light';
    // 显式 light 也写属性：这样能压过 CSS 里「跟随系统深色」的媒体查询
    root.setAttribute('data-theme', next);
    window.__THEME__ = next;
    updateThemeColor(next);
    updateToggleButton(next);
    document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: next } }));
    return next;
  }

  /** 设置主题；persist 为 false 时不写 localStorage（用于「跟随系统」自动切换）。 */
  function setTheme(theme, persist) {
    var next = applyTheme(theme);
    if (persist !== false) saveTheme(next);
    return next;
  }

  function toggleTheme() {
    return setTheme(getCurrentTheme() === 'dark' ? 'light' : 'dark', true);
  }

  /* ---------- 交互绑定 ---------- */

  function bindButton() {
    if (!toggleButton) return;
    toggleButton.addEventListener('click', function () {
      toggleTheme();
    });
  }

  /** Ctrl+Shift+D（Mac 上 Cmd+Shift+D）快速切换。 */
  function bindKeyboardShortcut() {
    document.addEventListener('keydown', function (event) {
      var isToggleKey = (event.ctrlKey || event.metaKey) && event.shiftKey &&
        (event.key === 'D' || event.key === 'd');
      if (!isToggleKey) return;
      event.preventDefault();
      toggleTheme();
    });
  }

  /** 用户没手动选过时，跟随系统深浅色变化；手动选过后以用户选择为准。 */
  function bindSystemThemeListener() {
    if (!window.matchMedia) return;
    var mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    function onChange(event) {
      if (readSavedTheme() === null) {
        applyTheme(event.matches ? 'dark' : 'light');   // 不写 localStorage
      }
    }

    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', onChange);
    } else if (typeof mediaQuery.addListener === 'function') {
      // 老浏览器兜底
      mediaQuery.addListener(onChange);
    }
  }

  /** 从 bfcache 回来时，按钮状态可能过期，重新同步一次。 */
  function bindPageShow() {
    window.addEventListener('pageshow', function () {
      updateToggleButton(getCurrentTheme());
      updateThemeColor(getCurrentTheme());
    });
  }

  /* ---------- 初始化 ---------- */

  // 正常情况下内联脚本已经写好 data-theme；这里再算一次，保证两者逻辑一致、
  // 也覆盖「有人单独引用 theme.js、漏了内联脚本」的情况。
  var initialTheme = root.getAttribute('data-theme') || readSavedTheme() ||
    (systemPrefersDark() ? 'dark' : 'light');
  applyTheme(initialTheme);
  bindButton();
  bindKeyboardShortcut();
  bindSystemThemeListener();
  bindPageShow();

  // 给控制台 / 以后别的脚本留一个稳定的入口
  window.DarkMode = {
    getCurrentTheme: getCurrentTheme,
    setTheme: function (theme) { return setTheme(theme, true); },
    toggle: toggleTheme
  };
})();
