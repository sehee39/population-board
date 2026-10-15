import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# 1. 스트림릿 페이지 기본 설정
# ==========================================
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="👨‍👩‍👧‍👦",
    layout="centered"
)

# 데이터 주소 설정
DATA_URL = "https://raw.githubusercontent.com/sehee39/population-board/main/population_ts_yearly_gender.zip"


# ==========================================
# 2. 데이터 로드 및 최신 연도 추출 함수
# ==========================================
@st.cache_data
def load_data():
    # pandas는 zip 파일 내부의 CSV를 자동으로 읽어옵니다.
    df = pd.read_csv(DATA_URL)
    
    # 데이터 중 가장 최신 연도만 선택
    latest_year = df["연도"].max()
    df_latest = df[df["연도"] == latest_year].copy()
    
    return df_latest, latest_year


# 메인 화면 제목 및 설명 (따뜻한 톤)
st.title("👨‍👩‍👧‍👦 우리 동네 인구 피라미드")
st.caption("우리 동네에는 어떤 연령대의 이웃들이 살고 있을까요? 궁금한 지역을 선택해 보세요.")

# 데이터 불러오기
with st.spinner("최신 인구 데이터를 불러오는 중입니다..."):
    df, year = load_data()

st.success(f"기준 연도: **{year}년** 최신 데이터 로드 완료!", icon="✨")
st.write("---")

# ==========================================
# 3. 지역 선택 드롭다운 (시도 -> 시군구 -> 동)
# ==========================================
col1, col2, col3 = st.columns(3)

# 1) 시·도 선택
with col1:
    sido_list = sorted(df["시도"].dropna().unique())
    selected_sido = st.selectbox("1. 시·도 선택", sido_list)

# 선택한 시·도에 해당하는 데이터 필터링
df_sido = df[df["시도"] == selected_sido]

# 2) 시·군·구 선택
with col2:
    sigungu_list = sorted(df_sido["시군구"].dropna().unique())
    selected_sigungu = st.selectbox("2. 시·군·구 선택", sigungu_list)

# 선택한 시·군·구에 해당하는 데이터 필터링
df_sigungu = df_sido[df_sido["시군구"] == selected_sigungu]

# 3) 읍·면·동 선택
with col3:
    dong_list = sorted(df_sigungu["동"].dropna().unique())
    selected_dong = st.selectbox("3. 읍·면·동 선택", dong_list)

# 최종 선택된 읍·면·동 행 데이터 추출
target_row = df_sigungu[df_sigungu["동"] == selected_dong]

