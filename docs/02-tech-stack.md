# 技术栈定版

**后端 Python 3.12 + FastAPI + SQLite（标准库 sqlite3），前端 Vue 3 + Vite 7 + Vue Router 4（JavaScript、原生 CSS），v0.1 本地双进程运行。**

| 项目 | 约定 |
| --- | --- |
| Python | 3.12；使用项目根目录 `.venv` 隔离依赖 |
| 后端依赖 | `backend/requirements.txt` 固定全部依赖版本；httpx 用于 TestClient 冒烟检查 |
| Node.js | 22.12+，推荐 22 LTS 或 24 LTS；`frontend/.nvmrc` 指向 22 |
| 前端依赖 | 保留 `package-lock.json`；组员使用 `npm ci` 安装 |
| 数据库 | 单文件 SQLite，无需安装数据库服务；不引入 ORM |
| 本地端口 | 后端 8000，前端 5173；默认仅监听 127.0.0.1 |
| 接口风格 | JSON + HTTP；业务接口统一 `/api` 前缀，健康检查为 `/health` |
| 模块结构 | 每人负责一组前端页面和一组后端路由；共享配置、数据库连接与布局 |
| 部署 | 当前只要求本地运行；单服务器部署另行安排，不在 v0.1 实施 |

## 环境变量

唯一示例位于根目录 `.env.example`，复制为根目录 `.env` 后由两端读取。修改配置后重启服务。

| 变量 | 默认示例 | 用途 |
| --- | --- | --- |
| `APP_NAME` | `Health Management System` | FastAPI 文档标题 |
| `BACKEND_HOST` | `127.0.0.1` | `python run.py` 监听地址 |
| `BACKEND_PORT` | `8000` | 后端端口；也是默认 Vite 代理目标端口 |
| `HEALTH_DB_PATH` | `backend/data/health.db` | SQLite 路径，相对路径始终相对项目根目录 |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 允许的浏览器来源，逗号分隔 |
| `FRONTEND_PORT` | `5173` | Vite 开发服务器端口；占用时直接报错 |
| `VITE_API_BASE_URL` | 留空 | 空值走本地代理；直连后端时填完整来源，如 `http://127.0.0.1:8000`，不加 `/api` |
| `API_PROXY_TARGET` | 留空 | 为空时代理到 `http://127.0.0.1:<BACKEND_PORT>`；需要时填完整后端来源 |

前端仅向浏览器暴露 `VITE_` 前缀变量，不能在此类变量中存放密钥。本项目本地运行无需任何密钥。

## 实现约定

- 数据层统一通过 `app.database.connect()` 建立连接，启用 SQLite 外键，每次使用后关闭。
- 数据库启动自动初始化，也可手动执行 `python scripts/init_db.py`；不自动生成档案或健康数据。
- `init.sql` 不是迁移工具，后续变更字段需单独提供迁移脚本。
- `run.py` 开启开发热重载，仅用于本地开发；v0.1 不包含生产部署配置。
- 前端使用 History 路由；以后部署需将未知页面路径回退到 `index.html`，并配置 API 转发。
- 当前没有登录鉴权，演示服务按单人本地工具运行；后续多人版本需另行设计账号与数据隔离。

## 官方参考

- [FastAPI 应用与自动接口文档](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [FastAPI 生命周期](https://fastapi.tiangolo.com/advanced/events/)
- [Vue 快速上手](https://vuejs.org/guide/quick-start)
- [Vite 环境要求与启动方式](https://vite.dev/guide/)
