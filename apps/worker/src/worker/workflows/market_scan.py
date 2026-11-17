from pydantic import BaseModel, Field

import mistralai.workflows as workflows

DEFAULT_STOCKS = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "BRK-B",
    "JNJ",
    "KO",
    "PG",
    "UNH",
    "COST",
    "WM",
    "XOM",
    "AC.PA",
    "AI.PA",
    "AIR.PA",
    "ALO.PA",
    "MT.AS",
    "CS.PA",
    "BNP.PA",
    "EN.PA",
    "CAP.PA",
    "CA.PA",
    "ACA.PA",
    "BN.PA",
    "DSY.PA",
    "EDEN.PA",
    "ENGI.PA",
    "EL.PA",
    "RMS.PA",
    "KER.PA",
    "OR.PA",
    "MC.PA",
    "LR.PA",
    "ML.PA",
    "ORA.PA",
    "RI.PA",
    "PUB.PA",
    "RNO.PA",
    "SAF.PA",
    "SGO.PA",
    "SAN.PA",
    "SU.PA",
    "STLA.PA",
    "STM.PA",
    "SW.PA",
    "TEP.PA",
    "HO.PA",
    "TTE.PA",
    "VIE.PA",
    "DG.PA",
    "VIV.PA",
    "WLN.PA",
    "ADP.PA",
    "ERF.PA",
    "GFC.PA",
    "RCO.PA",
    "URW.PA",
    "LI.PA",
    "FNAC.PA",
    "ALD.PA",
    "SOI.PA",
    "UBI.PA",
    "ASML.AS",
    "ADYEN.AS",
    "UNA.AS",
    "INGA.AS",
    "PHIA.AS",
    "HEIA.AS",
    "SAP.DE",
    "SIE.DE",
    "ALV.DE",
    "BAYN.DE",
    "BMW.DE",
    "MBG.DE",
    "DTE.DE",
    "MRK.DE",
    "NOVO-B.CO",
    "ISP.MI",
    "ENEL.MI",
    "ENI.MI",
    "G.MI",
    "SAN.MC",
    "ITX.MC",
    "IBE.MC",
    "CLNX.MC",
]
DEFAULT_CRYPTOS = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "BNB-USD",
    "XRP-USD",
    "ADA-USD",
    "AVAX-USD",
    "DOGE-USD",
    "LINK-USD",
    "DOT-USD",
    "LTC-USD",
]

DEFAULT_ETFS = [
    "DCAM.PA",
    "WPEA.PA",
    "PUST.PA",
    "PSP5.PA",
    "ESE.PA",
    "PAEEM.PA",
]

CRYPTO_NAMES = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
}


class ScanInput(BaseModel):
    recipient_email: str = "quemenerm1@gmail.com"
    stocks: list[str] = Field(default_factory=lambda: list(DEFAULT_STOCKS))
    cryptos: list[str] = Field(default_factory=lambda: list(DEFAULT_CRYPTOS))
    etfs: list[str] = Field(default_factory=lambda: list(DEFAULT_ETFS))
    min_buffett_score: int = 3
    dry_run: bool = False


class AssetReport(BaseModel):
    symbol: str
    asset_type: str
    name: str | None = None
    price: float | None = None
    sma_200w: float | None = None
    below_sma_200w: bool = False
    gap_to_sma_pct: float | None = None
    drawdown_from_ath_pct: float | None = None
    buffett_score: int = 0
    reasons: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    error: str | None = None


class ScanResult(BaseModel):
    scanned: int = 0
    alerts: list[AssetReport] = Field(default_factory=list)
    email_sent: bool = False
    dry_run: bool = False


def compute_sma(closes: list[float], window: int = 200) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def sma_trend_positive(closes: list[float], window: int = 200) -> bool | None:
    if len(closes) < window + 52:
        return None
    current = sum(closes[-window:]) / window
    past = sum(closes[-window - 52 : -52]) / window
    return current > past


def compute_drawdown_pct(closes: list[float]) -> float | None:
    if not closes:
        return None
    ath = max(closes)
    if ath <= 0:
        return None
    return (ath - closes[-1]) / ath * 100


