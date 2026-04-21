"""
SEQUOIA QUANTUM™ REAL ESTATE ENGINE v2.5
국토교통부 실거래가 API 기반 부동산 내재가치 분석 대시보드
Streamlit Cloud 단일 파일 배포용
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# 0. 페이지 설정 & 전체 스타일
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SEQUOIA QUANTUM™ RE v2.5",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Noto+Sans+KR:wght@300;400;700&display=swap');

html, body, [class*="css"]  { font-family:'Noto Sans KR',sans-serif; background:#0D0F17; color:#C8D0E0; }
.stApp                       { background:#0D0F17; }
section[data-testid="stSidebar"] { background:#080A11 !important; border-right:1px solid #1A1E30; }

[data-testid="metric-container"] {
    background:linear-gradient(135deg,#111420,#181C2C);
    border:1px solid #232840; border-radius:8px; padding:14px 18px;
}
[data-testid="metric-container"] label          { color:#556080!important; font-family:'Share Tech Mono',monospace!important; font-size:.7rem!important; letter-spacing:.1em; }
[data-testid="stMetricValue"]                   { font-family:'Share Tech Mono',monospace!important; font-size:1.4rem!important; color:#E0EAFF!important; }
[data-testid="stMetricDelta"] svg               { display:none; }
[data-testid="stMetricDelta"]                   { font-size:.75rem!important; }

.stButton>button { background:linear-gradient(135deg,#162840,#0D1E30); color:#6AAEE0; border:1px solid #254870; font-family:'Share Tech Mono',monospace; letter-spacing:.06em; border-radius:6px; }
.stButton>button:hover { background:linear-gradient(135deg,#1E3A58,#152E48); color:#90C8FF; border-color:#3A78B0; }

hr { border-color:#1A1E30!important; }
.block-container { padding-top:1.8rem; }

.mono  { font-family:'Share Tech Mono',monospace; }
.badge-buy  { background:#091A10; color:#2ECC71; border:1px solid #2ECC71; border-radius:4px; padding:3px 12px; font-size:.72rem; font-family:'Share Tech Mono',monospace; }
.badge-hold { background:#1A1500; color:#F1C40F; border:1px solid #F1C40F; border-radius:4px; padding:3px 12px; font-size:.72rem; font-family:'Share Tech Mono',monospace; }
.badge-sell { background:#1A0A0A; color:#E74C3C; border:1px solid #E74C3C; border-radius:4px; padding:3px 12px; font-size:.72rem; font-family:'Share Tech Mono',monospace; }
.badge-warn { background:#1A1000; color:#E67E22; border:1px solid #E67E22; border-radius:4px; padding:3px 12px; font-size:.72rem; font-family:'Share Tech Mono',monospace; }

.risk-ok       { background:#081510; border-left:3px solid #2ECC71; padding:10px 14px; border-radius:4px; margin:6px 0; font-size:.82rem; }
.risk-warn     { background:#150F00; border-left:3px solid #E67E22; padding:10px 14px; border-radius:4px; margin:6px 0; font-size:.82rem; }
.risk-critical { background:#150505; border-left:3px solid #E74C3C; padding:10px 14px; border-radius:4px; margin:6px 0; font-size:.82rem; }

.section-label { font-family:'Share Tech Mono',monospace; font-size:.68rem; letter-spacing:.14em; color:#3A5880; text-transform:uppercase; margin-bottom:2px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 1. 법정동 코드 참조 테이블 (주요 서울 자치구)
# ─────────────────────────────────────────────────────────────
LAWD_MAP = {
    "강남구": "11680", "서초구": "11650", "송파구": "11710", "강동구": "11740",
    "성동구": "11200", "광진구": "11215", "마포구": "11440", "용산구": "11170",
    "영등포구": "11560", "동작구": "11590", "관악구": "11620", "강서구": "11500",
    "양천구": "11470", "구로구": "11530", "금천구": "11545", "동대문구": "11230",
    "중랑구": "11260", "성북구": "11290", "강북구": "11305", "도봉구": "11320",
    "노원구": "11350", "은평구": "11380", "서대문구": "11410", "종로구": "11110",
    "중구": "11140", "중구(인천)": "28110", "수원시": "41111", "성남시": "41131",
    "고양시": "41281", "용인시": "41461", "부천시": "41190", "안양시": "41171",
    "직접 입력": "CUSTOM",
}


# ─────────────────────────────────────────────────────────────
# 2. 국토부 API 데이터 수집
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_molit_month(service_key: str, lawd_cd: str, ym: str) -> list:
    url = "http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTrade"
    params = {"serviceKey": service_key, "LAWD_CD": lawd_cd, "DEAL_YMD": ym, "numOfRows": 1000, "pageNo": 1}
    try:
        resp = requests.get(url, params=params, timeout=12)
        root = ET.fromstring(resp.content)
        code = root.findtext(".//resultCode", "")
        if code not in ("00", "0000", ""):
            return []
        records = []
        for item in root.findall(".//item"):
            try:
                price_raw = (item.findtext("dealAmount") or "0").replace(",", "").strip()
                records.append({
                    "단지명":   (item.findtext("aptNm") or "").strip(),
                    "전용면적": float(item.findtext("excluUseAr") or 0),
                    "거래금액": int(price_raw) if price_raw else 0,
                    "년":       int(item.findtext("dealYear") or 0),
                    "월":       int(item.findtext("dealMonth") or 0),
                    "일":       int(item.findtext("dealDay") or 1),
                    "층":       int(item.findtext("floor") or 0),
                    "건축년도": int(item.findtext("buildYear") or 0),
                })
            except Exception:
                continue
        return records
    except Exception:
        return []


def load_data_api(service_key: str, lawd_cd: str, months: int = 60) -> tuple[pd.DataFrame, list]:
    all_records, errors = [], []
    progress = st.progress(0, text="국토부 API 수집 중...")
    now = datetime.now()
    for i in range(months):
        target = now - timedelta(days=30 * i)
        ym = target.strftime("%Y%m")
        recs = fetch_molit_month(service_key, lawd_cd, ym)
        if not recs:
            errors.append(ym)
        all_records.extend(recs)
        progress.progress((i + 1) / months, text=f"수집 중... {ym}")
    progress.empty()

    if not all_records:
        return pd.DataFrame(), errors

    df = pd.DataFrame(all_records)
    df = df[df["거래금액"] > 0]
    df["날짜"] = pd.to_datetime(
        df[["년", "월", "일"]].rename(columns={"년": "year", "월": "month", "일": "day"}),
        errors="coerce"
    )
    df = df.dropna(subset=["날짜"]).drop_duplicates(
        subset=["날짜", "단지명", "전용면적", "거래금액"]
    ).sort_values("날짜").reset_index(drop=True)
    return df, errors


def load_data_csv(uploaded_file) -> pd.DataFrame:
    """
    CSV 컬럼: 단지명, 전용면적, 거래금액(만원), 년, 월, 일
    """
    df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
    required = {"단지명", "전용면적", "거래금액", "년", "월"}
    if not required.issubset(df.columns):
        st.error(f"CSV 필수 컬럼 누락: {required - set(df.columns)}")
        return pd.DataFrame()
    df["일"] = df.get("일", 1).fillna(1).astype(int)
    df["날짜"] = pd.to_datetime(
        df[["년", "월", "일"]].rename(columns={"년": "year", "월": "month", "일": "day"}),
        errors="coerce"
    )
    return df.dropna(subset=["날짜"]).sort_values("날짜").reset_index(drop=True)


# ─────────────────────────────────────────────────────────────
# 3. 분석 엔진
# ─────────────────────────────────────────────────────────────
def make_monthly(df: pd.DataFrame, apt_filter: str, area_min: float, area_max: float) -> pd.DataFrame:
    """단지·면적 필터 → 월별 중위가 집계"""
    d = df.copy()
    if apt_filter:
        d = d[d["단지명"].str.contains(apt_filter, na=False)]
    d = d[(d["전용면적"] >= area_min) & (d["전용면적"] <= area_max)]
    if d.empty:
        return pd.DataFrame()

    d["YM"] = d["날짜"].dt.to_period("M")
    monthly = (
        d.groupby("YM")
         .agg(월중위가=("거래금액", "median"), 거래건수=("거래금액", "count"))
         .reset_index()
    )
    monthly["날짜"] = monthly["YM"].dt.to_timestamp()
    monthly = monthly.sort_values("날짜").reset_index(drop=True)
    monthly["60MA"] = monthly["월중위가"].rolling(60, min_periods=3).mean()
    monthly["이격도"] = (monthly["월중위가"] / monthly["60MA"] * 100).round(1)
    return monthly


def signal(disparity: float) -> tuple:
    if disparity < 95:   return "강력 매수", "buy",  "#2ECC71"
    if disparity < 110:  return "매수 관심", "buy",  "#27AE60"
    if disparity < 120:  return "적정 구간", "hold", "#F1C40F"
    if disparity < 135:  return "고평가 주의","hold","#E67E22"
    if disparity < 150:  return "과열 경고", "sell", "#E74C3C"
    return               "버블 위험",  "sell", "#C0392B"


def dcf_value(monthly_rent_man: float, deposit_eok: float,
              base_rate: float, risk_premium: float,
              pir: float, pir_avg: float = 27.0) -> dict:
    r = (base_rate + risk_premium) / 100
    annual_rent_won = monthly_rent_man * 12 * 10_000
    base_eok = annual_rent_won / r / 1e8 + deposit_eok
    penalty = base_eok * 0.10 if pir > pir_avg * 1.2 else 0.0
    adjusted = base_eok - penalty
    yield_pct = (monthly_rent_man * 12) / ((adjusted - deposit_eok) * 1e4) * 100 if (adjusted - deposit_eok) > 0 else 0
    return {
        "base":     round(base_eok, 2),
        "adjusted": round(adjusted, 2),
        "penalty":  round(penalty, 2),
        "rate":     round(r * 100, 2),
        "yield":    round(yield_pct, 2),
    }


def dsr_limit(income_man: float, rate_pct: float, years: int = 30) -> dict:
    r = rate_pct / 100 / 12
    n = years * 12
    monthly_income = income_man * 10_000 / 12
    max_pay = monthly_income * 0.40
    loan_won = max_pay * (1 - (1 + r) ** (-n)) / r if r > 0 else max_pay * n
    return {"loan": round(loan_won / 1e8, 2), "monthly": round(max_pay / 10_000, 1)}


def momentum_eta(monthly_df: pd.DataFrame) -> dict:
    d = monthly_df.dropna(subset=["월중위가", "60MA", "이격도"])
    if len(d) < 6:
        return {"eta_date": None, "A": None, "trend": "데이터 부족"}

    r = d.tail(6).reset_index(drop=True)
    p_now  = r["월중위가"].tail(3).mean()
    p_prev = r["월중위가"].head(3).mean()
    dP = (p_now - p_prev) / p_prev * 100 if p_prev else 0

    v_now  = r["거래건수"].tail(3).mean() if "거래건수" in r else 1
    v_prev = r["거래건수"].head(3).mean() if "거래건수" in r else 1
    dV = (v_now - v_prev) / v_prev * 100 if v_prev else 0

    A = dP * 0.7 + dV * 0.3
    gap = 100.0 - float(d["이격도"].iloc[-1])

    if abs(A) < 0.05:
        return {"eta_date": None, "A": round(A, 3), "trend": "횡보 (추세 미약)", "dP": round(dP,2), "dV": round(dV,2)}

    eta_m = gap / A
    eta_date = datetime.now() + timedelta(days=30 * eta_m) if eta_m > 0 else None
    trend = ("하락 수렴 중" if A < 0 else "상승 이탈 중") if eta_m > 0 else ("이미 수렴" if A < 0 else "이미 이탈")
    return {"eta_date": eta_date, "eta_m": round(eta_m, 1) if eta_m > 0 else None,
            "A": round(A, 3), "trend": trend, "dP": round(dP, 2), "dV": round(dV, 2)}


def project_future(monthly_df: pd.DataFrame, ahead: int = 18) -> pd.DataFrame:
    d = monthly_df.dropna(subset=["월중위가"]).tail(12).copy()
    if len(d) < 4:
        return pd.DataFrame()
    d["t"] = np.arange(len(d))
    slope, intercept = np.polyfit(d["t"], d["월중위가"], 1)

    future = []
    last_date = d["날짜"].iloc[-1]
    last_t = len(d)
    for i in range(1, ahead + 1):
        future.append({
            "날짜": last_date + timedelta(days=30 * i),
            "예측가": round(intercept + slope * (last_t + i - 1)),
        })
    return pd.DataFrame(future)


def integrity_check(monthly_df: pd.DataFrame) -> dict:
    """최근 1개월 vs 3개월 중위가 괴리 무결성 검사"""
    d = monthly_df.dropna(subset=["월중위가"])
    if len(d) < 4:
        return {"status": "데이터 부족", "level": "warn"}
    last_1m = float(d["월중위가"].iloc[-1])
    avg_3m  = float(d["월중위가"].tail(4).iloc[:-1].mean())
    gap_pct = (last_1m - avg_3m) / avg_3m * 100 if avg_3m else 0
    if gap_pct < -10:
        return {"status": f"급락 감지 ({gap_pct:+.1f}%) — 하락 압력 강함", "level": "critical", "gap": gap_pct}
    if gap_pct < -3:
        return {"status": f"소폭 하락 압력 ({gap_pct:+.1f}%)", "level": "warn", "gap": gap_pct}
    if gap_pct > 10:
        return {"status": f"급등 감지 ({gap_pct:+.1f}%) — 과열 주의", "level": "warn", "gap": gap_pct}
    return {"status": f"정상 범위 ({gap_pct:+.1f}%)", "level": "ok", "gap": gap_pct}


# ─────────────────────────────────────────────────────────────
# 4. 차트
# ─────────────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="#0D0F17", plot_bgcolor="#0D0F17",
    font=dict(family="Share Tech Mono, monospace", color="#8090B0", size=11),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#2A2F45", borderwidth=1),
    xaxis=dict(gridcolor="#1A1E30", zerolinecolor="#1A1E30"),
    yaxis=dict(gridcolor="#1A1E30", zerolinecolor="#1A1E30"),
)


def chart_price(monthly_df: pd.DataFrame, future_df: pd.DataFrame,
                eta_info: dict, apt_name: str) -> go.Figure:
    fig = go.Figure()

    # 실거래 월중위가
    fig.add_trace(go.Scatter(
        x=monthly_df["날짜"], y=monthly_df["월중위가"],
        name="월중위가(실거래)", mode="lines+markers",
        line=dict(color="#4A90D9", width=2),
        marker=dict(size=4, color="#4A90D9"),
    ))

    # 60MA
    fig.add_trace(go.Scatter(
        x=monthly_df["날짜"], y=monthly_df["60MA"],
        name="60월선(5년 평균)", mode="lines",
        line=dict(color="#F39C12", width=2, dash="dot"),
    ))

    # 미래 예측 (점선)
    if not future_df.empty:
        # 연결용 브릿지
        last_row = monthly_df.dropna(subset=["월중위가"]).tail(1)
        bridge_x = list(last_row["날짜"]) + list(future_df["날짜"])
        bridge_y = list(last_row["월중위가"]) + list(future_df["예측가"])
        fig.add_trace(go.Scatter(
            x=bridge_x, y=bridge_y,
            name="회귀 예측(점선)", mode="lines",
            line=dict(color="#9B59B6", width=1.5, dash="dash"),
        ))

    # ETA 수직선
    if eta_info.get("eta_date"):
        fig.add_vline(
            x=eta_info["eta_date"].timestamp() * 1000,
            line=dict(color="#2ECC71", width=1, dash="dot"),
            annotation_text=f"  60MA 수렴 예상: {eta_info['eta_date'].strftime('%Y.%m')}",
            annotation_font=dict(color="#2ECC71", size=10),
        )

    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text=f"📈  {apt_name}  실거래 추세 & 미래 예측", font=dict(color="#7BB8F0", size=14)),
        yaxis_title="거래금액 (만원)",
        height=380,
    )
    return fig


def chart_disparity(monthly_df: pd.DataFrame) -> go.Figure:
    d = monthly_df.dropna(subset=["이격도"])
    fig = go.Figure()

    colors = ["#2ECC71" if v < 110 else "#F1C40F" if v < 130 else "#E74C3C"
              for v in d["이격도"]]

    fig.add_trace(go.Bar(
        x=d["날짜"], y=d["이격도"],
        name="이격도", marker_color=colors, opacity=0.8,
    ))
    fig.add_hline(y=100, line=dict(color="#4A90D9", width=1, dash="dot"),
                  annotation_text="  60MA 기준선(100%)",
                  annotation_font=dict(color="#4A90D9", size=10))
    fig.add_hline(y=120, line=dict(color="#E67E22", width=1, dash="dot"))
    fig.add_hline(y=150, line=dict(color="#E74C3C", width=1, dash="dot"))

    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="📊  60월선 이격도 (%)", font=dict(color="#7BB8F0", size=13)),
        yaxis_title="이격도 (%)",
        height=260,
    )
    return fig


def chart_scenario(loan_eok: float, cash_eok: float, rate_pct: float) -> go.Figure:
    rates = [rate_pct - 1.5, rate_pct - 0.5, rate_pct, rate_pct + 0.5, rate_pct + 1.5]
    payments = []
    for r in rates:
        r_m = r / 100 / 12
        n = 30 * 12
        p = loan_eok * 1e8 * r_m / (1 - (1 + r_m) ** (-n)) / 10_000 if r_m > 0 else 0
        payments.append(round(p, 1))

    bar_colors = ["#2ECC71" if r <= rate_pct else "#E74C3C" for r in rates]
    fig = go.Figure(go.Bar(
        x=[f"{r:.1f}%" for r in rates], y=payments,
        marker_color=bar_colors, text=[f"{p}만" for p in payments],
        textposition="outside", textfont=dict(color="#C8D0E0", size=10),
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="💰  금리 시나리오별 월 상환액 (만원)", font=dict(color="#7BB8F0", size=13)),
        yaxis_title="월 상환액 (만원)",
        height=260,
    )
    return fig


# ─────────────────────────────────────────────────────────────
# 5. 사이드바 입력
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="mono" style="color:#4A90D9;font-size:.8rem;letter-spacing:.12em;">PRINCIPAL ARCHITECT</p>', unsafe_allow_html=True)
    st.markdown("### 🏗️ SEQUOIA QUANTUM™")
    st.caption("RE Engine v2.5")
    st.divider()

    # ── 데이터 소스 ──
    st.markdown('<p class="section-label">📡 데이터 소스</p>', unsafe_allow_html=True)
    data_mode = st.radio("", ["국토부 API", "CSV 업로드"], horizontal=True, label_visibility="collapsed")

    service_key = ""
    uploaded_csv = None

    if data_mode == "국토부 API":
        service_key = st.text_input("API 서비스 키", type="password", placeholder="발급받은 키를 입력하세요")
        region_name = st.selectbox("지역 (법정동 코드)", list(LAWD_MAP.keys()))
        if region_name == "직접 입력":
            lawd_cd = st.text_input("법정동 코드 (5자리)", "11200")
        else:
            lawd_cd = LAWD_MAP[region_name]
        fetch_months = st.slider("수집 기간 (개월)", 12, 60, 36, step=6)
    else:
        uploaded_csv = st.file_uploader("CSV 파일 업로드", type=["csv"])
        st.caption("필수 컬럼: 단지명, 전용면적, 거래금액(만원), 년, 월")

    st.divider()

    # ── 단지·면적 필터 ──
    st.markdown('<p class="section-label">🔍 단지 필터</p>', unsafe_allow_html=True)
    apt_name = st.text_input("단지명 (일부 포함)", placeholder="예) 센트라스")
    col_a, col_b = st.columns(2)
    area_min = col_a.number_input("면적 최소(㎡)", value=59.0, step=1.0)
    area_max = col_b.number_input("면적 최대(㎡)", value=85.0, step=1.0)

    st.divider()

    # ── 재무 입력 ──
    st.markdown('<p class="section-label">💼 아키텍트 재무 정보</p>', unsafe_allow_html=True)
    cash       = st.number_input("가용 자산 (억)", value=5.0, step=0.5)
    income_man = st.number_input("연봉 (만원)", value=8000, step=500)
    rate       = st.slider("적용 금리 (%)", 2.0, 9.0, 4.5, step=0.1)

    st.divider()

    # ── DCF 입력 ──
    st.markdown('<p class="section-label">📐 DCF 가치 입력</p>', unsafe_allow_html=True)
    monthly_rent = st.number_input("예상 월세 (만원)", value=150, step=10)
    deposit      = st.number_input("보증금 (억)", value=1.0, step=0.5)
    risk_prem    = st.slider("리스크 프리미엄 (%)", 0.5, 3.0, 1.5, step=0.25)
    pir          = st.number_input("단지 PIR (배수)", value=27.0, step=0.5, help="서울 평균 약 25~30")

    st.divider()
    run_btn = st.button("⚡ 퀀텀 엔진 가동", use_container_width=True)


# ─────────────────────────────────────────────────────────────
# 6. 메인 화면
# ─────────────────────────────────────────────────────────────
st.markdown('<p class="mono" style="font-size:1.5rem;color:#7BB8F0;letter-spacing:.04em;">📊 SEQUOIA QUANTUM™  REAL ESTATE ENGINE</p>', unsafe_allow_html=True)
st.markdown('<p class="mono" style="font-size:.72rem;color:#2A4060;letter-spacing:.14em;">INTRINSIC VALUE · MOMENTUM ANALYSIS · DSR FILTER · PREDICTIVE ETA</p>', unsafe_allow_html=True)
st.divider()

if not run_btn:
    st.info("👈 좌측 사이드바에서 설정을 완료한 후 **'퀀텀 엔진 가동'** 버튼을 누르세요.")
    st.stop()


# ─────────────────────────────────────────────────────────────
# 7. 데이터 로드
# ─────────────────────────────────────────────────────────────
raw_df = pd.DataFrame()

with st.spinner("데이터 수집 중..."):
    if data_mode == "국토부 API":
        if not service_key:
            st.error("❌ API 서비스 키를 입력해 주세요.")
            st.stop()
        raw_df, api_errors = load_data_api(service_key, lawd_cd, fetch_months)
        if api_errors:
            st.caption(f"⚠️ 데이터 없는 월: {len(api_errors)}개월 (정상 범위)")
    else:
        if uploaded_csv is None:
            st.error("❌ CSV 파일을 업로드해 주세요.")
            st.stop()
        raw_df = load_data_csv(uploaded_csv)

if raw_df.empty:
    st.error("❌ 수집된 데이터가 없습니다. 단지명 필터를 비우거나 지역/날짜 범위를 확인하세요.")
    st.stop()

# 단지·면적 필터 → 월별 집계
monthly_df = make_monthly(raw_df, apt_name, area_min, area_max)
if monthly_df.empty:
    st.error(f"❌ 단지명 '{apt_name}' + 면적 {area_min}~{area_max}㎡ 조건에 해당하는 거래가 없습니다.")
    st.stop()

display_name = apt_name if apt_name else f"{region_name if data_mode=='국토부 API' else 'CSV'} 전체"


# ─────────────────────────────────────────────────────────────
# 8. 지표 계산
# ─────────────────────────────────────────────────────────────
last_row  = monthly_df.dropna(subset=["이격도"]).iloc[-1]
disp_val  = float(last_row["이격도"])
sig_label, sig_type, sig_color = signal(disp_val)

dcf       = dcf_value(monthly_rent, deposit, rate, risk_prem, pir)
dsr       = dsr_limit(income_man, rate)
budget    = cash + dsr["loan"]
eta       = momentum_eta(monthly_df)
future_df = project_future(monthly_df)
integrity = integrity_check(monthly_df)

current_price_man = int(last_row["월중위가"])
current_price_eok = round(current_price_man / 10_000, 2)
dcf_diff          = round(dcf["adjusted"] - current_price_eok, 2)
ma60_val          = round(float(last_row["60MA"]) / 10_000, 2) if not pd.isna(last_row["60MA"]) else None


# ─────────────────────────────────────────────────────────────
# 9. KPI 카드 (상단 5개)
# ─────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric(
        "현재 실거래가",
        f"{current_price_eok}억",
        f"60MA {ma60_val}억" if ma60_val else "",
    )
with c2:
    disp_delta = f"{sig_label}"
    delta_color = "normal" if sig_type == "hold" else ("off" if sig_type == "sell" else "normal")
    st.metric("60월선 이격도", f"{disp_val:.1f}%", disp_delta)
with c3:
    st.metric(
        "DCF 내재가치",
        f"{dcf['adjusted']}억",
        f"괴리 {dcf_diff:+.2f}억",
    )
with c4:
    st.metric(
        "DSR 40% 대출한도",
        f"{dsr['loan']}억",
        f"월 상환 {dsr['monthly']}만",
    )
with c5:
    if eta.get("eta_date"):
        eta_str = eta["eta_date"].strftime("%Y.%m")
        eta_delta = eta.get("trend", "")
    else:
        eta_str = "산출 불가"
        eta_delta = eta.get("trend", "")
    st.metric("60MA 수렴 예상", eta_str, eta_delta)

st.divider()


# ─────────────────────────────────────────────────────────────
# 10. 메인 차트 + 리스크 패널
# ─────────────────────────────────────────────────────────────
col_chart, col_risk = st.columns([3, 1])

with col_chart:
    st.plotly_chart(
        chart_price(monthly_df, future_df, eta, display_name),
        use_container_width=True
    )

with col_risk:
    st.markdown('<p class="section-label">🛡️ 리스크 판정</p>', unsafe_allow_html=True)

    # 이격도 신호
    badge_cls = f"badge-{sig_type}"
    st.markdown(f'<span class="{badge_cls}">{sig_label}</span>', unsafe_allow_html=True)
    st.caption(f"이격도 {disp_val:.1f}% | 기준: 120% 미만 매수, 150% 초과 버블")
    st.divider()

    # 무결성 검사
    ic = integrity
    ic_cls = f"risk-{ic['level']}"
    ic_icon = "✅" if ic["level"] == "ok" else "⚠️" if ic["level"] == "warn" else "🚨"
    st.markdown(f'<div class="{ic_cls}">{ic_icon} 데이터 무결성<br><b>{ic["status"]}</b></div>', unsafe_allow_html=True)
    st.divider()

    # 예산 vs 현재가
    st.markdown('<p class="section-label">💼 진입 가능성</p>', unsafe_allow_html=True)
    if current_price_eok <= budget:
        entry_cls = "risk-ok"
        entry_msg = f"✅ 진입 가능<br>예산 {budget:.1f}억 ≥ 현재가 {current_price_eok}억"
    else:
        entry_cls = "risk-critical"
        entry_msg = f"❌ 예산 부족<br>필요 {current_price_eok - budget:.1f}억 추가"
    st.markdown(f'<div class="{entry_cls}">{entry_msg}</div>', unsafe_allow_html=True)
    st.divider()

    # DCF 괴리
    st.markdown('<p class="section-label">📐 DCF 괴리</p>', unsafe_allow_html=True)
    if dcf_diff >= 0:
        st.markdown(f'<div class="risk-ok">✅ 저평가<br>내재가치 대비 <b>+{dcf_diff}억</b> 여유</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="risk-warn">⚠️ 고평가<br>내재가치 대비 <b>{dcf_diff}억</b> 초과</div>', unsafe_allow_html=True)

    if dcf["pir_exceeded"]:
        st.markdown(f'<div class="risk-warn">⚠️ PIR {pir} → DCF -10% 페널티 적용 ({dcf["penalty"]}억)</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 11. 이격도 바차트 + 시나리오 차트
# ─────────────────────────────────────────────────────────────
col_disp, col_scenario = st.columns(2)

with col_disp:
    st.plotly_chart(chart_disparity(monthly_df), use_container_width=True)

with col_scenario:
    st.plotly_chart(chart_scenario(dsr["loan"], cash, rate), use_container_width=True)


# ─────────────────────────────────────────────────────────────
# 12. 상세 분석 테이블
# ─────────────────────────────────────────────────────────────
with st.expander("📋 상세 수치 테이블 (최근 24개월)", expanded=False):
    show = monthly_df.tail(24).copy()
    show["거래금액(억)"] = (show["월중위가"] / 10_000).round(2)
    show["60MA(억)"]    = (show["60MA"] / 10_000).round(2)
    show["날짜"]         = show["날짜"].dt.strftime("%Y.%m")
    st.dataframe(
        show[["날짜", "거래금액(억)", "60MA(억)", "이격도", "거래건수"]].rename(
            columns={"이격도": "이격도(%)"}
        ),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("🔬 모멘텀 & DCF 계산 근거", expanded=False):
    col_m, col_d = st.columns(2)
    with col_m:
        st.markdown("**추세 가속도 (A)**")
        st.markdown(f"""
