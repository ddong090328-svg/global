# ============================================
# 기후변화 뉴스 감성 분석 대시보드
# - RSS 기반 뉴스 수집
# - API 키 없이 감성 분석
# - Streamlit Cloud 배포용
# ============================================

import streamlit as st
import feedparser
import requests
import pandas as pd
import plotly.express as px
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
import platform
from io import BytesIO

# ============================================
# 페이지 설정
# ============================================

st.set_page_config(
    page_title="기후변화 뉴스 감성 분석",
    layout="wide"
)

st.title("🌍 기후변화 뉴스 감성 분석 대시보드")
st.caption("RSS 기반 실시간 뉴스 감성 분석 (API 키 사용 없음)")

# ============================================
# RSS 수집용 User-Agent
# ============================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ============================================
# 뉴스 미디어 RSS 목록
# ============================================

RSS_FEEDS = {
    "The Guardian": "https://www.theguardian.com/world/rss",
    "BBC News": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Reuters": "https://feeds.reuters.com/reuters/worldNews",
    "연합뉴스": "https://www.yna.co.kr/rss/news.xml",
    "MBC 뉴스": "https://imnews.imbc.com/rss/news/news_00.xml",
    "경향신문": "https://www.khan.co.kr/rss/rssdata/total_news.xml",
    "동아일보": "https://rss.donga.com/total.xml",
    "한국경제": "https://rss.hankyung.com/economy.xml",
    "매일경제": "https://file.mk.co.kr/news/rss/rss_30000001.xml"
}

# ============================================
# 감성 분석 키워드 사전
# - 자유롭게 단어 추가 가능
# ============================================

POSITIVE_WORDS = [
    "growth", "success", "improve", "innovation", "clean",
    "green", "sustainable", "renewable", "positive",
    "hope", "recover", "benefit", "good", "excellent",
    "친환경", "성장", "회복", "개선", "혁신",
    "지속가능", "재생에너지", "탄소중립", "성과",
    "희망", "발전", "확대", "친환경적"
]

NEGATIVE_WORDS = [
    "crisis", "disaster", "pollution", "damage", "decline",
    "risk", "danger", "failure", "problem", "loss",
    "warming", "flood", "fire", "drought",
    "위기", "재난", "오염", "피해", "감소",
    "위험", "실패", "문제", "손실", "폭염",
    "홍수", "가뭄", "산불", "기후위기"
]

# ============================================
# 불용어 처리
# ============================================

STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "to", "of",
    "and", "or", "is", "are", "was", "were",
    "http", "https", "www", "html", "com",
    "nbsp", "says", "said",
    "이", "그", "저", "을", "를", "가",
    "은", "는", "에서", "으로", "에",
    "의", "와", "과"
}

# ============================================
# 한국어 폰트 자동 탐색
# ============================================

def get_korean_font():
    system = platform.system()

    if system == "Windows":
        return "malgun.ttf"

    elif system == "Darwin":
        return "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

    else:
        linux_fonts = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]

        for font in linux_fonts:
            try:
                with open(font, "rb"):
                    return font
            except:
                continue

    return None

FONT_PATH = get_korean_font()

# ============================================
# RSS 뉴스 수집 함수
# ============================================

@st.cache_data(ttl=600)
def fetch_news(selected_media):

    articles = []
    seen_titles = set()

    for media in selected_media:

        url = RSS_FEEDS[media]

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

            feed = feedparser.parse(response.content)

            for entry in feed.entries:

                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()

                # 제목 너무 짧으면 제외
                if len(title) < 5:
                    continue

                # 중복 기사 제거
                if title in seen_titles:
                    continue

                seen_titles.add(title)

                text = f"{title} {summary}"

                # 기후변화 관련 기사만 필터링
                keywords = [
                    "climate",
                    "global warming",
                    "carbon",
                    "environment",
                    "기후",
                    "탄소",
                    "환경",
                    "온난화"
                ]

                if any(k.lower() in text.lower() for k in keywords):

                    articles.append({
                        "media": media,
                        "title": title,
                        "summary": summary,
                        "link": entry.get("link", ""),
                    })

        except Exception:
            st.warning(f"⚠️ {media} RSS 수집 실패")

    return articles

