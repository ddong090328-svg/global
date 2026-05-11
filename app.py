# ─────────────────────────────────────────────────────────────
# 기후변화 뉴스 감성 분석 대시보드
# RSS 피드 수집 → 키워드 기반 감성 분석 → 시각화
# API 키 불필요, Streamlit Cloud 바로 배포 가능
# ─────────────────────────────────────────────────────────────

import streamlit as st
import feedparser
import requests
import re
from collections import Counter
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# ─────────────────────────────────────────────────────────────
# 워드클라우드 라이브러리 (없으면 해당 섹션 비활성화)
# ─────────────────────────────────────────────────────────────
try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
    from PIL import Image
    import io
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False

# ─────────────────────────────────────────────────────────────
# 페이지 기본 설정
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="기후변화 뉴스 감성 분석",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────
# 커스텀 CSS 스타일
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a5276;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #5d6d7e;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #eaf4fb, #d6eaf8);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1a5276;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #5d6d7e;
        margin-top: 0.2rem;
    }
    .tag-pos {
        display: inline-block;
        background: #d5f5e3;
        color: #1e8449;
        border-radius: 20px;
        padding: 4px 12px;
        margin: 3px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .tag-neg {
        display: inline-block;
        background: #fadbd8;
        color: #922b21;
        border-radius: 20px;
        padding: 4px 12px;
        margin: 3px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .article-card {
        background: #f8f9fa;
        border-left: 4px solid #2980b9;
        border-radius: 6px;
        padding: 0.9rem 1.2rem;
        margin-bottom: 0.7rem;
    }
    .article-card.pos { border-left-color: #27ae60; }
    .article-card.neg { border-left-color: #e74c3c; }
    .article-card.neu { border-left-color: #95a5a6; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# RSS 피드 URL 목록 (미디어별)
# ─────────────────────────────────────────────────────────────
RSS_FEEDS = {
    "The Guardian":  "https://www.theguardian.com/world/rss",
    "BBC News":      "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera":    "https://www.aljazeera.com/xml/rss/all.xml",
    "Reuters":       "https://feeds.reuters.com/reuters/worldNews",
    "연합뉴스":      "https://www.yna.co.kr/rss/news.xml",
    "MBC 뉴스":      "https://imnews.imbc.com/rss/news/news_00.xml",
    "경향신문":      "https://www.khan.co.kr/rss/rssdata/total_news.xml",
    "동아일보":      "https://rss.donga.com/total.xml",
    "한국경제":      "https://rss.hankyung.com/economy.xml",
    "매일경제":      "https://file.mk.co.kr/news/rss/rss_30000001.xml",
}

# ─────────────────────────────────────────────────────────────
# 분석 키워드 (기후변화 관련 영어 + 한국어)
# ─────────────────────────────────────────────────────────────
CLIMATE_KEYWORDS_EN = [
    "climate", "climate change", "global warming", "greenhouse", "carbon",
    "emission", "fossil fuel", "renewable", "solar", "wind energy",
    "net zero", "carbon neutral", "ipcc", "cop", "paris agreement",
    "sea level", "arctic", "glacier", "drought", "flood", "wildfire",
    "heatwave", "biodiversity", "deforestation", "methane", "co2",
    "sustainability", "green energy", "decarbonization", "temperature"
]
CLIMATE_KEYWORDS_KO = [
    "기후변화", "기후위기", "지구온난화", "온실가스", "탄소", "탄소중립",
    "탄소배출", "재생에너지", "태양광", "풍력", "에너지전환",
    "탄소발자국", "녹색", "친환경", "기상이변", "폭염", "홍수", "가뭄",
    "해수면", "빙하", "산불", "생물다양성", "환경", "온도상승",
    "파리협약", "기후협약", "이산화탄소", "메탄", "화석연료", "저탄소"
]

# ─────────────────────────────────────────────────────────────
# 감성 분석용 키워드 사전 (영어 + 한국어)
# 필요 시 여기에 단어를 추가하세요
# ─────────────────────────────────────────────────────────────
POSITIVE_WORDS = [
    # 영어 긍정 단어
    "progress", "hope", "solution", "success", "achieve", "improve",
    "breakthrough", "innovation", "agreement", "commitment", "advance",
    "reduce", "clean", "sustainable", "green", "renewable", "recovery",
    "protect", "save", "benefit", "opportunity", "positive", "effective",
    "historic", "landmark", "pledge", "invest", "fund", "support",
    "grow", "rise", "increase", "record", "celebrate", "win",
    # 한국어 긍정 단어
    "성공", "희망", "발전", "개선", "혁신", "합의", "달성", "해결",
    "감소", "친환경", "재생", "보호", "투자", "지원", "증가", "기록",
    "협력", "약속", "긍정", "효과적", "획기적", "선도", "극복",
    "전환", "청정", "회복", "진전", "확대", "성장"
]

NEGATIVE_WORDS = [
    # 영어 부정 단어
    "crisis", "disaster", "catastrophe", "failure", "threat", "danger",
    "risk", "destroy", "damage", "loss", "extreme", "severe", "worsen",
    "decline", "collapse", "warn", "alarm", "urgent", "fear", "concern",
    "problem", "challenge", "emit", "pollute", "toxic", "deadly",
    "flood", "drought", "wildfire", "heatwave", "melt", "extinction",
    "die", "dead", "kill", "suffer", "vulnerable", "impact", "harm",
    # 한국어 부정 단어
    "위기", "재난", "재앙", "실패", "위협", "위험", "파괴", "피해",
    "손실", "악화", "심각", "경고", "우려", "문제", "도전", "오염",
    "유독", "치명", "홍수", "가뭄", "산불", "폭염", "소멸", "멸종",
    "사망", "고통", "취약", "영향", "피해", "증가", "상승", "이상"
]

# ─────────────────────────────────────────────────────────────
# 불용어 목록 (워드클라우드 + 연관어 분석용)
# ─────────────────────────────────────────────────────────────
STOPWORDS_EN = {
    "a", "an", "the", "in", "on", "at", "to", "of", "and", "or",
    "is", "are", "was", "were", "http", "https", "www", "html",
    "com", "nbsp", "says", "said", "be", "by", "for", "with",
    "as", "it", "its", "this", "that", "from", "but", "not",
    "have", "has", "had", "he", "she", "they", "we", "you", "i",
    "will", "would", "could", "should", "may", "might", "do", "does"
}
STOPWORDS_KO = {
    "이", "그", "저", "을", "를", "가", "은", "는", "에서", "으로",
    "에", "의", "와", "과", "도", "만", "로", "부터", "까지", "하다",
    "이다", "있다", "없다", "되다", "하여", "때문에", "위해", "통해",
    "대해", "관련", "따르면", "따라", "대한", "등의", "등을", "등이",
    "한편", "또한", "그러나", "하지만", "따라서", "그리고"
}

# ─────────────────────────────────────────────────────────────
# RSS 수집 함수 (캐싱 적용, 10분마다 갱신)
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def fetch_rss(url: str, media_name: str) -> list:
    """RSS 피드를 수집하고 기사 리스트를 반환합니다."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    articles = []
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        # 한국어 RSS 인코딩 문제 대비: resp.content 사용
        feed = feedparser.parse(resp.content)
        for entry in feed.entries:
            title   = getattr(entry, "title",   "").strip()
            summary = getattr(entry, "summary", "").strip()
            link    = getattr(entry, "link",    "").strip()
            # 5자 미만 제목 건너뛰기
            if len(title) < 5:
                continue
            articles.append({
                "media":   media_name,
                "title":   title,
                "summary": summary,
                "link":    link,
            })
    except Exception as e:
        # 수집 실패 시 빈 리스트 반환 (경고는 호출부에서 처리)
        return []
    return articles

# ─────────────────────────────────────────────────────────────
# 기후변화 관련 기사 필터링
# ─────────────────────────────────────────────────────────────
def is_climate_related(article: dict) -> bool:
    """기사 제목/요약에 기후변화 키워드가 포함되어 있는지 확인합니다."""
    text = (article["title"] + " " + article["summary"]).lower()
    for kw in CLIMATE_KEYWORDS_EN:
        if kw in text:
            return True
    for kw in CLIMATE_KEYWORDS_KO:
        if kw in text:
            return True
    return False

# ─────────────────────────────────────────────────────────────
# 감성 분석 함수 (키워드 사전 방식)
# ─────────────────────────────────────────────────────────────
def analyze_sentiment(text: str) -> dict:
    """텍스트에서 긍정/부정 단어를 세어 감성을 분류합니다."""
    text_lower = text.lower()
    pos_count = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text_lower)

    if pos_count > neg_count:
        label = "긍정"
    elif neg_count > pos_count:
        label = "부정"
    else:
        label = "중립"

    return {
        "label":     label,
        "pos_score": pos_count,
        "neg_score": neg_count,
        "pos_words": [w for w in POSITIVE_WORDS if w in text_lower],
        "neg_words": [w for w in NEGATIVE_WORDS if w in text_lower],
    }

# ─────────────────────────────────────────────────────────────
# 텍스트 토큰화 (연관어 분석용)
# ─────────────────────────────────────────────────────────────
def tokenize(text: str) -> list:
    """텍스트를 단어 단위로 분리하고 불용어를 제거합니다."""
    tokens = re.findall(r'[a-zA-Z가-힣]{2,}', text)
    result = []
    for t in tokens:
        t_lower = t.lower()
        if t_lower not in STOPWORDS_EN and t not in STOPWORDS_KO:
            result.append(t_lower)
    return result

# ─────────────────────────────────────────────────────────────
# 워드클라우드 생성 함수
# ─────────────────────────────────────────────────────────────
def generate_wordcloud(text: str):
    """텍스트로 워드클라우드 이미지를 생성합니다."""
    if not WORDCLOUD_AVAILABLE or not text.strip():
        return None

    # 시스템 한국어 폰트 자동 탐색
    import os
    font_candidates = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/gulim.ttc",
    ]
    font_path = None
    for fp in font_candidates:
        if os.path.exists(fp):
            font_path = fp
            break

    all_stopwords = STOPWORDS_EN | STOPWORDS_KO

    try:
        wc_kwargs = dict(
            width=800,
            height=400,
            background_color="white",
            max_words=100,
            stopwords=all_stopwords,
            collocations=False,
        )
        if font_path:
            wc_kwargs["font_path"] = font_path

        wc = WordCloud(**wc_kwargs).generate(text)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        buf = io.BytesIO()
        plt.tight_layout(pad=0)
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None

# ─────────────────────────────────────────────────────────────
# 사이드바 UI
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌍 설정")
    st.markdown("---")
    st.markdown("**📰 뉴스 소스 선택**")

    selected_media = []
    for media in RSS_FEEDS:
        if st.checkbox(media, value=True, key=f"cb_{media}"):
            selected_media.append(media)

    st.markdown("---")
    st.markdown("**⚙️ 표시 설정**")
    show_articles = st.checkbox("기사 목록 표시", value=True)
    max_articles  = st.slider("최대 표시 기사 수", 5, 100, 30, 5)

    st.markdown("---")
    st.caption("💡 캐시는 10분마다 갱신됩니다")
    if st.button("🔄 지금 새로고침"):
        st.cache_data.clear()
        st.rerun()

# ─────────────────────────────────────────────────────────────
# 메인 헤더
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🌍 기후변화 뉴스 감성 분석 대시보드</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-title">실시간 RSS 수집 · 키워드 기반 감성 분류 · '
    f'업데이트: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>',
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────────────────────
# 선택된 미디어가 없을 때
# ─────────────────────────────────────────────────────────────
if not selected_media:
    st.info("👈 왼쪽 사이드바에서 뉴스 소스를 하나 이상 선택해주세요.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# RSS 수집 및 기후변화 기사 필터링
# ─────────────────────────────────────────────────────────────
with st.spinner("📡 뉴스를 수집하는 중..."):
    all_articles = []
    seen_titles  = set()  # 중복 제거용

    for media in selected_media:
        url      = RSS_FEEDS[media]
        fetched  = fetch_rss(url, media)

        if not fetched:
            st.warning(f"⚠️ [{media}] RSS 수집에 실패했습니다. 잠시 후 다시 시도해주세요.")
            continue

        for art in fetched:
            # 중복 제목 건너뛰기
            if art["title"] in seen_titles:
                continue
            seen_titles.add(art["title"])
            # 기후변화 관련 기사만 필터링
            if is_climate_related(art):
                text     = art["title"] + " " + art["summary"]
                sentiment = analyze_sentiment(text)
                art.update(sentiment)
                all_articles.append(art)

# ─────────────────────────────────────────────────────────────
# 수집된 기사가 없을 때 안내 메시지
# ─────────────────────────────────────────────────────────────
if not all_articles:
    st.warning(
        "😔 선택한 미디어에서 기후변화 관련 기사를 찾지 못했습니다.\n\n"
        "- 다른 미디어를 선택해보세요.\n"
        "- RSS 피드가 일시적으로 차단됐을 수 있습니다.\n"
        "- 잠시 후 새로고침 버튼을 눌러주세요."
    )
    st.stop()

# ─────────────────────────────────────────────────────────────
# 감성 통계 집계
# ─────────────────────────────────────────────────────────────
total   = len(all_articles)
pos_cnt = sum(1 for a in all_articles if a["label"] == "긍정")
neg_cnt = sum(1 for a in all_articles if a["label"] == "부정")
neu_cnt = sum(1 for a in all_articles if a["label"] == "중립")

# ─────────────────────────────────────────────────────────────
# 상단 요약 지표 카드
# ─────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f'<div class="metric-card"><div class="metric-value">{total}</div>'
        f'<div class="metric-label">📰 수집된 기사</div></div>',
        unsafe_allow_html=True
    )
with c2:
    st.markdown(
        f'<div class="metric-card" style="background:linear-gradient(135deg,#d5f5e3,#a9dfbf)">'
        f'<div class="metric-value" style="color:#1e8449">{pos_cnt}</div>'
        f'<div class="metric-label">😊 긍정 기사</div></div>',
        unsafe_allow_html=True
    )
with c3:
    st.markdown(
        f'<div class="metric-card" style="background:linear-gradient(135deg,#fadbd8,#f1948a)">'
        f'<div class="metric-value" style="color:#922b21">{neg_cnt}</div>'
        f'<div class="metric-label">😟 부정 기사</div></div>',
        unsafe_allow_html=True
    )
with c4:
    st.markdown(
        f'<div class="metric-card" style="background:linear-gradient(135deg,#f2f3f4,#d5d8dc)">'
        f'<div class="metric-value" style="color:#5d6d7e">{neu_cnt}</div>'
        f'<div class="metric-label">😐 중립 기사</div></div>',
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 차트 섹션 (긍정/부정 막대 차트 + 미디어별 분포)
# ─────────────────────────────────────────────────────────────
col_chart1, col_chart2 = st.columns([1, 1])

with col_chart1:
    st.markdown("#### 📊 감성 분포")
    fig_bar = go.Figure(go.Bar(
        x=["긍정 😊", "부정 😟", "중립 😐"],
        y=[pos_cnt, neg_cnt, neu_cnt],
        marker_color=["#27ae60", "#e74c3c", "#95a5a6"],
        text=[pos_cnt, neg_cnt, neu_cnt],
        textposition="outside",
        width=0.5,
    ))
    fig_bar.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="#eee"),
        xaxis=dict(showgrid=False),
        margin=dict(t=20, b=20, l=20, r=20),
        height=300,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_chart2:
    st.markdown("#### 🗞️ 미디어별 기사 수")
    media_counts = Counter(a["media"] for a in all_articles)
    media_df_sorted = sorted(media_counts.items(), key=lambda x: x[1], reverse=True)
    media_names = [x[0] for x in media_df_sorted]
    media_vals  = [x[1] for x in media_df_sorted]

    fig_media = go.Figure(go.Bar(
        x=media_vals,
        y=media_names,
        orientation="h",
        marker_color="#2980b9",
        text=media_vals,
        textposition="outside",
    ))
    fig_media.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#eee"),
        yaxis=dict(showgrid=False),
        margin=dict(t=20, b=20, l=10, r=40),
        height=300,
    )
    st.plotly_chart(fig_media, use_container_width=True)

# ─────────────────────────────────────────────────────────────
# 연관어 태그 섹션
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 🏷️ 연관어 태그")

col_pos_tag, col_neg_tag = st.columns(2)

# 긍정 기사에서 자주 등장한 단어 추출
pos_texts = " ".join(
    a["title"] + " " + a["summary"]
    for a in all_articles if a["label"] == "긍정"
)
neg_texts = " ".join(
    a["title"] + " " + a["summary"]
    for a in all_articles if a["label"] == "부정"
)

pos_tokens  = tokenize(pos_texts)
neg_tokens  = tokenize(neg_texts)
top_pos_words = [w for w, _ in Counter(pos_tokens).most_common(20) if len(w) > 1]
top_neg_words = [w for w, _ in Counter(neg_tokens).most_common(20) if len(w) > 1]

with col_pos_tag:
    st.markdown("**😊 긍정 연관어**")
    if top_pos_words:
        tags_html = "".join(f'<span class="tag-pos">#{w}</span>' for w in top_pos_words)
        st.markdown(tags_html, unsafe_allow_html=True)
    else:
        st.caption("긍정 기사가 없습니다.")

with col_neg_tag:
    st.markdown("**😟 부정 연관어**")
    if top_neg_words:
        tags_html = "".join(f'<span class="tag-neg">#{w}</span>' for w in top_neg_words)
        st.markdown(tags_html, unsafe_allow_html=True)
    else:
        st.caption("부정 기사가 없습니다.")

# ─────────────────────────────────────────────────────────────
# 워드클라우드 섹션
# ─────────────────────────────────────────────────────────────
if WORDCLOUD_AVAILABLE:
    st.markdown("---")
    st.markdown("#### ☁️ 워드클라우드")
    wc_col1, wc_col2 = st.columns(2)

    with wc_col1:
        st.markdown("**😊 긍정 기사 워드클라우드**")
        buf = generate_wordcloud(pos_texts)
        if buf:
            st.image(buf, use_container_width=True)
        else:
            st.caption("긍정 기사 텍스트가 부족합니다.")

    with wc_col2:
        st.markdown("**😟 부정 기사 워드클라우드**")
        buf = generate_wordcloud(neg_texts)
        if buf:
            st.image(buf, use_container_width=True)
        else:
            st.caption("부정 기사 텍스트가 부족합니다.")

# ─────────────────────────────────────────────────────────────
# 기사 목록 섹션
# ─────────────────────────────────────────────────────────────
if show_articles:
    st.markdown("---")
    st.markdown("#### 📋 기사 목록")

    # 필터 탭
    tab_all, tab_pos, tab_neg, tab_neu = st.tabs(
        [f"전체 ({total})", f"긍정 ({pos_cnt})", f"부정 ({neg_cnt})", f"중립 ({neu_cnt})"]
    )

    def render_articles(articles, limit):
        if not articles:
            st.info("해당 감성의 기사가 없습니다.")
            return
        for art in articles[:limit]:
            label = art["label"]
            css_cls = {"긍정": "pos", "부정": "neg", "중립": "neu"}.get(label, "neu")
            emoji   = {"긍정": "😊", "부정": "😟", "중립": "😐"}.get(label, "😐")
            color   = {"긍정": "#27ae60", "부정": "#e74c3c", "중립": "#95a5a6"}.get(label, "#95a5a6")

            summary_text = art["summary"][:150] + "..." if len(art["summary"]) > 150 else art["summary"]
            link_html = (
                f'<a href="{art["link"]}" target="_blank" style="color:#2980b9;font-size:0.8rem;">🔗 원문 보기</a>'
                if art["link"] else ""
            )

            st.markdown(
                f'<div class="article-card {css_cls}">'
                f'<span style="color:{color};font-weight:700">{emoji} [{label}]</span> '
                f'<span style="font-size:0.75rem;color:#888">· {art["media"]}</span><br>'
                f'<span style="font-weight:600">{art["title"]}</span><br>'
                f'<span style="font-size:0.85rem;color:#555">{summary_text}</span><br>'
                f'{link_html}'
                f'</div>',
                unsafe_allow_html=True
            )

    with tab_all:
        render_articles(all_articles, max_articles)
    with tab_pos:
        render_articles([a for a in all_articles if a["label"] == "긍정"], max_articles)
    with tab_neg:
        render_articles([a for a in all_articles if a["label"] == "부정"], max_articles)
    with tab_neu:
        render_articles([a for a in all_articles if a["label"] == "중립"], max_articles)

# ─────────────────────────────────────────────────────────────
# 푸터
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "🌍 기후변화 뉴스 감성 분석 대시보드 · RSS 기반 · API 키 불필요 · "
    "Streamlit Cloud 배포 가능"
)