| 항목 | 값 |
|------|-----|
| 가격 변화율 ΔP | {eta.get('dP', 'N/A')} % |
| 거래량 변화율 ΔV | {eta.get('dV', 'N/A')} % |
| 가속도 A = ΔP×0.7 + ΔV×0.3 | **{eta.get('A', 'N/A')}** |
| 현재 이격도 | {disp_val:.1f} % |
| 60MA 수렴 예상 | {eta.get('eta_date').strftime('%Y.%m') if eta.get('eta_date') else '산출 불가'} |
""")
    with col_d:
        st.markdown("**하이브리드 DCF**")
        st.markdown(f"""
| 항목 | 값 |
|------|-----|
| 월세 기준 연수익 | {monthly_rent * 12:,} 만원 |
| 할인율 (금리+리스크) | {dcf['rate']} % |
| DCF 기초 가치 | {dcf['base']} 억 |
| PIR 페널티 | -{dcf['penalty']} 억 |
| **DCF 조정 가치** | **{dcf['adjusted']} 억** |
| 내재 수익률 | {dcf['yield']} % |
""")


# ─────────────────────────────────────────────────────────────
# 13. 푸터
# ─────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    '<p class="mono" style="font-size:.62rem;color:#2A3850;text-align:center;">'
    'SEQUOIA QUANTUM™ RE v2.5 · 본 분석은 투자 참고용이며 투자 권유가 아닙니다 · '
    f'데이터 기준일 {datetime.now().strftime("%Y.%m.%d")}</p>',
    unsafe_allow_html=True
)
