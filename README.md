# 我的博客

> 技术组最终任务：用 **Django** 做一个自己的博客。
> 分 4 个阶段做，不一次做完——每阶段代码量可控，也方便讲清楚。

## 当前进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| **1** | 项目骨架 + 文章模型 + 后台 + 列表/详情页 | ✅ 2026-11-07 |
| 2 | 分类 + 搜索 + 分页 | ⬜ 下一步 |
| 3 | Markdown 渲染 + 样式打磨 | ⬜ |
| 4 | 部署上线 + 写 3 篇真实文章 | ⬜ |

## 环境

| 项 | 版本 |
|---|---|
| Python | 3.12.10 |
| Django | 5.2.18 LTS |
| 数据库 | SQLite |
| 依赖 | `requirements.txt`（Django + python-dotenv） |

> ⚠️ **不能用 Python 3.14**：Django 5.2 官方支持 3.10–3.13。
> 建虚拟环境时确认 `python --version` 是 3.12。

## 怎么跑

```powershell
cd D:\ai宝贝\12_我的博客\myblog

# 1 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 2 生成本地配置（第一次/换电脑必做，否则启动会报「缺少 DJANGO_SECRET_KEY」）
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(50))"
#   把输出的字符串填进 .env 的 DJANGO_SECRET_KEY=

# 3 建表
python manage.py migrate

# 4 造演示文章（可选）
python manage.py seed_posts

# 5 建后台账号（自己定用户名密码，仓库里不放密码）
python manage.py createsuperuser

# 6 启动
python manage.py runserver
```

浏览器打开 <http://127.0.0.1:8000/>。

| 页面 | 地址 |
|---|---|
| 首页（文章列表） | <http://127.0.0.1:8000/> |
| 文章详情 | <http://127.0.0.1:8000/post/1/> |
| 后台（写文章） | <http://127.0.0.1:8000/admin/> |

停止服务器：终端里按 `Ctrl + C`。

## 项目结构

```text
myblog/
├── manage.py
├── requirements.txt
├── .env / .env.example     # 密钥配置（.env 不进 Git）
├── db.sqlite3              # 数据库（本地生成，不进 Git）
├── config/                 # 项目配置包
│   ├── settings.py         # 全局配置：应用、数据库、时区、静态文件
│   └── urls.py             # 总路由：/admin/ 和 /（交给 blog）
├── blog/                   # 博客应用
│   ├── models.py           # Post 模型（标题/正文/是否发布/时间）
│   ├── admin.py            # 后台配置
│   ├── views.py            # 列表、详情
│   ├── urls.py             # 2 条路由
│   ├── tests.py            # 6 个测试
│   ├── migrations/         # 建表脚本（自动生成，不要手改）
│   └── management/commands/seed_posts.py   # 造演示文章
├── templates/
│   ├── base.html           # 全站外壳（顶栏 + 页脚）
│   └── blog/
│       ├── post_list.html  # 列表页
│       └── post_detail.html# 详情页
└── static/css/style.css    # 全站样式（约 200 行，无框架）
```

## 这一版实现了什么

- **文章模型**：标题、正文、是否发布、创建/更新时间
- **后台写文章**：`/admin/` 里增删改查，不用自己写编辑页面
- **列表页**：只显示已发布文章，按时间倒序，每条带摘要
- **详情页**：正文按段落显示；草稿直接 404，改 URL 也看不到
- **6 个自动化测试**：只显示已发布、倒序、详情 200、草稿 404、不存在 404

## 用到的 Django 知识点

| 知识点 | 在哪 |
|---|---|
| 项目 vs 应用 | `config/` vs `blog/` |
| 模型与字段 | `blog/models.py` |
| `Meta.ordering` | 列表默认按时间倒序，视图里不用写 `order_by` |
| `@property` | `Post.summary` 生成摘要 |
| 数据库迁移 | `makemigrations` → `migrate` |
| 后台注册与配置 | `blog/admin.py`（list_display / list_filter / search_fields） |
| 函数视图 FBV | `blog/views.py` |
| `get_object_or_404` | 详情页，同时防止看到草稿 |
| URL 命名空间 | `app_name = 'blog'`，模板里 `{% url 'blog:detail' %}` |
| 模板继承 | `base.html` + 两个子模板 |
| 过滤器 | `date`、`linebreaks` |
| 静态文件 | `static/css/style.css` |
| 测试 | `blog/tests.py` |
| 环境变量管理密钥 | `.env` + `python-dotenv` |

## 几个设计决定

**为什么正文先用纯文本，不做 Markdown？**
阶段 1 的目标是「能发文章、能看文章」。Markdown 渲染要引第三方库、
要处理转义和 XSS，留到阶段 3 单独做，一次只加一个变量。

**为什么详情页要把 `is_published=True` 写进查询？**
只按 id 查的话，别人改 URL 里的数字就能看到你的草稿。
写进查询条件 = 草稿天然 404，不用额外写权限判断。

**为什么用函数视图（FBV）不用类视图（CBV）？**
初学阶段 FBV 直白、每条逻辑看得见。等阶段 2 加搜索分页时，
如果发现重复代码多，再换 CBV 对比——那时换才有感觉。

**为什么样式自己写不用 Bootstrap？**
国内 CDN 不稳，且 200 行 CSS 已经够用。自己写还能真学 CSS。

## 下一步（阶段 2）

- 给 `Post` 加 `category` 字段（外键）→ 走一遍「改模型 → 迁移」
- 首页加分类筛选
- 加标题搜索（`Q` 查询）
- 列表分页（`Paginator`）

## 换台电脑怎么复现

```powershell
git clone <仓库地址>
cd myblog
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env    # 按注释填密钥
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
