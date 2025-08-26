

import streamlit as st
from ui.portfolio_ui import PortfolioUI

st.title("📊 Multi-Demat Portfolio Tracker")
ui = PortfolioUI()
menu = ui.sidebar()

if menu == "Upload Holdings":
    ui.upload_holdings()
elif menu == "Upload Trades":
    ui.upload_trades()
elif menu == "Portfolio":
    ui.portfolio()
elif menu == "Cash Ledger":
    ui.cash_ledger()
elif menu == "Export":
    ui.export()
elif menu == "Watchlist":
    ui.watchlist()