def evaluate_buffett_stock(info: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    roe = info.get("returnOnEquity")
    if isinstance(roe, (int, float)) and roe >= 0.15:
        score += 1
        reasons.append(f"ROE solide ({roe * 100:.1f}%)")

    margin = info.get("profitMargins")
    if isinstance(margin, (int, float)) and margin >= 0.10:
        score += 1
        reasons.append(f"Marge nette elevee ({margin * 100:.1f}%)")

    debt_equity = info.get("debtToEquity")
    if isinstance(debt_equity, (int, float)) and debt_equity <= 120:
        score += 1
        reasons.append(f"Dette moderee (D/E {debt_equity:.0f})")

    growth = info.get("revenueGrowth")
    if isinstance(growth, (int, float)) and growth >= 0.05:
        score += 1
        reasons.append(f"Croissance des revenus ({growth * 100:.1f}%)")

    pe = info.get("trailingPE")
    if isinstance(pe, (int, float)) and 0 < pe <= 25:
        score += 1
        reasons.append(f"PER raisonnable ({pe:.1f})")

    return score, reasons


def build_stock_report(symbol: str, history_closes: list[float], info: dict) -> AssetReport:
    report = AssetReport(symbol=symbol, asset_type="stock")
    report.name = info.get("longName") or info.get("shortName") or symbol
    report.price = history_closes[-1] if history_closes else None
    report.sma_200w = compute_sma(history_closes)
    if report.price is not None and report.sma_200w is not None:
        report.below_sma_200w = report.price < report.sma_200w
        report.gap_to_sma_pct = (report.sma_200w - report.price) / report.sma_200w * 100
    report.drawdown_from_ath_pct = compute_drawdown_pct(history_closes)
    report.buffett_score, report.reasons = evaluate_buffett_stock(info)

    if report.below_sma_200w:
        report.alerts.append("Cours sous la moyenne mobile 200 semaines")
    if isinstance(report.drawdown_from_ath_pct, (int, float)) and report.drawdown_from_ath_pct >= 20:
        report.alerts.append(
            f"Drawdown de {report.drawdown_from_ath_pct:.1f}% par rapport au plus haut historique"
        )
    if report.buffett_score >= 3:
        report.alerts.append("Fondamentaux de qualite (criteres Buffett)")
    return report


def build_crypto_report(symbol: str, history_closes: list[float], info: dict | None = None) -> AssetReport:
    report = AssetReport(symbol=symbol, asset_type="crypto")
    info = info or {}
    report.name = info.get("longName") or CRYPTO_NAMES.get(symbol) or symbol
    report.price = history_closes[-1] if history_closes else None
    report.sma_200w = compute_sma(history_closes)
    if report.price is not None and report.sma_200w is not None:
        report.below_sma_200w = report.price < report.sma_200w
        report.gap_to_sma_pct = (report.sma_200w - report.price) / report.sma_200w * 100
    report.drawdown_from_ath_pct = compute_drawdown_pct(history_closes)
    trend = sma_trend_positive(history_closes)
    report.buffett_score = 0

    if report.below_sma_200w:
        report.reasons.append("Cours sous la moyenne mobile 200 semaines (zone d'accumulation historique)")
        report.buffett_score += 1
    if isinstance(report.drawdown_from_ath_pct, (int, float)) and report.drawdown_from_ath_pct >= 40:
        report.reasons.append(f"Drawdown de {report.drawdown_from_ath_pct:.0f}% par rapport a l'ATH")
        report.buffett_score += 1
    if trend is True:
        report.reasons.append("Tendance long terme intacte (MM200 semaines ascendante)")
        report.buffett_score += 1
    elif trend is None:
        report.reasons.append("Historique insuffisant pour juger la tendance long terme")

    report.alerts = list(report.reasons)
    return report


def build_etf_report(symbol: str, history_closes: list[float], info: dict | None = None) -> AssetReport:
    report = AssetReport(symbol=symbol, asset_type="etf")
    info = info or {}
    report.name = info.get("longName") or info.get("shortName") or symbol
    report.price = history_closes[-1] if history_closes else None
    report.sma_200w = compute_sma(history_closes)
    if report.price is not None and report.sma_200w is not None:
        report.below_sma_200w = report.price < report.sma_200w
        report.gap_to_sma_pct = (report.sma_200w - report.price) / report.sma_200w * 100
    report.drawdown_from_ath_pct = compute_drawdown_pct(history_closes)
    trend = sma_trend_positive(history_closes)
    report.buffett_score = 0

    if report.below_sma_200w:
        report.reasons.append("Cours sous la moyenne mobile 200 semaines")
        report.buffett_score += 1
    if isinstance(report.drawdown_from_ath_pct, (int, float)) and report.drawdown_from_ath_pct >= 20:
        report.reasons.append(f"Drawdown de {report.drawdown_from_ath_pct:.0f}% par rapport au plus haut historique")
        report.buffett_score += 1
    if trend is True:
        report.reasons.append("Tendance long terme intacte (MM200 semaines ascendante)")
        report.buffett_score += 1
    elif trend is None:
        report.reasons.append("Historique insuffisant pour juger la tendance long terme")

    report.alerts = list(report.reasons)
    return report


def is_opportunity(report: AssetReport, min_buffett_score: int) -> bool:
    if report.error or not report.below_sma_200w:
        return False
    if report.asset_type == "stock":
        return report.buffett_score >= min_buffett_score
    return report.buffett_score >= min_buffett_score


def build_email_html(alerts: list[AssetReport]) -> str:
    rows = []
    for a in alerts:
        label = f"{a.name} ({a.symbol})" if a.name else a.symbol
        gap = f"-{a.gap_to_sma_pct:.1f}%" if a.gap_to_sma_pct is not None else "n/a"
        drawdown = f"{a.drawdown_from_ath_pct:.0f}%" if a.drawdown_from_ath_pct is not None else "n/a"
        reasons = "<br>".join(a.reasons) if a.reasons else "-"
        price = f"{a.price:,.2f}" if a.price is not None else "n/a"
        sma = f"{a.sma_200w:,.2f}" if a.sma_200w is not None else "n/a"
        rows.append(
            "<tr>"
            f"<td><b>{label}</b> ({a.asset_type})</td>"
            f"<td>{price}</td><td>{sma}</td><td>{gap}</td><td>{drawdown}</td>"
            f"<td>{a.buffett_score}/5</td><td>{reasons}</td>"
            "</tr>"
        )
    return (
        "<h2>Opportunites detectees : cours sous la MM200 semaines avec fondamentaux solides</h2>"
        "<p>Les actifs suivants sont sous leur moyenne mobile de 200 semaines tout en respectant "
        "les criteres de qualite facon Buffett. Ce sont des zones historiques d'achat.</p>"
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<tr><th>Actif</th><th>Cours</th><th>MM200 sem.</th><th>Ecart</th>"
        "<th>Drawdown ATH</th><th>Score Buffett</th><th>Raisons</th></tr>"
        + "".join(rows)
        + "</table>"
        "<p style='color:gray'>Analyse automatique quotidienne. Ne constitue pas un conseil en investissement.</p>"
    )


@workflows.activity(name="fetch-stock-report")
async def fetch_stock_report(symbol: str) -> AssetReport:
    import asyncio

    import yfinance as yf

    def _fetch() -> AssetReport:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="10y", interval="1wk")
        closes = [float(c) for c in history["Close"].dropna().tolist()]
        if not closes:
            return AssetReport(symbol=symbol, asset_type="stock", error="Aucune donnee de cours")
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            info = {}
        return build_stock_report(symbol, closes, info)

    return await asyncio.to_thread(_fetch)


