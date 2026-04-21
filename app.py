"""
SEQUOIA QUANTUM™ REAL ESTATE ENGINE v3.0
매매 / 전세 / 월세 통합 분석 대시보드
국토교통부 실거래가 API | Streamlit Cloud 단일 파일 배포용
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

# ══════════════════════════════════════════════════════════════
# 0. 페이지 설정 & 스타일
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="SEQUOIA QUANTUM™ RE v3.0",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Noto+Sans+KR:wght@300;400;700&display=swap');

html, body, [class*="css"]  { font-family:'Noto Sans KR',sans-serif; background:#F5F7FA; color:#1A2035; }
.stApp                       { background:#F5F7FA; }
section[data-testid="stSidebar"] { background:#FFFFFF !important; border-right:1px solid #DDE3EE; }

[data-testid="metric-container"] {
    background:#FFFFFF; border:1px solid #DDE3EE; border-radius:10px;
    padding:14px 18px; box-shadow:0 2px 8px rgba(0,0,0,0.06);
}
[data-testid="metric-container"] label { color:#7A8BAA!important; font-family:'Share Tech Mono',monospace!important; font-size:.66rem!important; letter-spacing:.08em; }
[data-testid="stMetricValue"]          { font-family:'Share Tech Mono',monospace!important; font-size:1.35rem!important; color:#1A2035!important; }
[data-testid="stMetricDelta"] svg      { display:none; }
[data-testid="stMetricDelta"]          { font-size:.74rem!important; }

.stButton>button { background:linear-gradient(135deg,#1A5CB8,#1248A0); color:#FFF; border:none; font-family:'Share Tech Mono',monospace; letter-spacing:.06em; border-radius:8px; font-weight:600; }
.stButton>button:hover { background:linear-gradient(135deg,#2068CC,#1558B8); }

.stTabs [data-baseweb="tab-list"]  { background:#FFFFFF; border-radius:10px; border:1px solid #DDE3EE; padding:4px; gap:4px; }
.stTabs [data-baseweb="tab"]       { border-radius:7px; padding:8px 20px; font-family:'Share Tech Mono',monospace; font-size:.8rem; color:#7A8BAA; border:none; background:transparent; }
.stTabs [aria-selected="true"]     { background:#1A5CB8!important; color:#FFFFFF!important; }

hr { border-color:#DDE3EE!important; }
.block-container { padding-top:1.6rem; }
.mono { font-family:'Share Tech Mono',monospace; }

.badge-buy  { background:#E8FAF0; color:#1A8A4A; border:1px solid #1A8A4A; border-radius:4px; padding:3px 12px; font-size:.72rem; font-family:'Share Tech Mono',monospace; font-weight:700; }
.badge-hold { background:#FFFBE6; color:#B07800; border:1px solid #B07800; border-radius:4px; padding:3px 12px; font-size:.72rem; font-family:'Share Tech Mono',monospace; font-weight:700; }
.badge-sell { background:#FEF0F0; color:#C0392B; border:1px solid #C0392B; border-radius:4px; padding:3px 12px; font-size:.72rem; font-family:'Share Tech Mono',monospace; font-weight:700; }
.badge-warn { background:#FFF4E6; color:#C05A00; border:1px solid #C05A00; border-radius:4px; padding:3px 12px; font-size:.72rem; font-family:'Share Tech Mono',monospace; font-weight:700; }

.risk-ok       { background:#F0FBF5; border-left:4px solid #27AE60; padding:10px 14px; border-radius:6px; margin:6px 0; font-size:.82rem; color:#1A3A28; }
.risk-warn     { background:#FFF8EE; border-left:4px solid #E67E22; padding:10px 14px; border-radius:6px; margin:6px 0; font-size:.82rem; color:#3A2800; }
.risk-critical { background:#FEF0F0; border-left:4px solid #E74C3C; padding:10px 14px; border-radius:6px; margin:6px 0; font-size:.82rem; color:#3A0A0A; }

.section-label { font-family:'Share Tech Mono',monospace; font-size:.64rem; letter-spacing:.14em; color:#7A8BAA; text-transform:uppercase; margin-bottom:4px; }
.info-box  { background:#F0F5FF; border:1px solid #C0D0EE; border-radius:8px; padding:12px 16px; font-size:.84rem; color:#1A2035; margin:8px 0; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 1. 상수
# ══════════════════════════════════════════════════════════════
LAWD_MAP = {
    "강남구":"11680","서초구":"11650","송파구":"11710","강동구":"11740",
    "성동구":"11200","광진구":"11215","마포구":"11440","용산구":"11170",
    "영등포구":"11560","동작구":"11590","관악구":"11620","강서구":"11500",
    "양천구":"11470","구로구":"11530","금천구":"11545","동대문구":"11230",
    "중랑구":"11260","성북구":"11290","강북구":"11305","도봉구":"11320",
    "노원구":"11350","은평구":"11380","서대문구":"11410","종로구":"11110",
    "중구":"11140","중구(인천)":"28110","수원시":"41111","성남시":"41131",
    "고양시":"41281","용인시":"41461","부천시":"41190","안양시":"41171",
    "직접 입력":"CUSTOM",
}

# 공공데이터포털 신버전 URL (2023년 이후 유효)
EP_SALE = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
EP_RENT = "http://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"

CHART_LAYOUT = dict(
    paper_bgcolor="#FFFFFF", plot_bgcolor="#FAFBFD",
    font=dict(family="Share Tech Mono, monospace", color="#5A6A8A", size=11),
    margin=dict(l=20, r=20, t=44, b=20),
    legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#DDE3EE", borderwidth=1),
    xaxis=dict(gridcolor="#E8EDF5", zerolinecolor="#DDE3EE", linecolor="#DDE3EE"),
    yaxis=dict(gridcolor="#E8EDF5", zerolinecolor="#DDE3EE", linecolor="#DDE3EE"),
)


# ══════════════════════════════════════════════════════════════
# 2. API 수집
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_month(service_key, endpoint, lawd_cd, ym):
    """
    공공데이터포털 신버전 API 호출
    - 매매: dealAmount / 임대차: deposit + monthlyRent
    - 응답이 JSON 또는 XML 모두 처리
    """
    params = {
        "serviceKey": service_key,
        "LAWD_CD":    lawd_cd,
        "DEAL_YMD":   ym,
        "numOfRows":  1000,
        "pageNo":     1,
    }
    try:
        resp = requests.get(endpoint, params=params, timeout=15)

        # ── XML 파싱
        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            return []

        # 오류 코드 확인
        result_code = root.findtext(".//resultCode", "")
        if result_code and result_code not in ("00", "0000", "000", ""):
            return []

        items = root.findall(".//item")
        if not items:
            return []

        records = []
        for item in items:
            try:
                # 매매금액 (쉼표 제거)
                def clean(tag, default="0"):
                    v = item.findtext(tag) or default
                    return v.replace(",", "").strip()

                # 단지명: aptNm (신버전 동일)
                apt_nm = (item.findtext("aptNm") or "").strip()

                # 전용면적: excluUseAr
                area_raw = clean("excluUseAr", "0")
                try:
                    area = float(area_raw)
                except ValueError:
                    area = 0.0

                # 날짜
                year_  = int(item.findtext("dealYear")  or 0)
                month_ = int(item.findtext("dealMonth") or 0)
                # 일: dealDay (없으면 1)
                day_raw = (item.findtext("dealDay") or "1").strip()
                try:
                    day_ = int(day_raw)
                except ValueError:
                    day_ = 1

                # 매매금액
                deal_raw = clean("dealAmount")
                deal = int(deal_raw) if deal_raw and deal_raw != "0" else 0

                # 임대차: deposit(보증금), monthlyRent(월세)
                deposit_raw = clean("deposit")
                rent_raw    = clean("monthlyRent")
                deposit = int(deposit_raw) if deposit_raw and deposit_raw != "0" else 0
                rent    = int(rent_raw)    if rent_raw    and rent_raw    != "0" else 0

                build_yr = int(item.findtext("buildYear") or 0)
                floor_   = int((item.findtext("floor") or "0").strip() or 0)

                if year_ == 0 or month_ == 0:
                    continue

                records.append({
                    "단지명":   apt_nm,
                    "전용면적": area,
                    "거래금액": deal,
                    "보증금":   deposit,
                    "월세":     rent,
                    "년":       year_,
                    "월":       month_,
                    "일":       day_,
                    "건축년도": build_yr,
                    "층":       floor_,
                })
            except Exception:
                continue

        return records

    except requests.exceptions.Timeout:
        return []
    except Exception:
        return []


def load_api(service_key, lawd_cd, endpoint, months):
    all_rec = []
    now     = datetime.now()
    prog    = st.progress(0, text="수집 중...")
    failed  = []

    for i in range(months):
        ym  = (now - timedelta(days=30 * i)).strftime("%Y%m")
        rec = fetch_month(service_key, endpoint, lawd_cd, ym)
        if rec:
            all_rec.extend(rec)
        else:
            failed.append(ym)
        prog.progress((i + 1) / months, text=f"수집 중... {ym}  ({len(all_rec):,}건)")

    prog.empty()

    if not all_rec:
        # 디버그 정보 표시
        st.error(
            f"❌ 데이터 수집 실패 — 확인 사항:\n"
            f"1. API 키가 **Encoding 키**인지 확인 (Decoding 키 ❌)\n"
            f"2. 공공데이터포털에서 해당 API 활용신청이 **승인** 상태인지 확인\n"
            f"3. 법정동 코드 **{lawd_cd}** 가 올바른지 확인\n"
            f"4. 수집 대상 월: {months}개월 중 {len(failed)}개월 응답 없음"
        )
        return pd.DataFrame()

    df = pd.DataFrame(all_rec)
    df["날짜"] = pd.to_datetime(
        df[["년", "월", "일"]].rename(columns={"년": "year", "월": "month", "일": "day"}),
        errors="coerce"
    )
    df = df.dropna(subset=["날짜"]).sort_values("날짜").reset_index(drop=True)

    if failed:
        st.caption(f"ℹ️ 거래 없는 월 {len(failed)}개월 제외 (정상) | 총 {len(df):,}건 수집 완료")

    return df


def load_csv(uploaded):
    df = pd.read_csv(uploaded, encoding="utf-8-sig")
    if "일" not in df.columns:
        df["일"] = 1
    df["날짜"] = pd.to_datetime(
        df[["년","월","일"]].rename(columns={"년":"year","월":"month","일":"day"}),
        errors="coerce")
    return df.dropna(subset=["날짜"]).sort_values("날짜").reset_index(drop=True)


# ══════════════════════════════════════════════════════════════
# 3. 집계 & 분석 엔진
# ══════════════════════════════════════════════════════════════
def apply_filter(df, apt, amin, amax):
    if apt:
        df = df[df["단지명"].str.contains(apt, na=False)]
    return df[(df["전용면적"] >= amin) & (df["전용면적"] <= amax)]


def monthly_agg(df, price_col):
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["YM"] = df["날짜"].dt.to_period("M")
    m = (df.groupby("YM")
           .agg(중위가=(price_col,"median"), 건수=(price_col,"count"))
           .reset_index())
    m["날짜"] = m["YM"].dt.to_timestamp()
    m = m.sort_values("날짜").reset_index(drop=True)
    m["60MA"]  = m["중위가"].rolling(60, min_periods=3).mean()
    m["이격도"] = (m["중위가"] / m["60MA"] * 100).round(1)
    return m


def make_sale_monthly(df, apt, amin, amax):
    d = apply_filter(df[df["거래금액"]>0], apt, amin, amax)
    return monthly_agg(d, "거래금액")


def make_rent_monthly(df, apt, amin, amax):
    d = apply_filter(df, apt, amin, amax)
    js = monthly_agg(d[d["월세"]==0], "보증금")   # 전세
    ws = monthly_agg(d[d["월세"]>0],  "월세")     # 월세
    return js, ws


def signal(v):
    if v < 95:  return "강력 매수","buy","#1A8A4A"
    if v < 110: return "매수 관심","buy","#27AE60"
    if v < 120: return "적정 구간","hold","#B07800"
    if v < 135: return "고평가 주의","hold","#E67E22"
    if v < 150: return "과열 경고","sell","#C0392B"
    return              "버블 위험","sell","#922B21"


def eta(mdf):
    d = mdf.dropna(subset=["중위가","이격도"])
    if len(d) < 6:
        return {"eta_date":None,"A":None,"trend":"데이터 부족"}
    r = d.tail(6).reset_index(drop=True)
    p_now, p_prev = r["중위가"].tail(3).mean(), r["중위가"].head(3).mean()
    dP = (p_now-p_prev)/p_prev*100 if p_prev else 0
    v_now, v_prev = r["건수"].tail(3).mean(), r["건수"].head(3).mean()
    dV = (v_now-v_prev)/v_prev*100 if v_prev else 0
    A  = dP*0.7 + dV*0.3
    gap = 100.0 - float(d["이격도"].iloc[-1])
    if abs(A) < 0.05:
        return {"eta_date":None,"A":round(A,3),"trend":"횡보","dP":round(dP,2),"dV":round(dV,2)}
    eta_m = gap/A
    eta_date = datetime.now()+timedelta(days=30*eta_m) if eta_m>0 else None
    trend = ("하락 수렴 중" if A<0 else "상승 이탈 중") if eta_m>0 else ("이미 수렴" if A<0 else "이미 이탈")
    return {"eta_date":eta_date,"eta_m":round(eta_m,1) if eta_m>0 else None,
            "A":round(A,3),"trend":trend,"dP":round(dP,2),"dV":round(dV,2)}


def project_future(mdf, ahead=18):
    d = mdf.dropna(subset=["중위가"]).tail(12).copy()
    if len(d) < 4:
        return pd.DataFrame()
    d["t"] = np.arange(len(d))
    slope, intercept = np.polyfit(d["t"], d["중위가"], 1)
    last_date = d["날짜"].iloc[-1]
    return pd.DataFrame([
        {"날짜": last_date+timedelta(days=30*i),
         "예측가": round(intercept+slope*(len(d)+i-1))}
        for i in range(1, ahead+1)
    ])


def dcf_value(ws_man, dep_eok, base_r, risk_p, pir, pir_avg=27.0):
    r = (base_r+risk_p)/100
    base = (ws_man*12*10_000)/r/1e8 + dep_eok
    pen  = base*0.10 if pir > pir_avg*1.2 else 0.0
    adj  = base - pen
    yld  = (ws_man*12)/((adj-dep_eok)*1e4)*100 if (adj-dep_eok)>0 else 0
    return {"base":round(base,2),"adjusted":round(adj,2),
            "penalty":round(pen,2),"rate":round(r*100,2),"yield":round(yld,2)}


def dsr_limit(income_man, rate_pct, years=30):
    r = rate_pct/100/12; n = years*12
    mp = income_man*10_000/12*0.40
    loan = mp*(1-(1+r)**(-n))/r if r>0 else mp*n
    return {"loan":round(loan/1e8,2),"monthly":round(mp/10_000,1)}


# ══════════════════════════════════════════════════════════════
# 4. 차트
# ══════════════════════════════════════════════════════════════
def chart_trend(mdf, fut, e, title, unit, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mdf["날짜"], y=mdf["중위가"],
        name=f"실거래 중위({unit})", mode="lines+markers",
        line=dict(color=color, width=2), marker=dict(size=4)))
    if "60MA" in mdf.columns:
        fig.add_trace(go.Scatter(x=mdf["날짜"], y=mdf["60MA"],
            name="60월선", mode="lines",
            line=dict(color="#F39C12", width=2, dash="dot")))
    if not fut.empty:
        last = mdf.dropna(subset=["중위가"]).tail(1)
        bx = list(last["날짜"]) + list(fut["날짜"])
        by = list(last["중위가"]) + list(fut["예측가"])
        fig.add_trace(go.Scatter(x=bx, y=by, name="회귀 예측",
            mode="lines", line=dict(color="#9B59B6", width=1.5, dash="dash")))
    if e.get("eta_date"):
        fig.add_vline(x=e["eta_date"].timestamp()*1000,
            line=dict(color="#27AE60", width=1, dash="dot"),
            annotation_text=f"  60MA 수렴 {e['eta_date'].strftime('%Y.%m')}",
            annotation_font=dict(color="#27AE60", size=10))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text=title, font=dict(color="#1A2035", size=13)),
        yaxis_title=unit, height=350)
    return fig


def chart_disparity(mdf, title):
    d = mdf.dropna(subset=["이격도"])
    colors = ["#27AE60" if v<110 else "#F39C12" if v<130 else "#E74C3C" for v in d["이격도"]]
    fig = go.Figure(go.Bar(x=d["날짜"], y=d["이격도"],
        marker_color=colors, opacity=0.75))
    fig.add_hline(y=100, line=dict(color="#2270CC", width=1, dash="dot"),
        annotation_text="  기준선(100%)", annotation_font=dict(color="#2270CC", size=9))
    fig.add_hline(y=120, line=dict(color="#E67E22", width=1, dash="dot"))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text=title, font=dict(color="#1A2035", size=12)),
        yaxis_title="이격도 (%)", height=230)
    return fig


def chart_overlay(sale_m, js_m):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sale_m["날짜"], y=sale_m["중위가"]/10_000,
        name="매매가(억)", mode="lines", line=dict(color="#1A5CB8", width=2)))
    fig.add_trace(go.Scatter(x=js_m["날짜"], y=js_m["중위가"]/10_000,
        name="전세가(억)", mode="lines", line=dict(color="#E67E22", width=2)))
    merged = pd.merge(sale_m[["날짜","중위가"]].rename(columns={"중위가":"sale"}),
                      js_m[["날짜","중위가"]].rename(columns={"중위가":"js"}),
                      on="날짜", how="inner")
    if not merged.empty:
        merged["전세가율"] = (merged["js"]/merged["sale"]*100).round(1)
        fig.add_trace(go.Scatter(x=merged["날짜"], y=merged["전세가율"],
            name="전세가율(%)", mode="lines",
            line=dict(color="#9B59B6", width=1.5, dash="dot"), yaxis="y2"))
        fig.add_hline(y=80, line=dict(color="#E74C3C", width=1, dash="dot"),
            annotation_text="  갭투자 위험(80%)",
            annotation_font=dict(color="#E74C3C", size=9), yref="y2")
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text="📊 매매 vs 전세 & 전세가율", font=dict(color="#1A2035", size=13)),
        yaxis=dict(title="금액(억)", gridcolor="#E8EDF5"),
        yaxis2=dict(title="전세가율(%)", overlaying="y", side="right",
                    gridcolor="rgba(0,0,0,0)", showgrid=False),
        height=360)
    return fig


def chart_rent_yield(ws_m, sale_eok, dep_eok):
    ws_m = ws_m.copy()
    net = (sale_eok - dep_eok) * 1e8
    if net <= 0:
        return None
    ws_m["수익률"] = (ws_m["중위가"]*12*10_000/net*100).round(2)
    fig = go.Figure(go.Scatter(x=ws_m["날짜"], y=ws_m["수익률"],
        mode="lines+markers", line=dict(color="#27AE60", width=2),
        marker=dict(size=4), fill="tozeroy", fillcolor="rgba(39,174,96,0.08)"))
    fig.add_hline(y=3.0, line=dict(color="#E67E22", width=1, dash="dot"),
        annotation_text="  최저 기대수익 3%", annotation_font=dict(color="#E67E22", size=9))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text="💰 월세 임대 수익률 추이(%)", font=dict(color="#1A2035", size=13)),
        yaxis_title="연 수익률(%)", height=270)
    return fig


def chart_scenario(loan_eok, rate_pct):
    rates = [rate_pct-1.5, rate_pct-0.5, rate_pct, rate_pct+0.5, rate_pct+1.5]
    pays  = []
    for r in rates:
        rm = r/100/12; n = 30*12
        pays.append(round(loan_eok*1e8*rm/(1-(1+rm)**(-n))/10_000,1) if rm>0 else 0)
    colors = ["#1A5CB8" if r<=rate_pct else "#E74C3C" for r in rates]
    fig = go.Figure(go.Bar(x=[f"{r:.1f}%" for r in rates], y=pays,
        marker_color=colors, text=[f"{p}만" for p in pays],
        textposition="outside", textfont=dict(color="#1A2035", size=10)))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text="💰 금리 시나리오별 월 상환액", font=dict(color="#1A2035", size=13)),
        yaxis_title="월 상환액(만원)", height=250)
    return fig


# ══════════════════════════════════════════════════════════════
# 5. 사이드바
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<p class="mono" style="color:#1A5CB8;font-size:.78rem;letter-spacing:.12em;">PRINCIPAL ARCHITECT</p>', unsafe_allow_html=True)
    st.markdown("### 🏗️ SEQUOIA QUANTUM™")
    st.caption("RE Engine v3.0 — 매매·전세·월세 통합")
    st.divider()

    st.markdown('<p class="section-label">📡 데이터 소스</p>', unsafe_allow_html=True)
    data_mode = st.radio("", ["국토부 API","CSV 업로드"], horizontal=True, label_visibility="collapsed")

    service_key = ""; lawd_cd = "11200"; region_name = "성동구"; fetch_months = 36
    uploaded_sale = uploaded_rent = None

    if data_mode == "국토부 API":
        service_key = st.text_input("API 서비스 키", type="password", placeholder="발급받은 키 입력")
        region_name = st.selectbox("지역 (법정동 코드)", list(LAWD_MAP.keys()))
        lawd_cd = st.text_input("법정동 코드(5자리)", LAWD_MAP.get(region_name,"11200")) \
                  if region_name=="직접 입력" else LAWD_MAP[region_name]
        fetch_months = st.slider("수집 기간(개월)", 12, 60, 36, step=6)
    else:
        st.caption("매매·임대차를 각각 업로드하세요")
        uploaded_sale = st.file_uploader("매매 CSV", type=["csv"], key="sale")
        uploaded_rent = st.file_uploader("임대차 CSV (전세·월세 포함)", type=["csv"], key="rent")
        st.caption("필수 컬럼: 단지명, 전용면적, 거래금액(매매) / 보증금·월세(임대차), 년, 월")

    st.divider()
    st.markdown('<p class="section-label">🔍 단지 필터</p>', unsafe_allow_html=True)
    apt_name = st.text_input("단지명 (일부 포함)", placeholder="예) 센트라스")
    c1, c2 = st.columns(2)
    area_min = c1.number_input("면적 최소(㎡)", value=59.0, step=1.0)
    area_max = c2.number_input("면적 최대(㎡)", value=85.0, step=1.0)

    st.divider()
    st.markdown('<p class="section-label">💼 재무 정보</p>', unsafe_allow_html=True)
    cash       = st.number_input("가용 자산(억)", value=5.0, step=0.5)
    income_man = st.number_input("연봉(만원)", value=8000, step=500)
    rate       = st.slider("적용 금리(%)", 2.0, 9.0, 4.5, step=0.1)

    st.divider()
    st.markdown('<p class="section-label">📐 DCF 입력</p>', unsafe_allow_html=True)
    deposit_dcf = st.number_input("보증금(억)", value=1.0, step=0.5)
    risk_prem   = st.slider("리스크 프리미엄(%)", 0.5, 3.0, 1.5, step=0.25)
    pir         = st.number_input("단지 PIR(배수)", value=27.0, step=0.5)

    st.divider()
    run_btn = st.button("⚡ 퀀텀 엔진 가동", use_container_width=True)


# ══════════════════════════════════════════════════════════════
# 6. 메인 헤더
# ══════════════════════════════════════════════════════════════
st.markdown('<p class="mono" style="font-size:1.45rem;color:#1A5CB8;letter-spacing:.04em;">📊 SEQUOIA QUANTUM™  REAL ESTATE ENGINE  v3.0</p>', unsafe_allow_html=True)
st.markdown('<p class="mono" style="font-size:.68rem;color:#8A9BB8;letter-spacing:.14em;">매매 · 전세 · 월세 통합분석 | DCF · 60MA · DSR · ETA PREDICTIVE</p>', unsafe_allow_html=True)
st.divider()

if not run_btn:
    st.info("👈 좌측 사이드바 설정 후 **'퀀텀 엔진 가동'** 버튼을 누르세요.")
    st.stop()


# ══════════════════════════════════════════════════════════════
# 7. 데이터 로드
# ══════════════════════════════════════════════════════════════
sale_raw = rent_raw = pd.DataFrame()

with st.spinner("데이터 수집 중..."):
    if data_mode == "국토부 API":
        if not service_key:
            st.error("❌ API 서비스 키를 입력해 주세요."); st.stop()
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.caption("📥 매매 데이터 수집 중...")
            sale_raw = load_api(service_key, lawd_cd, EP_SALE, fetch_months)
        with col_p2:
            st.caption("📥 임대차 데이터 수집 중...")
            rent_raw = load_api(service_key, lawd_cd, EP_RENT, fetch_months)
    else:
        if uploaded_sale: sale_raw = load_csv(uploaded_sale)
        if uploaded_rent: rent_raw = load_csv(uploaded_rent)

if sale_raw.empty and rent_raw.empty:
    st.error("❌ 수집된 데이터가 없습니다. 설정을 확인하세요."); st.stop()


# ══════════════════════════════════════════════════════════════
# 8. 집계
# ══════════════════════════════════════════════════════════════
sale_m = make_sale_monthly(sale_raw, apt_name, area_min, area_max) if not sale_raw.empty else pd.DataFrame()
js_m, ws_m = make_rent_monthly(rent_raw, apt_name, area_min, area_max) if not rent_raw.empty else (pd.DataFrame(), pd.DataFrame())

display_name = apt_name if apt_name else (region_name if data_mode=="국토부 API" else "CSV 전체")


# ══════════════════════════════════════════════════════════════
# 9. 지표 계산
# ══════════════════════════════════════════════════════════════
# 매매
current_sale_eok = current_disp = ma60_eok = None
sig_label = "—"; sig_type = "hold"
if not sale_m.empty:
    lr = sale_m.dropna(subset=["이격도"])
    if not lr.empty:
        lr = lr.iloc[-1]
        current_sale_eok = round(float(lr["중위가"])/10_000, 2)
        current_disp     = float(lr["이격도"])
        ma60_eok         = round(float(lr["60MA"])/10_000, 2) if not pd.isna(lr["60MA"]) else None
        sig_label, sig_type, _ = signal(current_disp)

# 전세
current_js_eok = js_ratio = None
if not js_m.empty:
    lr_js = js_m.dropna(subset=["중위가"])
    if not lr_js.empty:
        current_js_eok = round(float(lr_js.iloc[-1]["중위가"])/10_000, 2)
        if current_sale_eok and current_sale_eok > 0:
            js_ratio = round(current_js_eok/current_sale_eok*100, 1)

# 월세
current_ws_man = ws_yield = None
if not ws_m.empty:
    lr_ws = ws_m.dropna(subset=["중위가"])
    if not lr_ws.empty:
        current_ws_man = int(lr_ws.iloc[-1]["중위가"])
        if current_sale_eok:
            net = (current_sale_eok - deposit_dcf)*1e8
            ws_yield = round(current_ws_man*12*10_000/net*100, 2) if net>0 else None

dsr = dsr_limit(income_man, rate)
budget = cash + dsr["loan"]


# ══════════════════════════════════════════════════════════════
# 10. KPI 카드 (상단 5개)
# ══════════════════════════════════════════════════════════════
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("현재 매매가",
              f"{current_sale_eok}억" if current_sale_eok else "—",
              f"60MA {ma60_eok}억" if ma60_eok else "")
with k2:
    st.metric("60월선 이격도",
              f"{current_disp:.1f}%" if current_disp else "—",
              sig_label)
with k3:
    js_warn = " ⚠️" if js_ratio and js_ratio > 80 else ""
    st.metric("현재 전세가",
              f"{current_js_eok}억" if current_js_eok else "—",
              f"전세가율 {js_ratio}%{js_warn}" if js_ratio else "")
with k4:
    st.metric("현재 월세(중위)",
              f"{current_ws_man}만" if current_ws_man else "—",
              f"수익률 {ws_yield}%" if ws_yield else "")
with k5:
    st.metric("DSR 40% 대출한도",
              f"{dsr['loan']}억",
              f"월 상환 {dsr['monthly']}만")

st.divider()


# ══════════════════════════════════════════════════════════════
# 11. 탭
# ══════════════════════════════════════════════════════════════
tab_sale, tab_jeonse, tab_wolse, tab_compare, tab_summary = st.tabs([
    "🏠 매매 분석", "📋 전세 분석", "💵 월세 분석", "🔍 단지 비교", "🎯 종합 판단"
])


# ── TAB 1: 매매 ──────────────────────────────────────────────
with tab_sale:
    if sale_m.empty:
        st.warning("매매 데이터가 없습니다.")
    else:
        e_s  = eta(sale_m)
        fut_s = project_future(sale_m)

        col_ch, col_risk = st.columns([3,1])
        with col_ch:
            st.plotly_chart(
                chart_trend(sale_m, fut_s, e_s,
                            f"📈 {display_name} 매매가 추세 & 60MA", "만원", "#1A5CB8"),
                use_container_width=True)
        with col_risk:
            st.markdown('<p class="section-label">🛡️ 매매 신호</p>', unsafe_allow_html=True)
            if current_disp:
                st.markdown(f'<span class="badge-{sig_type}">{sig_label}</span>', unsafe_allow_html=True)
                st.caption(f"이격도 {current_disp:.1f}%")
            st.divider()

            st.markdown('<p class="section-label">💼 진입 가능성</p>', unsafe_allow_html=True)
            if current_sale_eok:
                if current_sale_eok <= budget:
                    st.markdown(f'<div class="risk-ok">✅ 진입 가능<br>예산 {budget:.1f}억 ≥ {current_sale_eok}억</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="risk-critical">❌ 예산 부족<br>+{current_sale_eok-budget:.1f}억 필요</div>', unsafe_allow_html=True)
            st.divider()

            st.markdown('<p class="section-label">📡 60MA ETA</p>', unsafe_allow_html=True)
            if e_s.get("eta_date"):
                st.markdown(f'<div class="risk-ok">📅 {e_s["eta_date"].strftime("%Y.%m")}<br>{e_s["trend"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="risk-warn">⚠️ {e_s.get("trend","산출 불가")}</div>', unsafe_allow_html=True)

        st.plotly_chart(chart_disparity(sale_m, "📊 매매가 60월선 이격도"), use_container_width=True)

        with st.expander("📐 가속도 계산 근거"):
            st.markdown(f"""
