# 排障

- 脚本需要 Node.js 和 Playwright。先检查可用的已安装模块；也可在技能目录执行 `npm install --no-save --no-package-lock playwright`，再执行 `npx playwright install chromium`。安装依赖或浏览器前遵守当前环境与用户要求；不要假定网络可用。脚本也支持 `AXURE_PLAYWRIGHT_PATH` 指向 Playwright 包目录或入口文件。
- 脚本使用 DOM 加载而非等待网络空闲，持续网络连接不应导致必然超时。增加等待时间可使用 `--wait-ms 10000`。截图和文字仍可能缺少延迟加载或被遮挡的内容，应核对。
- Axure 播放器常用 iframe，先检查页面列表和每个 frame 的 URL、标题、文字；播放器提示可遮挡页面。脚本只尝试关闭名为“知道了”的提示，不处理登录或其他业务弹窗。
- URL 参数必须作为一个完整的 shell 参数传入，尤其是 `&`、`#` 和空格。PowerShell 中将整个 URL 用单引号包住。
- 遇到登录或权限拒绝，应请用户在合适的浏览器完成登录，或使用当前环境提供的已授权浏览器能力；不绕过权限。脚本的独立浏览器不会自动继承用户浏览器登录状态。
- 截图是页面当前可见状态，动态面板、滚动区、交互与条件内容不一定完整。需要时使用浏览器逐项验证，无法验证则标注。
- Windows Node ESM 导入本地绝对路径应转成 file URL；本脚本使用 require 解析，避免直接 import Windows 路径。