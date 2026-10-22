import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="전국 고령화 단계구분도", layout="wide")

st.title("📊 2026년 시군구별 고령화 단계구분도")
st.markdown("전국 읍·면·동 인구 데이터를 시군구(5자리 코드) 단위로 집계하여 65세 이상 인구 비율을 시각화합니다.")

# ----------------------------------------------------
# 1. 데이터 로드 (캐싱 적용)
# ----------------------------------------------------
@st.cache_data
def load_population_data():
    url = "https://raw.githubusercontent.com/sehee39/population-board//main/population_ts_yearly_gender.zip"
    df = pd.read_csv(url, encoding="utf-8")
    return df

@st.cache_data
def load_geojson():
    geojson_url = "https://raw.githubusercontent.com/sehee39/population-board//main/sigungu_kr.geojson"
    res = requests.get(geojson_url)
    return res.json()

with st.spinner("데이터 및 GeoJSON 지도를 불러오는 중입니다..."):
    df_raw = load_population_data()
    geojson_data = load_geojson()

# ----------------------------------------------------
# 2. 데이터 전처리
# ----------------------------------------------------
# 2026년 데이터 필터링
df_2026 = df_raw[df_raw["연도"] == 2026].copy()

# '코드' 열을 문자열로 변환 후 앞 5자리(시군구 코드) 추출
df_2026["코드"] = df_2026["코드"].astype(str).str.zfill(10).str[:5]

# '계_'로 시작하는 전체 연령대 열 추출
total_cols = [col for col in df_2026.columns if col.startswith("계_")]

# 65세 이상 열 추출 ('계_65세' ~ '계_100세 이상')
def is_over_65(col_name):
    age_str = col_name.replace("계_", "").replace("세", "").replace(" 이상", "")
    try:
        return int(age_str) >= 65
    except ValueError:
        return False

senior_cols = [col for col in total_cols if is_over_65(col)]

# 시군구(코드 5자리) 단위로 그룹화하여 합산
df_grouped = df_2026.groupby("코드")[total_cols].sum().reset_index()

# 전체 인구수 및 65세 이상 인구수 계산
df_grouped["전체인구"] = df_grouped[total_cols].sum(axis=1)
df_grouped["고령인구"] = df_grouped[senior_cols].sum(axis=1)

# 고령화율(%) 계산
df_grouped["고령화율"] = (df_grouped["고령인구"] / df_grouped["전체인구"]) * 100
df_grouped["고령화율"] = df_grouped["고령화율"].round(2)

# GeoJSON 데이터에서 시군구 코드 - 시군구 이름 매핑 생성
sigungu_map = {}
for feature in geojson_data["features"]:
    props = feature["properties"]
    sigungu_map[str(props["코드"])] = f"{props.get('시도', '')} {props.get('시군구', '')}".strip()

df_grouped["시군구명"] = df_grouped["코드"].map(sigungu_map)

# ----------------------------------------------------
# 3. Plotly 단계구분도 시각화
# ----------------------------------------------------
fig = px.choropleth_mapbox(
    df_grouped,
    geojson=geojson_data,
    locations="코드",
    featureidkey="properties.코드",
    color="고령화율",
    color_continuous_scale="Reds",
    range_color=(0, df_grouped["고령화율"].max()),
    mapbox_style="white-bg",  # 배경 지도(타일) 없이 경계만 출력
    center={"lat": 35.9, "lon": 127.8},
    zoom=6,
    hover_name="시군구명",
    hover_data={
        "코드": True,
        "고령화율": ":.2f%",
        "전체인구": ":,",
        "고령인구": ":,"
    },
    labels={
        "고령화율": "고령화율(%)",
        "코드": "시군구 코드",
        "전체인구": "전체 인구수",
        "고령인구": "65세 이상 인구수"
    }
)

fig.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    height=750
)

st.plotly_chart(fig, use_container_width=True)

with st.expander("📌 시군구별 데이터 상세 보기"):
    st.dataframe(
        df_grouped[["코드", "시군구명", "전체인구", "고령인구", "고령화율"]]
        .sort_values(by="고령화율", ascending=False)
        .reset_index(drop=True),
        use_container_width=True
    )
