# 我的博客

> 技术组最终任务：用 **Django** 做一个自己的博客。
> 分阶段做，不一次做完——每阶段代码量可控，也方便讲清楚。

## 当前进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| **1** | 项目骨架 + 文章模型 + 后台 + 列表/详情页 | ✅ 2026-11-07 |
| **2** | 分类 + 搜索 + 分页 | ✅ 2026-11-15 |
| **3** | Markdown 渲染 + 代码高亮 + 样式打磨 | ✅ 2026-11-16 |
| 4 | 部署上线 | — **不做**（本地项目，无云端需求；部署手册留档备用） |
| **5** | 按 GitHub 参考项目 DjangoBlog 复现功能（第一批） | ✅ 2026-11-23（评论/登录/页面/侧边栏/站点设置） |
| **6** | 复现 DjangoBlog 第二批：草稿+定时发布、深色模式 | ✅ 2026-11-23 |

## 文章（3 篇）

1. 《我做投票demo时遇到的各种drama问题》—— 饼图 SVG 踩坑（2026-11-09）
2. 《给博客加分类、搜索和分页，三个我以为半小时能搞定的东西》（2026-11-16）
3. 《让室友用手机给我的投票 demo 投票：ALLOWED_HOSTS 那点事》（2026-11-16）

## 已经能做什么（v1.4，2026-11-23）

| 功能 | 说明 |
|---|---|
| 写文章 | 后台写 Markdown：标题、列表、表格、代码块、图片；可传封面图 |
| 分类 / 标签 | 分类是栏目（一个），标签是关键词（多个）；都能筛选 |
| 搜索 | 标题 + 正文，不区分大小写，和分类/标签可叠加 |
| 分页 / 归档 | 每页 5 篇；归档页按年月分组 |
| 阅读量 | 详情页每次阅读 +1，列表和详情都显示 |
| 相关文章 | 详情页底部按标签、再按分类推荐 |
| **登录 / 注册** | 注册、登录、退出、个人中心（看我发过的评论） |
| **评论** | 登录后评论；支持嵌套回复、审核、关闭评论；后台批量通过 |
| **独立页面** | 后台把文章勾成「页面」，走 `/page/<id>/`，不进列表/搜索/归档（如留言板） |
| **侧边栏** | 最新文章 / 最多阅读 / 标签云 / 最新评论 / 页面入口 |
| **站点设置** | 后台改站名、描述、页脚、备案号、统计代码、评论审核开关、侧边栏数量 |
| **草稿 / 定时发布** | 后台存草稿，或把「发布时间」填到将来；没发布/没到点的文章在列表、搜索、RSS、sitemap、侧边栏、评论里都不出现，详情直接 404，到点自动出现 |
| **深色模式** | 顶栏一键切换（日/月图标）或跟随系统；localStorage 记住选择，`?theme=dark\|light` 可固定；深色下代码高亮单独配色 |
| 订阅 / 收录 | RSS 订阅 `/feed/`、站点地图 `/sitemap.xml` |
| 关于页 | 介绍博客、技术栈、现状 |

## 环境

| 项 | 版本 |
|---|---|
| Python | 3.12.10 |
| Django | 5.2.18 LTS |
| 数据库 | SQLite |
| 依赖 | `requirements.txt`（Django + python-dotenv + Markdown + bleach + Pygments + Pillow + WhiteNoise） |

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

