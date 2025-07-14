import streamlit as st
import pandas as pd
import altair as alt
import os

st.set_page_config(page_title="IRP 수익률 대시보드", layout="wide")
st.title("📊 IRP 수익률 비교 대시보드 (2025-1분기)")
st.caption("⚠️ 해당 페이지의 수치와 내용은 실제 상품 정보와 일부 차이가 있을 수 있으니 참고용으로 활용해주세요. IRP 투자에는 충분히 다양한 요소가 고려되어야 합니다. 해당 웹앱은 총 42개 퇴직연금사업자 대상 데이터를 기준으로 합니다.")

# ------------------ 파일 로딩 함수 ------------------
@st.cache_data
def load_excel_data(uploaded_file=None):
    default_path = os.path.join(os.path.dirname(__file__), "2025-1 IRP 수익률.xlsx")
    try:
        if uploaded_file:
            return pd.read_excel(uploaded_file, header=7)
        elif os.path.exists(default_path):
            return pd.read_excel(default_path, header=7)
        else:
            st.warning("기본 파일이 존재하지 않습니다. 파일을 업로드해주세요.")
            return None
    except Exception as e:
        st.error(f"파일을 불러오는 데 실패했습니다: {e}")
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

    if not fee_df.empty:
        df = df.merge(fee_df, on="사업자명", how="left")
        df["순효율"] = df["1년수익률"] - df["총비용부담률"]

    return df.reset_index(drop=True)

# ------------------ 파일 로딩 ------------------
raw_df = load_excel_data()
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
    avg_df = df.groupby("사업자명", as_index=False)[["1년수익률"]].mean().sort_values(by="1년수익률", ascending=False)
    bar = alt.Chart(avg_df).mark_bar().encode(
        x=alt.X("사업자명:N", sort="-y", title="사업자명"),
        y=alt.Y("1년수익률:Q", title="평균 수익률 (%)"),
        tooltip=["사업자명", "1년수익률"]
    ).properties(width=700, height=400)
    st.altair_chart(bar, use_container_width=True)

    if "총비용부담률" in df.columns:
        st.subheader("3. 수익률 vs 총비용부담률 산점도")
        st.markdown("""
            **※ 총비용부담률** = 당해연도 총 비용 ÷ 적립금  
            (총 비용 = 운용관리수수료 + 자산관리수수료 + 펀드총비용(운용보수, 판매보수 등))
        """)
        st.caption("📍 산점도에 표시된 사업자는 순효율 상위 5개 사업자입니다.")

        top5 = df.sort_values(by="순효율", ascending=False).head(5)
        top5_labels = alt.Chart(top5).mark_text(align='left', dx=7, dy=-7).encode(
            x="총비용부담률:Q",
            y="1년수익률:Q",
            text="사업자명"
        )

        scatter = alt.Chart(df).mark_circle(size=60).encode(
            x=alt.X("총비용부담률:Q", title="총비용부담률 (%)"),
            y=alt.Y("1년수익률:Q", title="1년 수익률 (%)"),
            color="원리금구분:N",
            tooltip=["사업자명", "1년수익률", "총비용부담률"]
        ).properties(width=700, height=400)

        st.altair_chart(scatter + top5_labels, use_container_width=True)

        st.subheader("4. 순효율(수익률 - 비용) 높은 사업자")
        st.caption("💡 순효율은 단순히 수익률에서 총비용부담률을 뺀 값으로, 실제 투자성과와 차이가 있을 수 있습니다.")
        eff_df = df[["사업자명", "원리금구분", "1년수익률", "총비용부담률", "순효율"]].dropna()
        top_eff = eff_df.sort_values(by="순효율", ascending=False)
        st.dataframe(top_eff.reset_index(drop=True), use_container_width=True)

    st.subheader("5. 상품/사업자별 필터링")
    col1, col2 = st.columns(2)
    selected_type = col1.selectbox("상품 유형 선택", options=df["원리금구분"].unique())
    selected_provider = col2.selectbox("사업자 선택", options=sorted(df["사업자명"].unique()))
    filtered = df[(df["원리금구분"] == selected_type) & (df["사업자명"] == selected_provider)]
    st.dataframe(filtered.sort_values(by="1년수익률", ascending=False).reset_index(drop=True), use_container_width=True)

    st.subheader("6. 수익률 추세 비교 (1년 vs 3년 vs 5년)")
    trend_mode = st.radio("비교 기준", ["사업자별", "상품유형별"], horizontal=True)

    if trend_mode == "사업자별":
        trend_df = df.groupby("사업자명", as_index=False)[["1년수익률", "3년수익률", "5년수익률"]].mean().dropna()
        trend_df = pd.melt(trend_df, id_vars="사업자명", value_vars=["1년수익률", "3년수익률", "5년수익률"],
                            var_name="수익률기간", value_name="수익률")
        trend_chart = alt.Chart(trend_df).mark_bar().encode(
            x=alt.X("사업자명:N", sort="-y", title="사업자명"),
            y=alt.Y("수익률:Q", title="수익률 (%)"),
            color="수익률기간:N",
            tooltip=["사업자명", "수익률기간", "수익률"]
        ).properties(width=800, height=400)
    else:
        trend_df = df.groupby("원리금구분", as_index=False)[["1년수익률", "3년수익률", "5년수익률"]].mean().dropna()
        trend_df = pd.melt(trend_df, id_vars="원리금구분", value_vars=["1년수익률", "3년수익률", "5년수익률"],
                            var_name="수익률기간", value_name="수익률")
        trend_chart = alt.Chart(trend_df).mark_bar().encode(
            x=alt.X("원리금구분:N", title="상품유형"),
            y=alt.Y("수익률:Q", title="수익률 (%)"),
            color="수익률기간:N",
            tooltip=["원리금구분", "수익률기간", "수익률"]
        ).properties(width=600, height=400)

    st.altair_chart(trend_chart, use_container_width=True)

else:
    st.info("파일을 불러올 수 없습니다. 기본 파일이 없거나 업로드되지 않았습니다.")
