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

# ------------------ 총비용부담률 데이터 로딩 ------------------
@st.cache_data
def load_fee_data():
    fee_path = os.path.join(os.path.dirname(__file__), "2024 총비용부담률.xlsx")
    if os.path.exists(fee_path):
        fee_df = pd.read_excel(fee_path, sheet_name=0, header=8)
        fee_df.columns = ["사업자명", "총비용부담률", "수수료합계", "운용관리", "자산관리", "펀드총비용"]
        fee_df = fee_df[["사업자명", "총비용부담률"]]
        fee_df["총비용부담률"] = pd.to_numeric(fee_df["총비용부담률"], errors="coerce")
        return fee_df
    else:
        st.warning("2024 총비용부담률 파일이 존재하지 않습니다.")
        return pd.DataFrame()

# ------------------ 데이터 전처리 함수 ------------------
def preprocess_data(df, fee_df):
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

    # 총비용부담률 병합
    if not fee_df.empty:
        df = df.merge(fee_df, on="사업자명", how="left")
        df["순효율"] = df["1년수익률"] - df["총비용부담률"]

    return df

# ------------------ 파일 업로드 ------------------
st.sidebar.header("📁 파일 업로드")
uploaded_file = st.sidebar.file_uploader("IRP 수익률 Excel 파일 업로드", type=["xlsx"])

raw_df = load_excel_data(uploaded_file)
fee_df = load_fee_data()

if raw_df is not None:
    df = preprocess_data(raw_df, fee_df)

    # ------------------ 시각화 ------------------
    st.subheader("1. 상품 유형별 1년 수익률 분포")
    box = alt.Chart(df).mark_boxplot(extent="min-max").encode(
        x=alt.X("원리금구분:N", title="상품 유형"),
        y=alt.Y("1년수익률:Q", title="1년 수익률 (%)"),
        color="원리금구분:N"
    ).properties(width=600, height=400)
    st.altair_chart(box, use_container_width=True)

    st.subheader("2. 사업자별 평균 수익률")
    avg_df = df.groupby("사업자명")[["1년수익률"]].mean().reset_index().sort_values(by="1년수익률", ascending=False)
    bar = alt.Chart(avg_df).mark_bar().encode(
        x=alt.X("사업자명:N", sort="-y", title="사업자명"),
        y=alt.Y("1년수익률:Q", title="평균 수익률 (%)"),
        tooltip=["사업자명", "1년수익률"]
    ).properties(width=700, height=400)
    st.altair_chart(bar, use_container_width=True)

    if "총비용부담률" in df.columns:
        st.subheader("3. 수익률 vs 총비용부담률 산점도")
        scatter = alt.Chart(df).mark_circle(size=60).encode(
            x=alt.X("총비용부담률:Q", title="총비용부담률 (%)"),
            y=alt.Y("1년수익률:Q", title="1년 수익률 (%)"),
            color="원리금구분:N",
            tooltip=["사업자명", "1년수익률", "총비용부담률"]
        ).properties(width=700, height=400)
        st.altair_chart(scatter, use_container_width=True)

        st.subheader("4. 순효율(수익률 - 비용) 높은 사업자")
        st.caption("💡 순효율은 단순히 수익률에서 총비용부담률을 뺀 값으로, 실제 투자성과와 차이가 있을 수 있습니다.")
        eff_df = df[["사업자명", "원리금구분", "1년수익률", "총비용부담률", "순효율"]].dropna()
        top_eff = eff_df.sort_values(by="순효율", ascending=False)
        st.dataframe(top_eff, use_container_width=True)

    st.subheader("5. 상품 유형별 필터링")
    selected_type = st.selectbox("상품 유형 선택", options=df["원리금구분"].unique())
    filtered = df[df["원리금구분"] == selected_type]
    st.dataframe(filtered.sort_values(by="1년수익률", ascending=False), use_container_width=True)

else:
    st.info("파일을 불러올 수 없습니다. 기본 파일이 없거나 업로드되지 않았습니다.")