# 4 造演示数据（可选）：3 个分类、3 个标签 + 1 篇演示文章
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
| 标签筛选 | <http://127.0.0.1:8000/?tag=Django> |
| 关键词搜索 | <http://127.0.0.1:8000/?q=饼图> |
| 分页 | <http://127.0.0.1:8000/?page=2> |
| 文章详情 | <http://127.0.0.1:8000/post/1/> |
| 归档 | <http://127.0.0.1:8000/archive/> |
| 关于 | <http://127.0.0.1:8000/about/> |
| RSS 订阅 | <http://127.0.0.1:8000/feed/> |
| 站点地图 | <http://127.0.0.1:8000/sitemap.xml> |
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
│   ├── models.py           # Category 分类 + Tag 标签 + Post 文章 + BlogSettings 站点设置
│   ├── markdown_render.py  # Markdown → HTML + 白名单清洗（阶段 3）
│   ├── admin.py            # 后台配置（四个模型、封面预览、评论审核入口）
│   ├── views.py            # 列表/详情/页面/归档/关于/robots
│   ├── feeds.py            # RSS 订阅源 /feed/
│   ├── sitemap.py          # 站点地图 /sitemap.xml
│   ├── context_processors.py   # 站点设置 + 导航页面（全站模板可用）
│   ├── templatetags/blog_extras.py  # 侧边栏 inclusion tag
│   ├── urls.py             # 8 条路由
│   ├── tests.py            # 106 个测试（草稿/定时发布等）
│   ├── tests_theme.py      # 15 个深色模式测试（第二批）
│   ├── migrations/         # 建表脚本（自动生成，不要手改；已到 0005）
│   └── management/commands/
│       ├── seed_posts.py   # 造演示分类/标签/文章/页面
│       └── backup.py       # 备份数据库 + media/ 到 backups/
├── comments/               # 评论应用（嵌套回复、审核、后台批量通过）
│   ├── models.py           # Comment（自关联 parent）
│   ├── views.py            # 发表评论（登录 + POST）
│   ├── utils.py            # 可见评论 + 组装评论树
│   └── admin.py            # 审核 / 批量通过
├── accounts/               # 账号应用（登录/注册/退出/个人中心）
├── templates/
│   ├── base.html           # 全站外壳（顶栏 + 页脚 + SEO + 登录状态 + 深色模式）
│   ├── 404.html            # 404 页面（带搜索框）
│   ├── blog/
│   │   ├── post_list.html  # 列表页（头图 + 搜索 + 分类/标签 + 卡片 + 分页）
│   │   ├── post_detail.html# 详情页（封面 + 目录 + 正文 + 上下篇 + 相关 + 评论）
│   │   ├── page_detail.html# 独立页面（如留言板，也可评论）
│   │   ├── _sidebar.html   # 侧边栏
│   │   ├── archive.html    # 归档页（按年月分组）
│   │   └── about.html      # 关于页
│   ├── comments/           # _section.html + _comment.html（递归渲染回复）
│   └── accounts/           # login / register / profile
├── static/
│   ├── favicon.svg         # 站点图标
│   ├── js/
│   │   └── theme.js        # 深色模式切换（第二批，无依赖）
│   └── css/
│       ├── style.css       # 全站样式（约 1550 行，CSS 变量 + 响应式 + 深色模式，无框架）
│       └── pygments.css    # 代码高亮配色（Pygments 生成，勿手改）
├── media/                  # 用户上传的封面图（不进 Git，见 .gitignore）
├── docs/04_部署手册.md     # PythonAnywhere 部署步骤 + 排查清单
└── .github/workflows/tests.yml  # GitHub Actions：每次 push 自动跑测试
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

**阶段 3（2026-11-16）**

- **Markdown 渲染**：正文用 Markdown 写，支持标题、列表、表格、引用、链接、图片
- **代码高亮**：` ```python ` 围栏代码块由 Pygments 上色，配色表由程序生成
- **安全清洗**：渲染后过一遍 `bleach` 白名单，正文里混进 `<script>` 也不会执行
- **摘要不露记号**：列表页摘要基于渲染后的纯文本生成，不会出现 `**`、`` ` ``、`](`
- **细节补完**：分页条显示页码（页数多时用省略号）、404 页面、GitHub Actions 自动跑测试
- **测试从 22 个加到 33 个**：Markdown 渲染、XSS 清洗、页码、404 页面各有用例

**视觉改版（2026-11-16，组长反馈"不太美观"之后）**

- **整体风格**：暖纸色底 + 深绿主色 + 卡片式布局，全部手写 CSS（不引框架/CDN）
- **首页**：加了头图（一句话介绍 + 文章数/分类数/最近更新）、卡片式文章列表（hover 浮起）
- **详情页**：文章头部信息（分类 / 日期 / 阅读时间）、自动生成的「本文目录」、
  上一篇/下一篇卡片、更宽松的正文排版（h2 左侧色条、引用、表格、代码块）
- **细节**：网站图标样式的品牌标识、页脚、404 页、手机端断点适配
- **配套**：`Post.reading_time` 阅读时间估算；Markdown 标题生成中文锚点（目录跳转用）
- **测试从 33 个加到 37 个**：头图只出现在首页、目录生成、阅读时间、上下篇链接

**功能扩展（2026-11-16，解决"只能写文字"）**

