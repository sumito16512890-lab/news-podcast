#!/usr/bin/env bash
# 原稿から1回分の音声を作り、Safariページ／ポッドキャストに公開する。
# 使い方: ./make_episode.sh YYYY-MM-DD 原稿.txt "一行の要約"
set -euo pipefail
DAY=$1; SCRIPT=$(cd "$(dirname "$2")" && pwd)/$(basename "$2"); SUMMARY=$3
HERE=$(cd "$(dirname "$0")" && pwd)
BASE=https://sumito16512890-lab.github.io/news-podcast
export VOICE=Leda CHUNK=1200
export STYLE="次の日本語のニュース原稿を、明るく高めの声のトーンで、はきはきと親しみやすい女性ニュースキャスターとして、原稿どおりに読み上げてください。"
# クラウド環境などで ffmpeg が無ければ入れる
if ! command -v ffmpeg >/dev/null; then
  (sudo -n apt-get update -qq && sudo -n apt-get install -y -qq ffmpeg) || (apt-get update -qq && apt-get install -y -qq ffmpeg)
fi
mkdir -p "$HERE/work"; cd "$HERE/tools"
RAW="$HERE/work/$DAY-raw.wav"

# 1. Gemini で読み上げ（無料枠はモデルごとに1日10回なので、だめなら次のモデル）
OK=""
for M in gemini-3.8-flash-tts gemini-3.1-flash-tts-preview gemini-2.5-flash-preview-tts; do
  if MODEL=$M python3 gtts.py "$SCRIPT" "$HERE/work/$DAY-tmp.mp3"; then
    MODEL=$M python3 assemble.py "$SCRIPT" $CHUNK "$RAW"; OK=$M; break
  fi
done
# 全部だめなら Microsoft の Nanami で代用
if [[ -z $OK ]]; then
  [[ -x "$HERE/.venv/bin/edge-tts" ]] || { python3 -m venv "$HERE/.venv" && "$HERE/.venv/bin/pip" install -q edge-tts; }
  "$HERE/.venv/bin/edge-tts" --voice ja-JP-NanamiNeural -f "$SCRIPT" --write-media "$HERE/work/$DAY-edge.mp3"
  ffmpeg -y -loglevel error -i "$HERE/work/$DAY-edge.mp3" -ar 24000 -ac 1 "$RAW"; OK=edge-tts
fi

# 2. 20分に近づける（遅くするのは最大5%まで）
LEN=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$RAW")
TEMPO=$(python3 -c "print(max(0.95, min(1.0, $LEN/1200)))")

# 3. 音割れ・プツッ音の補正と音量調整をして 128kbps で保存
OUT="$HERE/episodes/$DAY.mp3"
ffmpeg -y -loglevel error -i "$RAW" \
  -af "aformat=sample_fmts=fltp,adeclip,volume=0.7,adeclick,highpass=f=60,lowpass=f=9500,atempo=$TEMPO,alimiter=limit=0.89,loudnorm=I=-16:TP=-1.5:LRA=11" \
  -ar 24000 -ac 1 -c:a libmp3lame -b:a 128k "$OUT"
printf '%s\n' "$SUMMARY" > "$HERE/episodes/$DAY.txt"
if [[ -d "$HERE/../news" ]]; then cp "$OUT" "$HERE/../news/news-$DAY.mp3"; fi

# 4. ページと配信ファイルを更新して公開
cd "$HERE"
python3 build_feed.py "$BASE"
git add -A
git -c user.name=sumito16512890-lab -c user.email=sumito16512890-lab@users.noreply.github.com \
  commit -q -m "Add $DAY episode" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q origin HEAD:main
echo "voice=$OK tempo=$TEMPO duration=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")"
