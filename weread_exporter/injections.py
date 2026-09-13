"""注入浏览器的 JS 片段（常量）。

这些字符串会被 evaluate 到微信读书页面里做检测或反自动化补丁，
集中放在本模块，避免 webpage.py 里塞大段内联 JS。
（不用 scripts.py 命名——那是放 shell 脚本的目录名，这里是 JS 注入片段。）
"""

DETECT_HEADLESS_SCRIPT = """
const webdriver = navigator.webdriver === true;
const chromeObj = typeof window.chrome !== "undefined";
const pluginCount = navigator.plugins.length;
const languageCount = navigator.languages ? navigator.languages.length : 0;
const headlessUA = /HeadlessChrome/.test(navigator.userAgent);
const zeroOuterSize = (window.outerWidth === 0 && window.outerHeight === 0);
webdriver || !chromeObj || pluginCount === 0 || languageCount === 0  || headlessUA || zeroOuterSize;
"""

# 只在可见 DOM 上判定的验证码信号。必须量到宽高都大于 0，
# 否则会命中打包 JS 源码里 incidental 的 captcha 字样，那是误报的根因。
DETECT_CAPTCHA_SCRIPT = """
() => {
  const sels = [
    'iframe[src*="captcha"]',
    '[id*="captcha" i]',
    '[class*="captcha" i]',
    '[id*="verify" i]',
    '[class*="verify" i]',
    '[class*="secsdk"]',
  ];
  return sels.some(s => {
    let el;
    try { el = document.querySelector(s); } catch (e) { return false; }
    if (!el) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  });
}
"""

# stealth 反自动化补丁：抹掉 navigator.webdriver 等自动化痕迹。
# 原项目从 headless 时代继承，真实浏览器没有这些痕迹所以实际不触发。
STEALTH_PATCH_SCRIPT = """
() => {
    if (navigator.webdriver) {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => {
                console.log('navigator.webdriver is called');
                console.log(new Error().stack);
                return undefined;
            }
        });
        var _hasOwnProperty = Object.prototype.hasOwnProperty;
        Object.prototype.hasOwnProperty = function (key) {
            if (key === 'webdriver') {
                console.log('hasOwnProperty', key, 'is called');
                console.log(new Error().stack);
                return false;
            }
            return _hasOwnProperty.call(this, key);
        };
        const originalQuery = navigator.permissions.query;
        navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );
    }
    if (navigator.plugins.length === 0) {
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        Object.defineProperty(window, 'PluginArray', {
            get: () => Array,
        });
    }
    if (navigator.languages.length === 0) {
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
    }
    window.chrome = window.chrome || {
        runtime: {},
    };
}
"""
