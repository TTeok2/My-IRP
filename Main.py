import streamlit as st
import pandas as pd
import altair as alt
import os

st.set_page_config(page_title="IRP 수익률 대시보드", layout="wide")
st.title("📊 IRP 수익률 비교 대시보드 (2025-1분기)")

# ------------------ 파일 로딩 함수 ------------------
@st.cache_data
def load_excel_data(uploaded_file=None):
    if uploaded_file:
        try:
            return pd.read_excel(uploaded_file, header=7)
        except Exception as e:
            st.error(f"파일을 불러오는 데 실패했습니다: {e}")
            return None
    else:
        # __file__ 기준 현재 디렉토리에서 파일 찾기
        default_path = os.path.join(os.path.dirname(__file__), "2025-1 IRP 수익률.xlsx")
        st.text(f"📁 기본 파일 경로: {default_path}")
        if os.path.exists(default_path):
            try:
                return pd.read_excel(default_path, header=7)
            except Exception as e:
                st.error(f"기본 파일을 불러오는 데 실패했습니다: {e}")
                return None
        else:
            st.warning("기본 파일이 존재하지 않습니다. 파일을 업로드해주세요.")
            return None

# ------------------ 데이터 전처리 함수 ------------------
def preprocess_data(df):
    df.columns = ["사업자명", "원리금구분", "적립금", "1년수익률", "3년수익률", "5년수익률", "7년수익률", "10년수익률"]
    df = df[~df["적립금"].astype(str).str.contains("적립금|수익률|NaN", na=False)]

    numeric_cols = ["적립금", "1년수익률", "3년수익률", "5년수익률", "7년수익률", "10년수익률"]
    for col in numeric_cols:
        df[col] = (
            df[col].astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
            .replace("-", pd.NA)
        )
        try:
            df[col] = df[col].astype(float)
        except ValueError:
            st.warning(f"{col} 열에 숫자가 아닌 값이 포함되어 있어 변환에서 제외되었습니다.")

    df = df[
        (df["1년수익률"].notna()) &
        (~df["원리금구분"].str.contains("합계|자사계열사|기타", na=False))
    ]
    return df

# ------------------ 파일 업로드 ------------------
st.sidebar.header("📁 파일 업로드")
uploaded_file = st.sidebar.file_uploader("IRP 수익률 Excel 파일 업로드", type=["xlsx"])

raw_df = load_excel_data(uploaded_file)
if raw_df is not None:
    df = preprocess_data(raw_df)

    # ------------------ 시각화 ------------------
    st.subheader("1. 상품 유형별 1년 수익률 분포")
    box = alt.Chart(df).mark_boxplot(extent="min-max").encode(
        x=alt.X("원리금구분:N", title="상품 유형"),
        y=alt.Y("1년수익률:Q", title="1년 수익률 (%)"),
        color="원리금구분:N"
    ).properties(width=600, height=400)
    st.altair_chart(box, use_container_width=True)

    st.subheader("2. 사업자별 평균 수익률")
    avg_df = df.groupby("사업자명")["1년수익률"].mean().reset_index().sort_values(by="1년수익률", ascending=False)
    bar = alt.Chart(avg_df).mark_bar().encode(
        x=alt.X("사업자명:N", sort="-y", title="사업자명"),
        y=alt.Y("1년수익률:Q", title="평균 수익률 (%)"),
        tooltip=["사업자명", "1년수익률"]
    ).properties(width=700, height=400)
    st.altair_chart(bar, use_container_width=True)

    st.subheader("3. 상품 유형별 필터링")
    selected_type = st.selectbox("상품 유형 선택", options=df["원리금구분"].unique())
    filtered = df[df["원리금구분"] == selected_type]
    st.dataframe(filtered.sort_values(by="1년수익률", ascending=False), use_container_width=True)

else:
    st.info("파일을 불러올 수 없습니다. 기본 파일이 없거나 업로드되지 않았습니다.")
