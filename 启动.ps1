# 启动博客开发服务器
# ---------------------------------------------------------------
# 用法一：右键本文件 -> 使用 PowerShell 运行
# 用法二：双击同目录的「启动.bat」（更省事）
# ---------------------------------------------------------------

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

Write-Host ''
Write-Host '=== 我的博客 · 开发服务器 ===' -ForegroundColor Cyan
Write-Host ''

# 1. 进项目目录
Set-Location $root
Write-Host "[1/3] 目录：$root"

# 2. 检查虚拟环境
$venvPy = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) {
    Write-Host ''
    Write-Host '找不到虚拟环境 .venv\' -ForegroundColor Red
    Write-Host '解决办法：' -ForegroundColor Yellow
    Write-Host '  python -m venv .venv'
    Write-Host '  .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
    Write-Host ''
    Read-Host '按回车退出'
    exit 1
}
Write-Host '[2/3] 虚拟环境：正常'

# 3. 检查 .env（没有它启动会报「缺少 DJANGO_SECRET_KEY」）
$envFile = Join-Path $root '.env'
if (-not (Test-Path $envFile)) {
    Write-Host ''
    Write-Host '缺少 .env 文件（密钥配置）' -ForegroundColor Red
    Write-Host '解决办法：' -ForegroundColor Yellow
    Write-Host '  Copy-Item .env.example .env'
    Write-Host '  然后把 .env 里的 DJANGO_SECRET_KEY 换成一个自己生成的值'
    Write-Host '  生成命令：python -c "import secrets; print(secrets.token_urlsafe(50))"'
    Write-Host ''
    Read-Host '按回车退出'
    exit 1
}

# 4. 检查端口占用
$busy = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    Write-Host ''
    Write-Host '8000 端口被占用（可能是上次的服务器没关干净）' -ForegroundColor Yellow
    Write-Host '可以继续用 8001：' -ForegroundColor Yellow
    Write-Host '  python manage.py runserver 8001'
    Write-Host ''
}

Write-Host '[3/3] 启动中…… 浏览器会自动打开 http://127.0.0.1:8000/'
Write-Host '      关掉服务器：在本窗口按 Ctrl + C'
Write-Host ''

# 5. 3 秒后自动打开浏览器（不等服务器，起个独立进程）
Start-Process powershell -WindowStyle Hidden -ArgumentList @(
    '-NoProfile', '-Command',
    'Start-Sleep -Seconds 3; Start-Process "http://127.0.0.1:8000/"'
) -ErrorAction SilentlyContinue

# 6. 起服务器（阻塞，Ctrl+C 结束）
try {
    & $venvPy manage.py runserver
}
catch {
    Write-Host ''
    Write-Host '服务器异常退出。常见原因：' -ForegroundColor Red
    Write-Host '  ModuleNotFoundError: No module named ''django''  -> 依赖没装齐'
    Write-Host '  That port is already in use                     -> 换 8001'
    Write-Host '  缺少 DJANGO_SECRET_KEY                           -> .env 没配好'
}

Write-Host ''
Read-Host '服务器已停止，按回车关闭窗口'