# ==========================================
# 4. 인구 피라미드 및 지표 데이터 가공
# ==========================================
if not target_row.empty:
    row = target_row.iloc[0]
    
    # 나이 라벨 리스트 생성 (0세, 1세, ..., 99세, 100세 이상)
    ages = [f"{i}세" for i in range(100)] + ["100세 이상"]
    
    male_pop = []
    female_pop = []
    
    # 나이별 남/여 인구수 가져오기
    for age in ages:
        m_col = f"남_{age}"
        f_col = f"여_{age}"
        
        # 열이 존재하면 값을 가져오고, 없으면 0으로 처리
        m_val = row[m_col] if m_col in row else 0
        f_val = row[f_col] if f_col in row else 0
        
        male_pop.append(m_val)
        female_pop.append(f_val)
    
    # 연령별 총 인구수 (남 + 여)
    total_pop_by_age = [m + f for m, f in zip(male_pop, female_pop)]
    total_pop = sum(total_pop_by_age)
    
    # --- 주요 지표 계산 ---
    if total_pop > 0:
        # 1) 평균 연령 계산 (0~99세는 해당 나이, 100세 이상은 100세로 계산)
        age_values = list(range(100)) + [100]
        avg_age = sum(a * p for a, p in zip(age_values, total_pop_by_age)) / total_pop
        
        # 2) 고령화율 계산 (65세 이상 인구 비율, 인덱스 65부터 끝까지)
        senior_pop = sum(total_pop_by_age[65:])
        aging_rate = (senior_pop / total_pop) * 100
        
        # 3) 유소년 비율 계산 (0~14세 인구 비율, 인덱스 0~14)
        child_pop = sum(total_pop_by_age[:15])
        child_rate = (child_pop / total_pop) * 100
    else:
        avg_age = 0.0
        aging_rate = 0.0
        child_rate = 0.0

    # ==========================================
    # 5. 지표 카드 3개 표시 (그래프 위)
    # ==========================================
    st.write("### 📊 주요 인구 지표")
    m_col1, m_col2, m_col3 = st.columns(3)
    
    # 카드 1: 총인구
    with m_col1:
        st.metric(label="👥 총인구", value=f"{total_pop:,} 명")
        
    # 카드 2: 평균 연령
    with m_col2:
        st.metric(label="🎂 평균 연령", value=f"{avg_age:.1f} 세")
        
    # 카드 3: 고령화율 (20% 초과 시 초고령사회 주의 표시)
    with m_col3:
        if aging_rate >= 20.0:
            st.metric(
                label="⚠️ 고령화율 (초고령)",
                value=f"{aging_rate:.1f} %",
                delta="초고령사회 (20% 이상)",
                delta_color="inverse"  # 빨간색/주의 톤으로 표시
            )
        else:
            st.metric(
                label="👴 고령화율",
                value=f"{aging_rate:.1f} %",
                delta="65세 이상 비율",
                delta_color="off"
            )

    st.write("")  # 여백

    # ==========================================
    # 6. Plotly 가로 막대 그래프 생성 (인구 피라미드)
    # ==========================================
    # 남성 인구는 피라미드 왼쪽에 배치하기 위해 음수로 변환
    male_pop_neg = [-val for val in male_pop]
    
    fig = go.Figure()
    
    # 남성 데이터 (왼쪽, 음수 값)
    fig.add_trace(go.Bar(
        y=ages,
        x=male_pop_neg,
        name='남성',
        orientation='h',
        marker=dict(color='#5B8FF9'),  # 부드러운 파란색
        hoverinfo='text',
        hovertext=[f"{age} 남성: {val:,}명" for age, val in zip(ages, male_pop)]
    ))
    
    # 여성 데이터 (오른쪽, 양수 값)
    fig.add_trace(go.Bar(
        y=ages,
        x=female_pop,
        name='여성',
        orientation='h',
        marker=dict(color='#F6868A'),  # 따뜻한 핑크/코랄색
        hoverinfo='text',
        hovertext=[f"{age} 여성: {val:,}명" for age, val in zip(ages, female_pop)]
    ))
    
    # 축의 최댓값을 계산하여 x축 범위를 좌우 대칭으로 설정
    max_val = max(max(male_pop), max(female_pop)) if total_pop > 0 else 10
    x_range_max = max_val * 1.15 if max_val > 0 else 10

    fig.update_layout(
        title=dict(
            text=f"📍 {selected_sido} {selected_sigungu} {selected_dong} 인구 피라미드 ({year}년)",
            font=dict(size=18),
            x=0.5,
            xanchor='center'
        ),
        barmode='overlay',  # 남/여 막대가 중앙 기준으로 갈라지도록 설정
        bargap=0.1,
        # 세로축(y축) 설정: 0세가 맨 아래, 100세 이상이 맨 위가 되도록 카테고리 순서 고정
        yaxis=dict(
            title="나이",
            type="category",
            categoryorder="array",     # 배열 순서대로 정렬
            categoryarray=ages,        # 0세부터 100세 이상까지 순서대로 고정
            showgrid=True,
            gridcolor="#E5E5E5"
        ),
        # 가로축(x축) 설정
        xaxis=dict(
            title="인구수 (명)",
            range=[-x_range_max, x_range_max],
            showgrid=True,
            gridcolor="#E5E5E5"
        ),
        template="plotly_white",
        height=900,  # 0~100세 이상까지 잘 보이도록 높이 충분히 설정
        legend=dict(x=0.85, y=1.05, orientation="h")
    )
    
    # x축 눈금의 음수(-) 표시를 양수로 변환하여 깔끔하게 표시
    tick_step = max(1, int(x_range_max / 4))
    ticks = list(range(-int(x_range_max), int(x_range_max) + 1, tick_step))
    fig.update_xaxes(
        tickvals=ticks,
        ticktext=[f"{abs(t):,}" for t in ticks]
    )

    # Streamlit 화면에 그래프 출력
    st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # 7. 피라미드 아래 한 줄 자동 설명
    # ==========================================
    st.write("---")
    st.subheader("💡 이 동네는 아이가 많은 편인가요, 어르신이 많은 편인가요?")
    
    # 조건에 따라 한 줄 설명 문구 자동 생성
    if aging_rate >= 20.0:
        summary_text = (
            f"이 동네는 **어르신(65세 이상) 비율이 {aging_rate:.1f}%**로 높은 "
            f"**초고령 지역**에 해당합니다. 실버 복지와 어르신 편의시설이 중요한 동네입니다."
        )
        box_type = st.warning
    elif child_rate > aging_rate:
        summary_text = (
            f"이 동네는 **어린이(0~14세) 비율이 {child_rate:.1f}%**로 어르신 비율({aging_rate:.1f}%)보다 높아 "
            f"**아이들이 상대적으로 많은 활기찬 동네**입니다."
        )
        box_type = st.info
    elif abs(aging_rate - child_rate) <= 5.0:
        summary_text = (
            f"이 동네는 **어린이({child_rate:.1f}%)와 어르신({aging_rate:.1f}%)의 비율이 비슷하게 균형**을 이루고 있는 동네입니다."
        )
        box_type = st.info
    else:
        summary_text = (
            f"이 동네는 **청장년층 중심의 경제활동 인구** 비율이 높으며, "
            f"어르신 비율은 **{aging_rate:.1f}%** 수준입니다."
        )
        box_type = st.info

    # 한 줄 설명 박스 출력
    box_type(summary_text, icon="🏠")
