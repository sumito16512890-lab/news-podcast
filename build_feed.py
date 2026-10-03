"""episodes/*.mp3 から feed.xml を作る。KEEP を数値にすると古い回を削除する（None なら全回を残す）。

使い方: python3 build_feed.py https://<ユーザー名>.github.io/<リポジトリ名>
各回の説明文は episodes/YYYY-MM-DD.txt（任意）に書く。
"""
import email.utils
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

KEEP = None  # None = 過去の回を消さない
HERE = os.path.dirname(os.path.abspath(__file__))
EP_DIR = os.path.join(HERE, "episodes")
JST = timezone(timedelta(hours=9))


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout
    return int(float(out))


def main(base):
    base = base.rstrip("/")
    mp3s = sorted(f for f in os.listdir(EP_DIR) if f.endswith(".mp3"))
    for old in (mp3s[:-KEEP] if KEEP else []):
        os.remove(os.path.join(EP_DIR, old))
        txt = os.path.join(EP_DIR, old[:-4] + ".txt")
        if os.path.exists(txt):
            os.remove(txt)
    mp3s = mp3s[-KEEP:] if KEEP else mp3s

    items = []
    for f in reversed(mp3s):
        day = f[:-4]
        path = os.path.join(EP_DIR, f)
        d = datetime.strptime(day, "%Y-%m-%d").replace(hour=6, tzinfo=JST)
        txt = os.path.join(EP_DIR, day + ".txt")
        desc = open(txt, encoding="utf-8").read().strip() if os.path.exists(txt) else ""
        title = f"{d.month}月{d.day}日のニュース"
        items.append(f"""    <item>
      <title>{escape(title)}</title>
      <description>{escape(desc)}</description>
      <enclosure url="{base}/episodes/{f}" length="{os.path.getsize(path)}" type="audio/mpeg"/>
      <guid isPermaLink="false">news-{day}</guid>
      <pubDate>{email.utils.format_datetime(d)}</pubDate>
      <itunes:duration>{duration(path)}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>""")

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>毎日のニュース</title>
    <link>{base}/</link>
    <language>ja</language>
    <description>その日の主なニュースと兵庫県のニュースを、約20分の音声でまとめた個人用の番組です。音声はAIによる読み上げです。</description>
    <itunes:author>個人用</itunes:author>
    <itunes:image href="{base}/cover.jpg"/>
    <itunes:category text="News"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
{chr(10).join(items)}
  </channel>
</rss>
"""
    with open(os.path.join(HERE, "feed.xml"), "w", encoding="utf-8") as fh:
        fh.write(feed)

    # Safari でそのまま聴けるページ（バックグラウンド再生可）
    rows = []
    for f in reversed(mp3s):
        d = datetime.strptime(f[:-4], "%Y-%m-%d")
        txt = os.path.join(EP_DIR, f[:-4] + ".txt")
        desc = open(txt, encoding="utf-8").read().strip() if os.path.exists(txt) else ""
        rows.append(f'<li><b>{d.month}月{d.day}日のニュース</b><p>{escape(desc)}</p>'
                    f'<audio controls preload="none" src="episodes/{f}"></audio></li>')
    page = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>毎日のニュース</title>
<link rel="apple-touch-icon" href="cover.jpg">
<style>
:root{{--bg:#f3f5f7;--fg:#1c2530;--muted:#5d6b7a;--card:#fff;--line:#dde3ea}}
@media (prefers-color-scheme:dark){{:root{{--bg:#11161c;--fg:#e6ebf0;--muted:#98a6b5;--card:#1a212a;--line:#2a3440}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,"Hiragino Sans",sans-serif;padding:24px 16px}}
main{{max-width:560px;margin:0 auto}} h1{{font-size:24px}} ul{{list-style:none;padding:0;display:flex;flex-direction:column;gap:12px}}
li{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}} li p{{color:var(--muted);font-size:14px;margin:6px 0 10px}}
audio{{width:100%}}
</style></head><body><main>
<h1>毎日のニュース</h1>
<ul>{''.join(rows)}</ul>
</main></body></html>
"""
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"feed.xml: {len(items)} episodes")


if __name__ == "__main__":
    main(sys.argv[1])
