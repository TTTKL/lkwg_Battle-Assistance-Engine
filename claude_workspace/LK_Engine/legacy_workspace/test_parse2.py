"""测试 biligame 抓取和解析"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import time, requests, urllib.parse
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'}

# 直接重现解析过程
def fetch_and_parse(name):
    url = 'https://wiki.biligame.com/rocom/' + urllib.parse.quote(name)
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.find('div', class_='mw-parser-output')
    if not content:
        return None, None
    text = content.get_text(separator=' | ', strip=True)
    if '✦' not in text:
        return None, text[:200]
    parts = [p.strip() for p in text.split('|') if p.strip()]
    desc = ''
    for i, part in enumerate(parts):
        if '✦' in part:
            desc = part.replace('✦', '').strip()
            for j in range(i+1, len(parts)):
                if '可以学会' in parts[j]:
                    break
                desc += ' ' + parts[j]
            break
    return desc.strip(), None

import re
def parse_effects(desc):
    effects = []
    if not desc:
        return effects
    main_desc = desc
    for ct in ('应对攻击','应对防御','应对状态'):
        if ct in desc:
            main_desc = desc[:desc.index(ct)].strip().rstrip('，,；;')
            break
    # 治疗
    for m in re.finditer(r'(?:回复|恢复)(\d+)%(?:生命|血量)', desc):
        effects.append({'type':'heal','percent':int(m.group(1))/100})
    # 中毒
    for m in re.finditer(r'(\d+)层中毒', desc):
        effects.append({'type':'status_ailment','ailment':'poison','layers':int(m.group(1)),'target':'enemy'})
    if '中毒' in desc and not effects:
        effects.append({'type':'status_ailment','ailment':'poison','layers':1,'target':'enemy'})
    # 印记
    if '棘刺印记' in desc:
        m = re.search(r'(\d+)层棘刺印记', desc)
        stacks = int(m.group(1)) if m else 1
        effects.append({'type':'apply_mark','mark':'thorn','stacks':stacks,'target':'enemy'})
    return effects

for name in ['棘刺', '剧毒', '休息回复']:
    desc, raw_text = fetch_and_parse(name)
    print(f'[{name}]')
    if desc is not None:
        print(f'  desc: {desc}')
        print(f'  effects: {parse_effects(desc)}')
    else:
        print(f'  biligame原始: {raw_text}')
    print()
    time.sleep(0.3)
