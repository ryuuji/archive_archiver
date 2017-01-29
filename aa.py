# coding=utf-8

"""
デジタルアーカイブアーカイブツール
"""

import requests
import urlparse
import math
import StringIO
from PIL import Image
from bs4 import BeautifulSoup
import concurrent.futures
from PyPDF2 import PdfFileMerger

__copyright__ = "Copyright (C) 2016 Ryuuji Yoshimoto"
__author__ = "Ryuuji Yoshimoto <ryuuji@calil.jp>"
__licence__ = "MIT"

# トップページURL
index_url = 'https://trc-adeac.trc.co.jp/Html/BookletView/2120605100/2120605100100010/nktgshishi0101/'


# インデックスページをロード
def load_index(url):
    r = requests.get(url)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'lxml')
    pages = []
    for page in soup.select('.ftrselop'):
        pages.append(urlparse.urljoin(url, "./data/%03d/dzc_output.xml" % int(page.text)))
    return pages


# Deep Zoomの画像をダウンロードして結合
def load_deepzoom(url):
    r = requests.get(url)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'lxml')
    tile_size = int(soup.select_one('image')['tilesize'])
    width = int(soup.select_one('image').size['width'])
    height = int(soup.select_one('image').size['height'])
    maxzoom = int(math.ceil(math.log(max(width, height), 2)))
    x = 0
    y = 0
    face = Image.new('RGB', (width, height))
    # 参考:https://github.com/lovasoa/dezoomify/blob/master/zoommanager.js
    while 1:
        tile_url = urlparse.urljoin(url, './dzc_output_files/%d/%d_%d.jpg' % (maxzoom, x, y))
        im = Image.open(requests.get(tile_url, stream=True).raw)
        face.paste(im, (x * tile_size, y * tile_size))
        print tile_url
        x += 1
        if x > math.ceil(width / tile_size):
            x = 0
            y += 1
        if y > math.ceil(height / tile_size):
            break
    return url, face


# 並列処理でデータを取得
tile_urls = load_index(index_url)[0:4]
result_images = [None] * len(tile_urls)
executor = concurrent.futures.ThreadPoolExecutor(max_workers=30)
futures = [executor.submit(load_deepzoom, u) for u in tile_urls]
for future in concurrent.futures.as_completed(futures):
    u, img = future.result()
    result_images[tile_urls.index(u)] = img
executor.shutdown()

# PDFに結合
merger = PdfFileMerger()
for idx, img in enumerate(result_images):
    _tmp = StringIO.StringIO()
    img.save(_tmp, 'PDF')
    merger.append(fileobj=_tmp)
with open("output.pdf", "wb") as f:
    merger.write(f)