| 항목 | 값 |
|------|-----|
| 가격 변화율 ΔP | {e_s.get('dP','N/A')} % |
| 거래량 변화율 ΔV | {e_s.get('dV','N/A')} % |
| 가속도 A | **{e_s.get('A','N/A')}** |
| 60MA 수렴 예상 | {e_s['eta_date'].strftime('%Y.%m') if e_s.get('eta_date') else '산출 불가'} |
""")


# ── TAB 2: 전세 ──────────────────────────────────────────────
with tab_jeonse:
    if js_m.empty:
        st.warning("전세 데이터가 없습니다.")
    else:
        e_j   = eta(js_m)
        fut_j = project_future(js_m)

        # 전세가율 경고 배너
        if js_ratio:
            if js_ratio > 80:
                st.markdown(f'<div class="risk-critical">🚨 전세가율 {js_ratio}% — 갭투자 위험 구간. 매매가 하락 시 역전세 리스크.</div>', unsafe_allow_html=True)
            elif js_ratio > 70:
                st.markdown(f'<div class="risk-warn">⚠️ 전세가율 {js_ratio}% — 주의 구간 (70~80%).</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="risk-ok">✅ 전세가율 {js_ratio}% — 안전 구간 (70% 미만).</div>', unsafe_allow_html=True)

        col_a, col_b = st.columns([3,1])
        with col_a:
            if not sale_m.empty:
                st.plotly_chart(chart_overlay(sale_m, js_m), use_container_width=True)
            else:
                st.plotly_chart(
                    chart_trend(js_m, fut_j, e_j,
                                f"📋 {display_name} 전세가 추세 & 60MA", "만원", "#E67E22"),
                    use_container_width=True)
        with col_b:
            st.markdown('<p class="section-label">📡 전세 ETA</p>', unsafe_allow_html=True)
            if e_j.get("eta_date"):
                st.markdown(f'<div class="risk-ok">📅 {e_j["eta_date"].strftime("%Y.%m")}<br>{e_j["trend"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="risk-warn">⚠️ {e_j.get("trend","산출 불가")}</div>', unsafe_allow_html=True)
            st.divider()

            if current_js_eok:
                safe_sale = round(current_js_eok/0.70, 2)
                st.markdown('<p class="section-label">🏷️ 전세 역산 적정 매매가</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-box">전세가율 70% 기준<br><b>매매 최소 기대가: {safe_sale}억</b></div>', unsafe_allow_html=True)

        st.plotly_chart(chart_disparity(js_m, "📊 전세가 60월선 이격도"), use_container_width=True)


# ── TAB 3: 월세 ──────────────────────────────────────────────
with tab_wolse:
    if ws_m.empty:
        st.warning("월세 데이터가 없습니다.")
    else:
        e_w   = eta(ws_m)
        fut_w = project_future(ws_m)

        # DCF: 실제 시장 월세 자동 반영
        if current_ws_man:
            dcf = dcf_value(current_ws_man, deposit_dcf, rate, risk_prem, pir)
            dcf_diff = round(dcf["adjusted"]-(current_sale_eok or 0), 2)
            k1, k2, k3 = st.columns(3)
            k1.metric("시장 월세(중위)", f"{current_ws_man}만원/월")
            k2.metric("DCF 내재가치", f"{dcf['adjusted']}억", f"할인율 {dcf['rate']}%")
            k3.metric("매매가 괴리", f"{dcf_diff:+.2f}억", "저평가" if dcf_diff>=0 else "고평가")
            if dcf["penalty"] > 0:
                st.markdown(f'<div class="risk-warn">⚠️ PIR {pir} 과열 → DCF -10% 페널티 ({dcf["penalty"]}억 차감)</div>', unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(
                chart_trend(ws_m, fut_w, e_w,
                            f"💵 {display_name} 월세 추세 & 60MA", "만원/월", "#27AE60"),
                use_container_width=True)
        with col_b:
            if current_sale_eok:
                yc = chart_rent_yield(ws_m, current_sale_eok, deposit_dcf)
                if yc:
                    st.plotly_chart(yc, use_container_width=True)

        st.plotly_chart(chart_disparity(ws_m, "📊 월세 60월선 이격도"), use_container_width=True)
        st.plotly_chart(chart_scenario(dsr["loan"], rate), use_container_width=True)



# ── TAB 4: 단지 비교 ─────────────────────────────────────────
with tab_compare:
    st.markdown("### 🔍 인근 단지 비교 분석")
    st.caption("같은 지역 내 최대 5개 단지를 이격도·전세가율·수익률 기준으로 한눈에 비교합니다.")

    # 비교할 단지명 입력
    st.markdown('<p class="section-label">비교 단지 입력 (단지명 일부 포함, 쉼표로 구분)</p>', unsafe_allow_html=True)
    compare_input = st.text_input(
        "", placeholder="예) 센트라스, 텐즈힐, 왕십리, 두산위브",
        label_visibility="collapsed"
    )
    c_area_min, c_area_max = st.columns(2)
    cmin = c_area_min.number_input("면적 최소(㎡)", value=area_min, step=1.0, key="c_amin")
    cmax = c_area_max.number_input("면적 최대(㎡)", value=area_max, step=1.0, key="c_amax")

    if not compare_input.strip():
        st.info("👆 비교할 단지명을 쉼표로 구분해서 입력하세요. 데이터는 이미 수집된 지역 데이터를 사용합니다.")
    else:
        names = [n.strip() for n in compare_input.split(",") if n.strip()][:5]

        if sale_raw.empty and rent_raw.empty:
            st.warning("먼저 엔진을 가동해서 데이터를 수집해 주세요.")
        else:
            # 단지별 지표 계산
            compare_rows = []
            sale_series  = {}   # 이격도 차트용
            js_series    = {}   # 전세가율 차트용

            for nm in names:
                row = {"단지명": nm}

                # 매매
                sm = make_sale_monthly(sale_raw, nm, cmin, cmax) if not sale_raw.empty else pd.DataFrame()
                if not sm.empty:
                    lr = sm.dropna(subset=["이격도"])
                    if not lr.empty:
                        lr = lr.iloc[-1]
                        row["매매가(억)"]  = round(float(lr["중위가"])/10_000, 2)
                        row["60MA(억)"]   = round(float(lr["60MA"])/10_000, 2) if not pd.isna(lr["60MA"]) else None
                        row["이격도(%)"]  = float(lr["이격도"])
                        sig, _, _         = signal(float(lr["이격도"]))
                        row["매매신호"]   = sig
                        sale_series[nm]   = sm
                    else:
                        row["매매가(억)"] = row["60MA(억)"] = row["이격도(%)"] = row["매매신호"] = None
                else:
                    row["매매가(억)"] = row["60MA(억)"] = row["이격도(%)"] = row["매매신호"] = None

                # 전세
                jm, wm = make_rent_monthly(rent_raw, nm, cmin, cmax) if not rent_raw.empty else (pd.DataFrame(), pd.DataFrame())
                if not jm.empty:
                    lr_j = jm.dropna(subset=["중위가"])
                    if not lr_j.empty:
                        js_eok = round(float(lr_j.iloc[-1]["중위가"])/10_000, 2)
                        row["전세가(억)"] = js_eok
                        if row.get("매매가(억)") and row["매매가(억)"] > 0:
                            row["전세가율(%)"] = round(js_eok/row["매매가(억)"]*100, 1)
                        else:
                            row["전세가율(%)"] = None
                        js_series[nm] = jm
                    else:
                        row["전세가(억)"] = row["전세가율(%)"] = None
                else:
                    row["전세가(억)"] = row["전세가율(%)"] = None

                # 월세 수익률
                if not wm.empty:
                    lr_w = wm.dropna(subset=["중위가"])
                    if not lr_w.empty and row.get("매매가(억)"):
                        ws_man = float(lr_w.iloc[-1]["중위가"])
                        net    = (row["매매가(억)"] - deposit_dcf) * 1e8
                        row["월세수익률(%)"] = round(ws_man*12*10_000/net*100, 2) if net>0 else None
                    else:
                        row["월세수익률(%)"] = None
                else:
                    row["월세수익률(%)"] = None

                # ETA
                if not sm.empty and len(sm.dropna(subset=["이격도"])) >= 6:
                    e = eta(sm)
                    row["60MA수렴예상"] = e["eta_date"].strftime("%Y.%m") if e.get("eta_date") else e.get("trend","—")
                else:
                    row["60MA수렴예상"] = "—"

                compare_rows.append(row)

            if not compare_rows:
                st.warning("해당 단지명의 거래 데이터가 없습니다.")
            else:
                df_cmp = pd.DataFrame(compare_rows)

                # ── 요약 테이블
                st.markdown("#### 📋 단지별 핵심 지표 비교")

                def color_disparity(val):
                    if pd.isna(val): return ""
                    if val < 100:   return "background-color:#E8FAF0; color:#1A8A4A; font-weight:700"
                    if val < 115:   return "background-color:#F0F7E8; color:#2E7D32"
                    if val < 130:   return "background-color:#FFFBE6; color:#B07800"
                    return                  "background-color:#FEF0F0; color:#C0392B; font-weight:700"

                def color_jsratio(val):
                    if pd.isna(val): return ""
                    if val < 60:    return "background-color:#E8FAF0; color:#1A8A4A"
                    if val < 70:    return "background-color:#F0F7E8; color:#2E7D32"
                    if val < 80:    return "background-color:#FFFBE6; color:#B07800"
                    return                  "background-color:#FEF0F0; color:#C0392B; font-weight:700"

                def color_yield(val):
                    if pd.isna(val): return ""
                    if val >= 4:    return "background-color:#E8FAF0; color:#1A8A4A; font-weight:700"
                    if val >= 3:    return "background-color:#F0F7E8; color:#2E7D32"
                    if val >= 2:    return "background-color:#FFFBE6; color:#B07800"
                    return                  "background-color:#FEF0F0; color:#C0392B"

                styled = (
                    df_cmp.style
                    .applymap(color_disparity, subset=["이격도(%)"] if "이격도(%)" in df_cmp.columns else [])
                    .applymap(color_jsratio,   subset=["전세가율(%)"] if "전세가율(%)" in df_cmp.columns else [])
                    .applymap(color_yield,     subset=["월세수익률(%)"] if "월세수익률(%)" in df_cmp.columns else [])
                    .format(na_rep="—", precision=2)
                )
                st.dataframe(styled, use_container_width=True, hide_index=True)

                st.markdown("")
                st.caption("🟢 이격도: 100% 미만 저평가 / 🟡 115~130% 주의 / 🔴 130% 초과 과열  ·  전세가율: 🟢 60% 미만 안전 / 🔴 80% 초과 위험")

                # ── 이격도 멀티라인 차트
                if sale_series:
                    st.markdown("#### 📈 단지별 60월선 이격도 추이")
                    COLORS = ["#1A5CB8","#E67E22","#27AE60","#9B59B6","#E74C3C"]
                    fig_cmp = go.Figure()
                    for i, (nm, sm) in enumerate(sale_series.items()):
                        d = sm.dropna(subset=["이격도"])
                        if d.empty: continue
                        fig_cmp.add_trace(go.Scatter(
                            x=d["날짜"], y=d["이격도"],
                            name=nm, mode="lines",
                            line=dict(color=COLORS[i % len(COLORS)], width=2)
                        ))
                    fig_cmp.add_hline(y=100, line=dict(color="#888", width=1, dash="dot"),
                        annotation_text="  기준선(100%)", annotation_font=dict(color="#888", size=9))
                    fig_cmp.add_hline(y=120, line=dict(color="#E67E22", width=1, dash="dot"))
                    fig_cmp.update_layout(**CHART_LAYOUT,
                        title=dict(text="단지별 60월선 이격도 비교", font=dict(color="#1A2035", size=13)),
                        yaxis_title="이격도(%)", height=350)
                    st.plotly_chart(fig_cmp, use_container_width=True)

                # ── 매매가 절대값 비교 바차트
                if "매매가(억)" in df_cmp.columns:
                    st.markdown("#### 💰 현재 매매가 비교")
                    df_bar = df_cmp.dropna(subset=["매매가(억)"])
                    if not df_bar.empty:
                        COLORS = ["#1A5CB8","#E67E22","#27AE60","#9B59B6","#E74C3C"]
                        bar_colors = [COLORS[i % len(COLORS)] for i in range(len(df_bar))]
                        fig_bar = go.Figure()
                        fig_bar.add_trace(go.Bar(
                            x=df_bar["단지명"], y=df_bar["매매가(억)"],
                            name="현재 매매가",
                            marker_color=bar_colors,
                            text=[f"{v}억" for v in df_bar["매매가(억)"]],
                            textposition="outside",
                            textfont=dict(color="#1A2035", size=11),
                        ))
                        if "60MA(억)" in df_bar.columns:
                            fig_bar.add_trace(go.Bar(
                                x=df_bar["단지명"], y=df_bar["60MA(억)"],
                                name="60MA",
                                marker_color="rgba(243,156,18,0.5)",
                                text=[f"{v}억" if v else "" for v in df_bar["60MA(억)"]],
                                textposition="outside",
                                textfont=dict(color="#B07800", size=10),
                            ))
                        fig_bar.update_layout(**CHART_LAYOUT,
                            title=dict(text="현재 매매가 vs 60MA 비교", font=dict(color="#1A2035", size=13)),
                            yaxis_title="억원", barmode="group", height=320)
                        st.plotly_chart(fig_bar, use_container_width=True)

                # ── 전세가율 비교 바차트
                if "전세가율(%)" in df_cmp.columns:
                    df_js = df_cmp.dropna(subset=["전세가율(%)"])
                    if not df_js.empty:
                        st.markdown("#### 📋 전세가율 비교")
                        js_bar_colors = [
                            "#27AE60" if v < 60 else "#F39C12" if v < 80 else "#E74C3C"
                            for v in df_js["전세가율(%)"]
                        ]
                        fig_js = go.Figure(go.Bar(
                            x=df_js["단지명"], y=df_js["전세가율(%)"],
                            marker_color=js_bar_colors,
                            text=[f"{v}%" for v in df_js["전세가율(%)"]],
                            textposition="outside",
                            textfont=dict(color="#1A2035", size=11),
                        ))
                        fig_js.add_hline(y=80, line=dict(color="#E74C3C", width=1.5, dash="dot"),
                            annotation_text="  갭투자 위험선(80%)",
                            annotation_font=dict(color="#E74C3C", size=9))
                        fig_js.add_hline(y=70, line=dict(color="#E67E22", width=1, dash="dot"))
                        fig_js.update_layout(**CHART_LAYOUT,
                            title=dict(text="단지별 전세가율 비교", font=dict(color="#1A2035", size=13)),
                            yaxis_title="전세가율(%)", height=300)
                        st.plotly_chart(fig_js, use_container_width=True)

                # ── 레이더 차트 (5차원 종합)
                has_enough = sum([
                    any(r.get("이격도(%)") for r in compare_rows),
                    any(r.get("전세가율(%)") for r in compare_rows),
                    any(r.get("월세수익률(%)") for r in compare_rows),
                ]) >= 2

                if has_enough and len(compare_rows) >= 2:
                    st.markdown("#### 🕸️ 단지별 종합 스코어 레이더")

                    def normalize_score(val, low_good=True, v_min=None, v_max=None):
                        """0~100 점수로 정규화. low_good=True면 낮을수록 좋음(이격도·전세가율)"""
                        if val is None or pd.isna(val):
                            return 50
                        if v_min is None or v_max is None:
                            return 50
                        if v_max == v_min:
                            return 50
                        norm = (val - v_min) / (v_max - v_min) * 100
                        return round(100 - norm if low_good else norm, 1)

                    dims = ["이격도(%)", "전세가율(%)", "월세수익률(%)"]
                    dim_labels = ["이격도\n(낮을수록好)", "전세가율\n(낮을수록好)", "월세수익률\n(높을수록好)"]
                    low_goods  = [True, True, False]

                    fig_radar = go.Figure()
                    COLORS = ["#1A5CB8","#E67E22","#27AE60","#9B59B6","#E74C3C"]

                    for dim, lg in zip(dims, low_goods):
                        vals = [r.get(dim) for r in compare_rows if r.get(dim) is not None]
                        if not vals:
                            continue
                        v_min, v_max = min(vals), max(vals)
                        for r in compare_rows:
                            r[f"_{dim}_score"] = normalize_score(r.get(dim), lg, v_min, v_max)

                    for i, r in enumerate(compare_rows):
                        scores = [r.get(f"_{dim}_score", 50) for dim in dims]
                        scores_closed = scores + [scores[0]]
                        labels_closed = dim_labels + [dim_labels[0]]
                        fig_radar.add_trace(go.Scatterpolar(
                            r=scores_closed, theta=labels_closed,
                            name=r["단지명"],
                            line=dict(color=COLORS[i % len(COLORS)], width=2),
                            fill="toself",
                            fillcolor=COLORS[i % len(COLORS)].replace("#","rgba(").replace(")",",0.08)") if "#" in COLORS[i%len(COLORS)] else "rgba(0,0,0,0.05)",
                        ))

                    fig_radar.update_layout(
                        paper_bgcolor="#FFFFFF",
                        polar=dict(
                            bgcolor="#FAFBFD",
                            radialaxis=dict(visible=True, range=[0,100], gridcolor="#E8EDF5"),
                            angularaxis=dict(gridcolor="#DDE3EE"),
                        ),
                        font=dict(family="Share Tech Mono, monospace", color="#5A6A8A", size=11),
                        legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#DDE3EE", borderwidth=1),
                        margin=dict(l=60, r=60, t=60, b=60),
                        title=dict(text="단지별 종합 스코어 (100점 기준)", font=dict(color="#1A2035", size=13)),
                        height=420,
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)
                    st.caption("각 차원은 비교 단지 내에서 상대 정규화된 점수입니다. 절대값이 아닌 상대 우열 비교용입니다.")


# ── TAB 5: 종합 판단 ─────────────────────────────────────────
with tab_summary:
    st.markdown("### 🎯 5차원 교차 검증 — 종합 판단")

    def score_dim(label, s, msg):
        return {"분석 차원": label, "판정": msg, "점수": f"{s}/3" if s is not None else "—", "_s": s}

    rows = []

    # 1. 매매 이격도
    if current_disp:
        s = 3 if current_disp<100 else 2 if current_disp<115 else 1 if current_disp<130 else 0
        m = ["✅ 강력 매수","✅ 매수 관심","⚠️ 고평가 주의","❌ 과열/버블"][3-s if s<3 else 0]
        rows.append(score_dim("매매 이격도", s, m))
    else:
        rows.append(score_dim("매매 이격도", None, "— 데이터 없음"))

    # 2. 전세가율
    if js_ratio:
        s = 3 if js_ratio<60 else 2 if js_ratio<70 else 1 if js_ratio<80 else 0
        m = f"✅ 안전({js_ratio}%)" if s>=2 else f"⚠️ 주의({js_ratio}%)" if s==1 else f"❌ 위험({js_ratio}%)"
        rows.append(score_dim("전세가율 리스크", s, m))
    else:
        rows.append(score_dim("전세가율 리스크", None, "— 데이터 없음"))

    # 3. 월세 수익률
    if ws_yield:
        s = 3 if ws_yield>=4 else 2 if ws_yield>=3 else 1 if ws_yield>=2 else 0
        m = f"✅ 우수({ws_yield}%)" if s==3 else f"✅ 양호({ws_yield}%)" if s==2 else f"⚠️ 부족({ws_yield}%)" if s==1 else f"❌ 열위({ws_yield}%)"
        rows.append(score_dim("임대 수익률", s, m))
    else:
        rows.append(score_dim("임대 수익률", None, "— 데이터 없음"))

    # 4. DCF 괴리
    if current_ws_man and current_sale_eok:
        dcf3 = dcf_value(current_ws_man, deposit_dcf, rate, risk_prem, pir)
        gap3 = dcf3["adjusted"] - current_sale_eok
        s = 3 if gap3>=1 else 2 if gap3>=0 else 1 if gap3>=-1 else 0
        m = f"✅ 저평가(+{gap3:.1f}억)" if gap3>=0 else f"⚠️ 소폭 고평가({gap3:.1f}억)" if gap3>=-1 else f"❌ 고평가({gap3:.1f}억)"
        rows.append(score_dim("DCF 내재가치", s, m))
    else:
        rows.append(score_dim("DCF 내재가치", None, "— 데이터 없음"))

    # 5. 예산 적합성
    if current_sale_eok:
        margin = budget - current_sale_eok
        s = 3 if margin>=2 else 2 if margin>=0 else 1 if margin>=-1 else 0
        m = f"✅ 여유(+{margin:.1f}억)" if margin>=0 else f"⚠️ 빠듯(-{abs(margin):.1f}억)" if margin>=-1 else f"❌ 불가(-{abs(margin):.1f}억)"
        rows.append(score_dim("예산 적합성", s, m))
    else:
        rows.append(score_dim("예산 적합성", None, "— 데이터 없음"))

    # 종합 점수
    valid = [r for r in rows if r["_s"] is not None]
    if valid:
        total = sum(r["_s"] for r in valid)
        max_s = len(valid)*3
        pct   = total/max_s*100
        verdict, vcls = (
            ("🟢 매수 적기",        "risk-ok")       if pct>=75 else
            ("🟡 관망 / 조건부 검토","risk-warn")     if pct>=50 else
            ("🔴 진입 보류",        "risk-critical")
        )
        st.markdown(
            f'<div class="{vcls}" style="font-size:1rem;">'
            f'<b>{verdict}</b> — 종합 점수 {total}/{max_s} ({pct:.0f}%)</div>',
            unsafe_allow_html=True)
        st.markdown("")

    df_score = pd.DataFrame([{"분석 차원":r["분석 차원"],"판정":r["판정"],"점수":r["점수"]} for r in rows])
    st.dataframe(df_score, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════
# 12. 푸터
# ══════════════════════════════════════════════════════════════
st.divider()
st.markdown(
    f'<p class="mono" style="font-size:.6rem;color:#A0AABF;text-align:center;">'
    f'SEQUOIA QUANTUM™ RE v3.0 · 본 분석은 투자 참고용이며 투자 권유가 아닙니다 · '
    f'데이터 기준일 {datetime.now().strftime("%Y.%m.%d")}</p>',
    unsafe_allow_html=True)