@workflows.activity(name="fetch-crypto-report")
async def fetch_crypto_report(symbol: str) -> AssetReport:
    import asyncio

    import yfinance as yf

    def _fetch() -> AssetReport:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="10y", interval="1wk")
        closes = [float(c) for c in history["Close"].dropna().tolist()]
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            info = {}
        return build_crypto_report(symbol, closes, info)

    return await asyncio.to_thread(_fetch)


@workflows.activity(name="fetch-etf-report")
async def fetch_etf_report(symbol: str) -> AssetReport:
    import asyncio

    import yfinance as yf

    def _fetch() -> AssetReport:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="10y", interval="1wk")
        closes = [float(c) for c in history["Close"].dropna().tolist()]
        if not closes:
            return AssetReport(symbol=symbol, asset_type="etf", error="Aucune donnee de cours")
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            info = {}
        return build_etf_report(symbol, closes, info)

    return await asyncio.to_thread(_fetch)


@workflows.activity(name="send-alert-email")
async def send_alert_email(recipient_email: str, subject: str, html: str) -> bool:
    import os

    import httpx

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY manquant dans l'environnement du worker")
    from_email = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": from_email,
                "to": [recipient_email],
                "subject": subject,
                "html": html,
            },
        )
        response.raise_for_status()
    return True


@workflows.workflow.define(
    name="market-buffett-scan",
    workflow_display_name="Surveillance Bourse & Crypto MM200/Buffett",
    workflow_description=(
        "Scan quotidien des actions et cryptos : detecte les actifs sous leur moyenne mobile "
        "de 200 semaines qui respectent les criteres Buffett, et envoie une alerte e-mail."
    ),
)
class MarketBuffettScanWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, input: ScanInput) -> ScanResult:
        reports: list[AssetReport] = []
        for symbol in input.stocks:
            reports.append(await fetch_stock_report(symbol))
        for symbol in input.cryptos:
            reports.append(await fetch_crypto_report(symbol))
        for symbol in input.etfs:
            reports.append(await fetch_etf_report(symbol))

        alerts = [
            r
            for r in reports
            if not r.error and is_opportunity(r, input.min_buffett_score)
        ]
        result = ScanResult(
            scanned=len(reports),
            alerts=alerts,
            dry_run=input.dry_run,
        )
        if alerts and not input.dry_run:
            subject = f"[Surveillance Marches] {len(alerts)} opportunite(s) sous la MM200 semaines"
            html = build_email_html(alerts)
            result.email_sent = await send_alert_email(input.recipient_email, subject, html)
        return result