- **封面图**：`Post.cover` 图片字段（需 Pillow），后台可传，列表卡片和详情页都显示
- **标签**：`Tag` 模型 + 多对多；`/?tag=Django` 筛选；卡片/详情显示；后台可管理
- **阅读量**：`Post.views`，详情页每次阅读 +1（数据库 `F` 表达式自增）
- **相关文章**：详情页底部先按共同标签、再按同分类推荐 3 篇
- **归档页**：`/archive/` 按年月分组
- **关于页**：`/about/` 介绍博客、技术栈、现状
- **RSS / 站点地图**：`/feed/` 用 Django syndication，`/sitemap.xml` 手写 XML
- **测试从 37 个加到 51 个**：标签、封面、阅读量、相关、归档、关于、RSS、sitemap

**复现参考项目 DjangoBlog（2026-11-23，第一批）**

背景：GitHub 上参考了 [liangliangyy/DjangoBlog](https://github.com/liangliangyy/DjangoBlog)
（Django 5.2 + MySQL/Redis + Tailwind/Alpine/HTMX + Whoosh 的完整博客系统），
按「功能对齐、不照搬技术栈」的方式复现了最核心的五个差距：

- **评论系统**（`comments/`）：登录后评论、嵌套回复、审核开关、关闭评论、后台批量通过
- **账号系统**（`accounts/`）：注册、登录、退出、个人中心（看我的评论）
- **独立页面**：`Post.is_page`，走 `/page/<id>/`，不进列表/搜索/归档/相关（留言板已建）
- **侧边栏**：最新文章 / 最多阅读 / 标签云 / 最新评论 / 页面入口（两栏布局，窄屏隐藏）
- **站点设置**：`BlogSettings` 单例，后台可改站名、描述、页脚、备案号、统计代码、评论审核、侧边栏数量
- **测试从 59 个加到 84 个**：评论权限/审核/回复/关闭、注册登录退出、页面、侧边栏、站点设置

> 没照搬的：MySQL / Redis / Elasticsearch / Tailwind+Vite / OAuth / Docker（参考项目是线上系统，
> 这些和「本地项目」的定位冲突）。

**复现参考项目 DjangoBlog（2026-11-23，第二批）**

第一批补的是「缺的应用」，第二批补「写文章 / 读文章时的体验」：

- **草稿 + 定时发布**：`Post.status`（draft/published）替代 `is_published`，新增 `pub_time`；
  统一 `Post.objects.visible()` 判定（已发布且发布时间已到），所有前台入口共用——
  草稿和没到点的文章在列表 / 搜索 / 归档 / RSS / sitemap / 侧边栏里都不出现，详情直接 404；
  到点自动出现，**不需要定时任务**。顺便修了首页统计把独立页面算成文章的老 bug（4 → 3）。
- **深色模式**：`[data-theme="dark"]` + `prefers-color-scheme` 两套触发；顶栏切换按钮
  （日/月图标、aria 状态）；localStorage 记住选择，`?theme=dark|light` 可固定主题；
  Pygments 代码高亮单独配深色 token；防闪烁脚本先于样式表执行（不会闪一下白）。
- **测试从 84 个加到 121 个**（`blog/tests.py` 106 + `blog/tests_theme.py` 15）：
  草稿/定时在列表、搜索、分类、标签、归档、相关、侧边栏、RSS、sitemap、详情、独立页面、
  评论、计数、上下篇、admin 的可见性；深色模式的模板 / 无障碍属性 / 静态资源断言。

> 第二批还剩的候选：Whoosh 全文搜索 + 高亮、友链页 + 作者页、简化插件机制。

**部署加固 + 性能优化（2026-11-23）**

> 背景：一度打算部署到云端，顺手把生产配置也做了；后来确定**按本地项目交付、不上线**。
> 这些改动本地也用得上（DEBUG 默认值、日志、备份、性能、SEO、可访问性），
> 只有 WhiteNoise / HTTPS 开关 / collectstatic 是部署专用的，`DEBUG=True` 时不影响本地。

- **安全默认值**：`DEBUG` 默认改成 `False`（忘配 `.env` 也不会带调试页上线）
- **HTTPS 开关**：`.env` 里 `DJANGO_HTTPS=True` 自动开启 HTTPS 跳转、安全 Cookie、
  HSTS、反向代理头识别（PythonAnywhere 这类平台必需）
- **静态文件**：加 WhiteNoise，生产环境直接从 `staticfiles/` 返回 CSS；
  `collectstatic` 已实测（130 个文件）
- **日志**：配置 `LOGGING`，线上出错能在平台 Error log 里看到 traceback
- **备份**：新增 `python manage.py backup`，把数据库 + 封面图复制到 `backups/时间戳/`
- **性能**：`body_html` / `summary` / `word_count` 改用 `cached_property`；
  摘要和字数不再渲染 Markdown；列表和详情加 `prefetch_related('tags')`。
  实测：首页 SQL 15 → 8 条、详情页 11 → 8 条，渲染时间减半左右
- **封面图自动压缩**：上传超过 1600px 宽的图自动缩小（手机照片 5MB → 百 KB 级）
- **SEO / 分享**：favicon、`robots.txt`、RSS 自动发现、Open Graph / Twitter 卡片、canonical
- **可访问性**：灰色文字对比度 3.53:1 → 4.83:1（达到 WCAG AA）；键盘焦点框；404 页加搜索框
- **部署手册**：`docs/04_部署手册.md`（注册 → 上传代码 → 环境变量 → 静态/媒体映射 → 验收 → 排查）
- **测试从 51 个加到 59 个**：SEO 标签、robots、404 搜索、缓存、备份、封面压缩

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
| 过滤器 | `date`、`urlencode` |
| 静态文件 | `static/css/style.css`、`pygments.css` |
| Markdown 渲染 | `blog/markdown_render.py`（`render_markdown`） |
| HTML 安全清洗 | `bleach.clean` 白名单（标签 / 属性 / 协议） |
| 代码高亮 | Pygments（`codehilite` 扩展 + 自动生成配色表） |
| `mark_safe` | 清洗后的 HTML 标记为安全，模板里 `|safe` 输出 |
| 404 自定义页 | `templates/404.html`，`DEBUG=False` 时自动使用 |
| 模板里的页码循环 | `page_numbers`（视图算好，模板只负责渲染） |
| 阅读时间估算 | `Post.reading_time`（有效字符数 ÷ 400，至少 1 分钟） |
| 目录锚点 | Markdown `toc` 扩展 + 自定义中文 slugify（默认会删掉中文） |
| 上一篇 / 下一篇 | 详情页按 pk 找相邻的已发布文章 |
| CSS 变量与响应式 | `style.css` 里 `:root` 定义配色/圆角/阴影，760px / 480px 两档断点 |
| 图片字段 `ImageField` + `MEDIA_ROOT` | `Post.cover`：上传、存储、模板里 `post.cover.url` |
| 多对多 `ManyToManyField` | `Post.tags`，一篇多标签，`tag.posts` 反查 |
| `F` 表达式 | 阅读量自增：`update(views=F('views') + 1)`，避免并发覆盖 |
| `aggregate(Sum(...))` | 首页「总阅读量」统计 |
| 多表筛选 `filter(tags=...)` | 标签筛选（多对多） |
| RSS syndication | `blog/feeds.py`（`django.contrib.syndication`） |
| 站点地图 | `blog/sitemap.py`（手写 XML，不引 sites 框架） |
| 归档分组 | 视图里按 `(年, 月)` 分组，模板只渲染 |
| `cached_property` | `body_html` / `summary` / `word_count` 同一实例只算一次 |
| `prefetch_related` | 列表/详情的标签一次批量查出，避免 N+1 |
| WhiteNoise | 生产环境直接返回静态文件（`MIDDLEWARE` 按 DEBUG 条件插入） |
| 安全配置 | `SECURE_SSL_REDIRECT` / `SECURE_PROXY_SSL_HEADER` / 安全 Cookie / HSTS，环境变量控制 |
| 生产检查 | `python manage.py check --deploy`（只剩 HSTS preload 一条有意保留的提示） |
| 封面压缩 | `Post.save()` 里用 Pillow 缩到 1600px 宽 |
| 备份命令 | `blog/management/commands/backup.py` |
| robots.txt | `blog/views.py` 的 `robots()`，指向 sitemap |
| SEO / 分享 | `base.html` 的 canonical / OG / Twitter / RSS 自动发现 |
| 登录 / 登出 | `django.contrib.auth`（`login()` / `logout()`，退出必须 POST） |
| 注册 | `UserCreationForm` 子类 + `login()` 自动登录 |
| 评论模型 | 自关联外键 `Comment.parent`（嵌套回复）、`related_name='replies'` |
| 评论审核 | `Comment.is_approved` + 站点设置开关 + 管理员自动通过 |
| 评论树 | 视图里组装嵌套 dict，模板 `_comment.html` 递归 include |
| 站点设置单例 | `BlogSettings.load()`（`get_or_create(pk=1)`）+ 上下文处理器 |
| 侧边栏 | 自定义 `inclusion_tag`（`{% sidebar %}`），内部查最新/最热/标签/评论 |
| 模板上下文处理器 | `blog.context_processors.blog_context`：`site`、`nav_pages` 全站可用 |
| 独立页面 | `Post.is_page` + 单独路由 `/page/<id>/` + 列表/搜索/归档全部排除 |
| 草稿 / 定时发布 | `Post.status` + `Post.pub_time`；自定义 Manager `PostQuerySet.visible()` 统一可见性 |
| 数据迁移 | `RunPython` 把旧 `is_published` 映射成 `status`，`pub_time` 用创建时间兜底 |
| 深色模式（CSS） | 第二套 CSS 变量 + `[data-theme="dark"]` + `@media (prefers-color-scheme: dark)` |
| 主题持久化 | `localStorage` 键 `dark-mode-enabled` + `<head>` 里防闪烁内联脚本 |
| 静态 JS | `static/js/theme.js`（普通 static 文件，`defer` 加载，无打包构建） |
| 测试 | `blog/tests.py`（106 个）+ `blog/tests_theme.py`（15 个，深色模式） |
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

**阶段 3：为什么 Markdown 渲染完还要用 bleach 清洗？**
Markdown 库默认允许 HTML 原样通过（方便写 `<br>`、`<img>`），这正是 XSS 的入口。
虽然现在只有管理员能写文章、风险低，但**渲染函数是唯一出口**，在这里兜一次底最省心：
标签、属性、协议全走白名单，`<script>`、`onerror=` 这类东西会被删掉。
测试里专门放了一条 `<script>` 和一条 `<img onerror>`，以后改渲染器也不会悄悄失守。

**阶段 3：为什么保留 `nl2br` 扩展？**
前两阶段正文是纯文本，靠 `|linebreaks` 把换行变段落；直接切 Markdown 会让老文章
的行间感丢失（Markdown 会把单个换行当空格）。`nl2br` 让单个换行也变 `<br>`，
旧文章看起来和以前一致，新文章写 Markdown 也不受影响。

**阶段 3：代码高亮的配色表为什么是生成的？**
Pygments 只负责输出 `<span class="k">` 这类 class，具体颜色要写在 CSS 里。
手抄几百行不现实，所以用 `HtmlFormatter().get_style_defs('.codehilite')` 生成一次
`static/css/pygments.css`，以后想换主题重跑一遍就行。文件头写了来源和生成方式。

**阶段 3：摘要为什么用渲染后的纯文本？**
直接截取正文的话，摘要里会混进 `**`、代码围栏标记、`[]()` 这些记号，列表页一眼假。
先渲染再 `strip_tags`，得到的是「读者真正看到的文字」，再截 80 字。

**视觉改版：为什么还是自己写 CSS？**
页面一共才 4 个模板，引 Bootstrap 只会带来一堆用不到的样式和中文排版水土不服。
这次把配色、圆角、阴影、字号全部提成 CSS 变量（`:root`），改风格只动一处；
断点只做两档（760px / 480px），够用且好维护。

**视觉改版：为什么目录的锚点要自己写 slugify？**
Python-Markdown 的 `toc` 扩展默认会删掉非 ASCII 字符，中文标题生成的 id 是
`slug`、`_1`、`_2` 这种，目录点了会跳到错误位置。自定义一个保留中文的 slugify，
「一、分类」的锚点就是「一-分类」，和标题一一对应。

**视觉改版：为什么加「阅读时间」和「上一篇/下一篇」？**
阅读时间是列表页和详情页都需要的轻量信息（字数 ÷ 400）；上一篇/下一篇让人读完后
能继续看，比只有「返回首页」自然。两者都不需要额外依赖，各加几行代码。

**功能扩展：为什么加封面图不加富文本编辑器？**
组长/读者反馈"只能写文字"，最直接缺的是**图片**。但引富文本编辑器（如 CKEditor）
会引入一大包前端资源，还容易和 Markdown 打架。所以只加一个可选的封面图：
列表卡片和详情页立刻有视觉重点，正文继续用 Markdown（图片本来就能写 `![]()`）。

**功能扩展：为什么标签已经有了分类还要加？**
分类是「这篇属于哪个栏目」，只能有一个；标签是「这篇提到了哪些关键词」，可以有多个，
而且能用来做相关文章推荐（同标签最优先）。两者不是替代关系。
筛选方式保持一致：`?category=` / `?tag=`。

**功能扩展：阅读量为什么用 `F` 表达式？**
`post.views += 1; post.save()` 在并发访问时会互相覆盖。改成
`Post.objects.filter(pk=...).update(views=F('views') + 1)`，
自增交给数据库，不会丢计数。代价是要 `refresh_from_db()` 才能拿到新值。

**功能扩展：RSS 和站点地图为什么不装第三方包？**
RSS 用 Django 自带的 `contrib.syndication`；sitemap 只有十几行 XML，
没必要为了它再装 `sites` 框架。少一个依赖，部署时少一个坑。

**功能扩展：封面图为什么不进 Git？**
`media/` 是「运行后上传的文件」，和 `static/`（代码带的资源）性质不同：
换台电脑/部署时应该单独备份或传到对象存储。所以 `.gitignore` 排除 `media/`，
README 的部署一节会写清楚怎么处理。

**部署加固：为什么把 DEBUG 默认值改成 False？**
`os.environ.get('DJANGO_DEBUG', 'True')` 看着方便，但部署时忘建 `.env` 就会带着
调试页上线——报错时源码、配置、SQL 全暴露。默认 False 是「安全失败」，
本地开发在 `.env` 里显式写 `True`，多打一行字换一个安全默认值。

**部署加固：为什么用 WhiteNoise 而不是全交给平台？**
PythonAnywhere 可以用 Static files 映射，但换到别的平台（Render/Fly/服务器）
就要重配。WhiteNoise 让应用自己带静态文件服务：装一个依赖、加一行中间件，
换平台不用改代码。媒体文件（封面图）仍然交给平台映射，因为上传目录会变。

**部署加固：为什么 HSTS preload 故意不开？**
`check --deploy` 会提示把 `SECURE_HSTS_PRELOAD` 设为 True，但免费二级域名
（`xxx.pythonanywhere.com`）不适合提交浏览器 preload 列表——一旦进了列表很难撤回。
HSTS 本身已开（1 小时），够用；这属于「知道警告在说什么，所以有意保留」。

**性能：为什么摘要不渲染 Markdown 了？**
列表页每张卡片都要摘要。之前是渲染完整 HTML 再 `strip_tags`，一页 5 篇就是
5 次 Markdown + bleach。改成只去 Markdown 记号的 `plain_text()`，结果一样
（不会露出 `**`、代码围栏），但快得多。正文仍然走完整渲染 + 清洗，安全不变。

**性能：为什么用 `cached_property`？**
详情页要拿 `body_html` 生成目录、再渲染正文，同一篇会算两次；相关文章卡片
还要算阅读时间。`cached_property` 让同一实例只算一次，页面请求里省掉重复渲染。

**部署：为什么写部署手册而不是记在聊天里？**
部署涉及「代码 + 数据库 + 上传文件 + 环境变量 + 平台映射」五样东西，
聊天记录会丢、平台界面会变。写成 `docs/04_部署手册.md`，照着做能复现，
换电脑/重装也能用。**后来确定这个项目不做云端部署，手册留作以后可选的参考。**

**复现参考项目：为什么只对齐功能、不照搬技术栈？**
DjangoBlog 是线上系统，用了 MySQL、Redis、Elasticsearch、Tailwind/Vite、Docker。
这些是「部署与规模」问题的解法，不是「个人本地博客」的问题。
照搬会先装一堆环境、跑不起来，学到的反而是运维而不是 Django。
所以按功能拆：评论、登录、页面、侧边栏、站点设置都在我们的技术栈里重写；
搜索先用 `icontains`，不做 Whoosh/ES；前端继续手写 CSS。

**复现参考项目：评论区为什么要审核开关？**
参考项目有 `comment_need_review`，这是很现实的需求：个人博客一旦被爬虫/广告盯上，
没有审核就是灾难。所以 `BlogSettings.comment_need_review` 默认开，
管理员/博主的评论自动通过（自己不用审自己），游客评论先在后台队列里躺着。

**复现参考项目：为什么独立页面用 `is_page` 而不新建 Page 模型？**
页面和文章 90% 的字段一样（标题、正文、封面、评论开关），差别只是「进不进列表」。
新建模型会复制一遍列表/详情/渲染/评论逻辑；加一个布尔字段 + 一条 `/page/<id>/` 路由，
复用全部现有代码，模板只多一个 `page_detail.html`。

**复现参考项目：站点设置为什么做成单例？**
站名、描述、备案号、统计代码这些全站只有一份。`BlogSettings.load()` 用
`get_or_create(pk=1)` 保证只有一行，后台也不允许新增第二行；
模板通过上下文处理器拿到 `site`，改站名不用改代码、不用重启。

**复现参考项目：为什么删掉 `is_published`、改成 `status` + `pub_time`？**
「是否发布」和「什么时候发布」是两个独立问题：草稿是永远不发布，定时文章是已决定发布、
但时间还没到。一个布尔字段表达不了后者，只能靠临时改 `created_at` 或者后台手点，容易乱。
拆成 choices + 时间字段后，可见性判定只有一句 `status=published and pub_time<=now`，
列表 / 搜索 / RSS / sitemap / 侧边栏 / 评论 POST 都复用它——漏掉任何一处，测试都能抓到。

**复现参考项目：为什么定时发布不用 celery / cron？**
本地博客没有常驻进程，引入定时任务只会多一个要维护的组件。可见性在每次查询时按
`pub_time <= now` 判断，到点下一次刷新页面就出现——零依赖、不会漏跑。

**复现参考项目：深色模式为什么写两段重复的 palette？**
CSS 没法把 `[data-theme="dark"]`（手动切换）和 `@media (prefers-color-scheme: dark)`
（跟随系统）合成一个选择器，所以变量块只能写两遍。为了不让两边漂移，两段相邻放、
注释写明同步修改，并在 `blog/tests_theme.py` 里断言两边关键字都存在。

## 下一步（本地交付，不部署）

**这个项目按本地项目交付，不需要上传到云端。** 平时就是：

```powershell
cd D:\ai宝贝\12_我的博客\myblog
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

浏览器打开 <http://127.0.0.1:8000/>；或者直接双击 `启动.bat`。

给组长验收用「本地演示」代替线上链接：

- [ ] 本地演示包：`启动.bat` + 30 秒演示脚本 + 截图（`12_我的博客/汇报材料_*`）
- [ ] 组长要看时，当面打开电脑演示；不在场就发截图/录屏（Win+G 录 30 秒）
- [ ] 每周跑一次 `python manage.py backup`（数据库 + 封面图备份到 `backups/`）

### 复现 DjangoBlog：第二批进展

- ✅ **草稿 + 定时发布**（2026-11-23）：`status` + `pub_time`，到点才出现在前台
- ✅ **深色模式**（2026-11-23）：`prefers-color-scheme` + 顶栏手动切换
- ⬜ **全文搜索 + 高亮**：本地用 Whoosh（不装 Elasticsearch），搜正文、关键词标黄
- ⬜ **友链页 + 作者页**：`Links` 模型、按作者筛文章
- ⬜ **简化插件机制**：文章版权声明、外链图标、SEO 插件（参考项目有 8 个插件）

**明确不做**：Docker/K8s、MySQL、Redis、Elasticsearch、Tailwind+Vite、OAuth 登录
（这些是参考项目的生产环境方案，和「本地项目」的定位冲突）。

> 如果哪天改变主意想上线，`docs/04_部署手册.md` 里已经写好了完整步骤
> （PythonAnywhere 免费方案），照着做即可。部署相关的配置（WhiteNoise、
> HTTPS 开关、`STATIC_ROOT`）只在 `DEBUG=False` 时生效，本地开发完全不受影响。

以后可选的加分项（都不是必须）：

- 再写几篇文章（现在 3 篇，内容越多越像真博客）
- 全文搜索（本地 Whoosh，带关键词高亮）
- 友链页 / 作者页
- 评论 / 点赞（个人本地项目意义不大）

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
