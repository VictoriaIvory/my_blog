# 我的博客

> 技术组最终任务：用 **Django** 做一个自己的博客。
> 分 4 个阶段做，不一次做完——每阶段代码量可控，也方便讲清楚。

## 当前进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| **1** | 项目骨架 + 文章模型 + 后台 + 列表/详情页 | ✅ 2026-11-07 |
| **2** | 分类 + 搜索 + 分页 | ✅ 2026-11-15 |
| 3 | Markdown 渲染 + 样式打磨 | ⬜ 下一步 |
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

# 4 造演示数据（可选）：3 个分类 + 1 篇演示文章
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
| 分类筛选 | <http://127.0.0.1:8000/?category=Django> |
| 关键词搜索 | <http://127.0.0.1:8000/?q=饼图> |
| 分页 | <http://127.0.0.1:8000/?page=2> |
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
│   ├── models.py           # Category 分类 + Post 文章（带外键）
│   ├── admin.py            # 后台配置（两个模型）
│   ├── views.py            # 列表（筛选/搜索/分页）、详情
│   ├── urls.py             # 2 条路由
│   ├── tests.py            # 22 个测试
│   ├── migrations/         # 建表脚本（自动生成，不要手改）
│   └── management/commands/seed_posts.py   # 造演示分类和文章
├── templates/
│   ├── base.html           # 全站外壳（顶栏 + 页脚）
│   └── blog/
│       ├── post_list.html  # 列表页（搜索框 + 分类导航 + 分页）
│       └── post_detail.html# 详情页
└── static/css/style.css    # 全站样式（约 330 行，无框架）
```

## 这一版实现了什么

**阶段 1（2026-11-07）**

- **文章模型**：标题、正文、是否发布、创建/更新时间
- **后台写文章**：`/admin/` 里增删改查，不用自己写编辑页面
- **列表页**：只显示已发布文章，按时间倒序，每条带摘要
- **详情页**：正文按段落显示；草稿直接 404，改 URL 也看不到
- **6 个自动化测试**：只显示已发布、倒序、详情 200、草稿 404、不存在 404

**阶段 2（2026-11-15）**

- **分类**：`Category` 模型 + `Post.category` 外键；后台可建分类、文章选分类
- **分类筛选**：`/?category=Django`，分类导航在首页顶部
- **搜索**：`/?q=关键词`，标题和正文都搜，不区分大小写
- **分页**：`/?page=2`，每页 5 篇；翻页时保留搜索词和分类
- **测试从 6 个加到 22 个**：分类、搜索、分页各有用例，草稿在任何筛选下都不漏

## 用到的 Django 知识点

| 知识点 | 在哪 |
|---|---|
| 项目 vs 应用 | `config/` vs `blog/` |
| 模型与字段 | `blog/models.py` |
| 外键 `ForeignKey` + `on_delete=SET_NULL` | `Post.category`：分类删了文章还在 |
| `related_name` | `category.posts` 反查这个分类下的文章 |
| `Meta.ordering` | 列表默认按时间倒序，视图里不用写 `order_by` |
| `@property` | `Post.summary` 生成摘要 |
| 数据库迁移 | `makemigrations` → `migrate`（阶段 2 又走了一遍） |
| 后台注册与配置 | `blog/admin.py`（list_display / list_filter / search_fields） |
| 函数视图 FBV | `blog/views.py` |
| `get_object_or_404` | 详情页，同时防止看到草稿 |
| 查询参数 `request.GET` | 分类、搜索、页码都从 URL 参数取 |
| `Q` 查询对象 | 搜索「标题或正文」：`Q(title__icontains=…) \| Q(body__icontains=…)` |
| `icontains` | 不区分大小写的模糊匹配 |
| `select_related` | 列表页一次查出分类，避免每篇都查数据库 |
| `Paginator` + `get_page` | 分页，非法页码自动兜底 |
| URL 命名空间 | `app_name = 'blog'`，模板里 `{% url 'blog:detail' %}` |
| 模板继承 | `base.html` + 两个子模板 |
| 过滤器 | `date`、`linebreaks`、`urlencode` |
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
（阶段 2 做完发现逻辑还是线性的，没到非换不可的程度，所以继续用 FBV。）

**为什么样式自己写不用 Bootstrap？**
国内 CDN 不稳，且 200 行 CSS 已经够用。自己写还能真学 CSS。

**阶段 2：分类为什么不用 slug？**
文章没有 slug 是因为中文标题转 slug 难看（见建站档案）。分类同理：
直接按名字筛（`?category=Django`），中文分类名由 Django 自动 urlencode，
URL 里不会出现拼音。代价是分类改名会断开旧链接——个人博客无所谓。

**阶段 2：搜索为什么搜正文而不只搜标题？**
`icontains` 对 SQLite 是小写化后的 LIKE，正文搜索成本很低；
只搜标题经常明明记得内容却搜不到。搜索词为空（或只有空格）时等于没搜。

**阶段 2：为什么分页用 `get_page`？**
`paginator.page()` 遇到非法页码会抛异常、返回 500；
`get_page()` 自动兜底：非数字 → 第一页，超出范围 → 最后一页。
另外「翻页链接」要把当前搜索词和分类带过去，所以视图里先把 `page`
参数摘掉、剩下参数重新编码成 `querystring` 交给模板。

## 下一步（阶段 3）

- Markdown 渲染：引 `markdownify` 或 `python-markdown`，写文章能用代码块
- 样式打磨：文章正文的代码块、引用、图片
- 测试继续守着：Markdown 渲染不能带出 XSS（渲染后要转义/清洗）

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
