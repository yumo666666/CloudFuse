<p align="center">
  <img src="image/CloudFuse.svg" alt="CloudFuse Logo" width="120"/>
</p>


| ![Demo](./imges/1.png) | ![Demo](./imges/2.png) |
| ![Demo](./imges/3.png) | ![Demo](./imges/4.png) |

# CloudFuse - 云函数管理系统

CloudFuse 是一个基于 FastAPI 的现代化云函数管理平台，支持函数的动态上传、管理、调用、依赖自动安装、调用统计、实时日志监控等功能，适合自建 Serverless/FAAS 场景。

---

## 主要特性

- 动态上传/创建/编辑/删除函数（支持 Web 界面和 API）
- 自动依赖管理：函数依赖自动检测与安装
- 函数调用统计：支持天/小时/总量统计
- 实时日志面板：只展示 logs/app.log，自动轮转，最多1000行
- 安全的沙箱式函数执行环境
- 支持多种文件管理操作（上传、下载、重命名、删除、目录树等）
- API 文档自动生成（/docs）
- 支持 Docker 部署
- 热重载开发体验

---

## 目录结构

```
.
├── admin/                # 后台管理前端模板与静态资源
│   ├── static/
│   └── templates/
├── apps/                 # 所有云函数目录
│   └── <function_name>/
│       ├── function.py
│       ├── config.json
│       ├── intro.md
│       ├── requirements.txt
│       └── ...
├── logs/                 # 日志目录，仅有 app.log
│   └── app.log
├── main.py               # FastAPI 启动入口
├── config.py             # 配置文件（含日志、路径、API等）
├── requirements.txt      # 依赖
└── README.md
```

---

## 快速开始

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **启动服务**
   ```bash
   python main.py
   ```

3. **访问管理后台**
   - Web 管理页面：http://localhost:8000/admin/
   - API 文档：http://localhost:8000/docs

---

## 函数管理

- 上传/创建函数：支持通过 Web 页面上传 zip/文件夹，或在线新建函数
- 函数目录要求：每个函数一个独立目录，需包含 function.py、config.json、intro.md
- 依赖自动安装：每次上传/保存函数时自动检测 requirements.txt 并安装新依赖
- 函数调用：通过 Web 或 API 直接调用，支持参数自动识别

---

## 日志系统

- 所有日志仅保存在 `logs/app.log`
- 自动轮转：只保留最新 1000 行，超出部分自动丢弃
- Web 日志面板：支持实时查看 logs/app.log 内容

---

## 文件管理

- 支持 apps 目录下的文件/文件夹上传、下载、重命名、删除、目录树浏览等操作

---

## 统计与监控

- 支持函数调用量的天/小时/总量统计
- 监控面板实时展示调用趋势、错误日志等

---

## Docker 部署

```bash
docker-compose up -d
```

---

## 常见问题

- 依赖安装失败：请检查 requirements.txt 是否正确，或手动 pip install
- 函数调用报错：请检查函数实现、参数类型、返回值格式
- 日志不显示：请确认 logs/app.log 是否有写入权限

---

## 贡献与许可

- 欢迎提交 PR 或 Issue
- 本项目采用 MIT 许可证