# ============================================
# 감성 분석 함수
# ============================================

def analyze_sentiment(text):

    text_lower = text.lower()

    positive_count = sum(
        text_lower.count(word.lower())
        for word in POSITIVE_WORDS
    )

    negative_count = sum(
        text_lower.count(word.lower())
        for word in NEGATIVE_WORDS
    )

    if positive_count > negative_count:
        sentiment = "긍정"

    elif negative_count > positive_count:
        sentiment = "부정"

    else:
        sentiment = "중립"

    return sentiment, positive_count, negative_count

# ============================================
# 텍스트 정제
# ============================================

def clean_text(text):

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^가-힣a-zA-Z\s]", " ", text)

    words = text.lower().split()

    words = [
        word for word in words
        if word not in STOPWORDS and len(word) > 1
    ]

    return words

# ============================================
# 사이드바
# ============================================

st.sidebar.header("📰 뉴스 미디어 선택")

selected_media = []

for media in RSS_FEEDS.keys():

    checked = st.sidebar.checkbox(media, value=True)

    if checked:
        selected_media.append(media)

# ============================================
# 뉴스 수집
# ============================================

with st.spinner("뉴스 수집 중..."):

    articles = fetch_news(selected_media)

# ============================================
# 기사 없을 때 안내
# ============================================

if len(articles) == 0:

    st.info("현재 수집된 기후변화 관련 기사가 없습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

# ============================================
# 데이터프레임 생성
# ============================================

data = []

all_words = []
positive_words_found = []
negative_words_found = []

for article in articles:

    combined_text = f"{article['title']} {article['summary']}"

    sentiment, pos_count, neg_count = analyze_sentiment(combined_text)

    words = clean_text(combined_text)

    all_words.extend(words)

    for word in words:

        if word in [w.lower() for w in POSITIVE_WORDS]:
            positive_words_found.append(word)

        if word in [w.lower() for w in NEGATIVE_WORDS]:
            negative_words_found.append(word)

    data.append({
        "언론사": article["media"],
        "제목": article["title"],
        "감성": sentiment,
        "링크": article["link"]
    })

df = pd.DataFrame(data)

# ============================================
# 감성 통계
# ============================================

st.subheader("📊 감성 분석 결과")

sentiment_counts = df["감성"].value_counts().reset_index()
sentiment_counts.columns = ["감성", "개수"]

fig = px.bar(
    sentiment_counts,
    x="감성",
    y="개수",
    color="감성",
    text="개수",
    color_discrete_map={
        "긍정": "green",
        "부정": "red",
        "중립": "gray"
    }
)

st.plotly_chart(fig, use_container_width=True)

# ============================================
# 긍정/부정 연관어
# ============================================

col1, col2 = st.columns(2)

with col1:

    st.subheader("😊 긍정 연관어")

    positive_counter = Counter(positive_words_found)

    if positive_counter:
        for word, count in positive_counter.most_common(10):
            st.markdown(f"- {word} ({count})")
    else:
        st.write("긍정 단어 없음")

with col2:

    st.subheader("😢 부정 연관어")

    negative_counter = Counter(negative_words_found)

    if negative_counter:
        for word, count in negative_counter.most_common(10):
            st.markdown(f"- {word} ({count})")
    else:
        st.write("부정 단어 없음")

# ============================================
# 워드클라우드
# ============================================

st.subheader("☁️ 워드클라우드")

word_freq = Counter(all_words)

if len(word_freq) > 0:

    try:

        wc = WordCloud(
            width=1000,
            height=500,
            background_color="white",
            font_path=FONT_PATH,
            colormap="viridis"
        ).generate_from_frequencies(word_freq)

        fig_wc, ax = plt.subplots(figsize=(12, 6))

        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")

        st.pyplot(fig_wc)

    except Exception:
        st.warning("워드클라우드 생성 중 오류 발생")

# ============================================
# 기사 목록
# ============================================

st.subheader("📰 수집 기사 목록")

for idx, row in df.iterrows():

    with st.expander(f"[{row['감성']}] {row['제목']}"):

        st.write(f"언론사: {row['언론사']}")
        st.markdown(f"[기사 링크 바로가기]({row['링크']})")
