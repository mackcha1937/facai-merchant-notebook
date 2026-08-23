# 05 · 安全与可访问性报告

## 安全基线

- 所有响应：`X-Content-Type-Options=nosniff`、`X-Frame-Options=DENY`、`Referrer-Policy=no-referrer`；
- Permissions-Policy：关闭camera/geolocation，只允许self microphone；
- API响应：`Cache-Control=no-store`；
- SPA：限制default/base/frame/object/form/image/style/script/connect来源的CSP；
- HTTPS请求才返回一年HSTS，避免本地HTTP被错误锁定；
- 生产身份关闭时缺上下文fail-closed；
- 状态接口不返回Key、完整提示词、配置正文或数据库异常正文；
- 真实 `.env`、数据库和备份继续被Git忽略。

## 可访问性基线

- 360～430px手机与桌面无横向溢出；
- 店主应用、阶段7管理页和阶段8验收页的可见主要交互目标最小44px；
- 应用工作台补全语义h1，阶段8页面使用单一h1和分区h2；
- 加载状态提供 `aria-busy`，错误提供 `role=alert`；
- 今日事项红点同时保留“新”文本/aria语义（历史回归）；
- 键盘Tab可进入主要链接和操作控件，显式 `:focus-visible` 轮廓可见。

限制：未完成第三方WCAG扫描、屏幕阅读器人工测试和正式品牌色全量对比度审计。
