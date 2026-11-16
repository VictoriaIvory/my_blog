"""站点地图（/sitemap.xml）。

搜索引擎和站长工具会来读它。用最简单的 XML 手写，
不引 django.contrib.sitemaps（那需要再装 sites 框架）。
"""

from django.http import HttpResponse
from django.urls import reverse

from .models import Post


def sitemap(request):
    static_urls = [
        request.build_absolute_uri(reverse('blog:list')),
        request.build_absolute_uri(reverse('blog:archive')),
        request.build_absolute_uri(reverse('blog:about')),
    ]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in static_urls:
        lines.append(f'  <url><loc>{url}</loc><changefreq>weekly</changefreq></url>')

    for post in Post.objects.filter(is_published=True).only('pk', 'updated_at'):
        loc = request.build_absolute_uri(reverse('blog:detail', args=[post.pk]))
        lastmod = post.updated_at.date().isoformat()
        lines.append(
            f'  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>'
        )

    lines.append('</urlset>')
    return HttpResponse('\n'.join(lines), content_type='application/xml')
