#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KBO 순위 자동 수집 → standings.json 생성
- KBO 공식 순위 페이지(일자별 팀 순위)를 파싱합니다.
- 페이지 구조가 바뀌면 CSS/열 매핑만 손보면 됩니다.
- 10개 팀을 못 찾으면 실패(exit 1)하여 기존 standings.json을 보존합니다.

필요 패키지: requests, beautifulsoup4
"""
import json, sys, re, datetime, zoneinfo

import requests
from bs4 import BeautifulSoup

URL = "https://www.koreabaseball.com/Record/TeamRank/TeamRankDaily.aspx"

# HTML(페넌트레이스_내기.html)이 쓰는 표준 팀 키
CANON = {"삼성","KT","LG","KIA","두산","한화","NC","롯데","SSG","키움"}
ALIAS = {
    "삼성":"삼성","두산":"두산","롯데":"롯데","한화":"한화","키움":"키움","넥센":"키움",
    "kt":"KT","lg":"LG","kia":"KIA","기아":"KIA","nc":"NC","ssg":"SSG",
    "kt wiz":"KT","lg 트윈스":"LG",
}
def canon(name:str):
    n = (name or "").strip()
    if n in CANON: return n
    return ALIAS.get(n.lower(), ALIAS.get(n))

def to_int(x):
    x = re.sub(r"[^\d\-]", "", x or "")
    return int(x) if x not in ("","-") else 0

def scrape():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }
    r = requests.get(URL, headers=headers, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # 순위 표 찾기: 헤더에 '승' '패' '승률'이 모두 있는 table
    target = None
    for tbl in soup.find_all("table"):
        head = " ".join(th.get_text() for th in tbl.find_all("th"))
        if ("승" in head and "패" in head and "승률" in head):
            target = tbl; break
    if target is None:
        raise RuntimeError("순위 테이블을 찾지 못했습니다 (페이지 구조 변경 가능)")

    # 헤더 인덱스 매핑
    ths = [th.get_text(strip=True) for th in target.find_all("th")]
    def idx(*names, default=None):
        for i,h in enumerate(ths):
            if h in names: return i
        return default
    i_team = idx("팀명","팀", default=1)
    i_w    = idx("승", default=3)
    i_l    = idx("패", default=4)
    i_d    = idx("무", default=5)

    teams = {}
    for tr in target.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < max(i_team,i_w,i_l,i_d)+1:
            continue
        name = canon(tds[i_team].get_text(strip=True))
        if not name:
            continue
        teams[name] = {"w": to_int(tds[i_w].get_text()),
                       "d": to_int(tds[i_d].get_text()),
                       "l": to_int(tds[i_l].get_text())}

    if set(teams.keys()) != CANON:
        raise RuntimeError(f"팀 10개를 모두 수집하지 못했습니다. 수집됨: {sorted(teams)}")
    return teams

def main():
    teams = scrape()
    kst = zoneinfo.ZoneInfo("Asia/Seoul")
    now = datetime.datetime.now(kst)
    out = {
        "asof": now.strftime("%Y-%m-%d"),
        "updated": now.isoformat(timespec="seconds"),
        "source": "koreabaseball.com",
        "teams": teams,
    }
    with open("standings.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("OK:", json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("SCRAPE FAILED:", e, file=sys.stderr)
        sys.exit(1)
