# SYSU 抢课助手

把中山大学教务系统抢课/选课能力做成一个面向普通用户的独立桌面工具：

- 一键安装、开机自启
- 控制台点“用浏览器登录”，不再手工填 Cookie
- 一个搜索框支持课程号、课程名、教师姓名
- 搜索、加入目标、一键启动、定时启动、全部定时启动
- 实时显示已选课程、类别、学分和数量
- 黑名单检测与安全请求间隔
- Windows 系统托盘：右键可“打开控制台 / 退出”

**新手请先看：** [docs/新手教程.md](docs/新手教程.md)

## 快速开始

1. 双击 `install.bat`
2. 等待脚本完成，控制台会自动打开
3. 点击“登录设置”→“用浏览器登录”
4. 在 Edge 窗口登录一次教务系统
5. 搜索课程，加入抢课目标
6. 在“抢课目标”页面开始或定时启动

程序会驻留在系统托盘。右键托盘图标可随时打开控制台或退出。

控制台默认地址：

```text
http://127.0.0.1:8124
```

## 功能

- 课程搜索：课程号、课程名、教师姓名
- 加入抢课目标：一次加入、到点自动启动
- 抢课目标：开始、只试一次、停止、单独定时、全部定时
- 已选课程：读取已选上的课，显示类别和学分
- 登录：一键浏览器登录；扩展保留为备用方案
- 通知与日志：实时查看尝试次数、最近结果和运行记录

控制台默认地址：`http://127.0.0.1:8124`

## 开发运行

```powershell
python main.py --data-dir .\dev-data
```

Vuetify 控制台开发：

```powershell
cd frontend
npm install
npm run dev
```

生产构建：

```powershell
cd frontend
npm run build
```

构建产物会被复制/托管在 `webui/`，Python 服务直接读取该目录。

运行测试：

```powershell
python tests\run_tests.py
```

## 项目结构

```text
sysu-course-grabber/
├── sycu_grabber/       # 核心库
│   ├── api_client.py   # 教务选课接口封装
│   ├── store.py        # 本地 SQLite 数据与 Cookie 存储
│   ├── engine.py       # 预定、排队、抢课循环、超时和黑名单处理
│   └── server.py       # 本机 HTTP 服务与 API
├── webui/              # 浏览器控制台
├── extension/          # 自动同步 Cookie 的浏览器扩展
│   # 扩展不是必需项；控制台内置一键浏览器登录
├── scripts/            # 一键安装、卸载、后台启动脚本
├── main.py
└── install.bat
```

## 安全说明

- 服务默认只监听 `127.0.0.1`，不开放局域网
- 只有本机可以写入 Cookie
- Cookie 保存在当前用户的应用数据目录，而不是项目仓库里
- 教务系统对高频请求有检测，客户端把请求间隔下限锁在 1 秒

## CI / 发布

仓库包含 GitHub Actions：

- `.github/workflows/ci.yml`：推送或 PR 时运行 Python 测试并构建 Vuetify 前端
- `.github/workflows/release.yml`：打 `v*` 标签时生成可分发 zip 和 GitHub Release
