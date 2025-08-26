import streamlit as st
import pandas as pd
import datetime
from db.portfolio_db import PortfolioDB
from utils.portfolio_utils import PortfolioUtils
from io import BytesIO

class PortfolioUI:
    def get_top_performers(self, holdings, group_by=None, top_n=3, ascending=False):
        df = holdings.sort_values("pnl_pct", ascending=ascending)
        if group_by:
            df = df.groupby(group_by).head(top_n).copy()
        else:
            df = df.head(top_n).copy()
        total_value = df["current_value"].sum()
        df["allocation_%"] = (df["current_value"] / total_value * 100).round(2) if total_value != 0 else 0
        df["investment"] = df["investment"]
        # Select columns based on group_by
        cols = ["symbol", "pnl_pct", "allocation_%", "investment"]
        if group_by:
            cols.insert(1, group_by)
        else:
            cols = ["symbol", "strategy", "demat", "pnl_pct", "allocation_%", "investment"]
        return df[cols].reset_index(drop=True)
    def __init__(self):
        self.db = PortfolioDB()
        self.utils = PortfolioUtils()

    def sidebar(self):
        return st.sidebar.radio("Navigation", ["Upload Trades", "Upload Holdings", "Portfolio", "Cash Ledger", "Export", "Watchlist"])

    def upload_holdings(self):
        st.subheader("Upload Initial Holdings File (CSV/XLSX)")
        file = st.file_uploader("Choose file", type=["csv", "xlsx"], key="holdings")
        demat = st.text_input("Enter Demat", "Zerodha")
        strategy = st.text_input("Enter Strategy", "Long Term")
        if file:
            try:
                if file.name.endswith(".csv"):
                    df = pd.read_csv(file)
                    symbol_fields = ["Instrument", "Name", "symbol", "Symbol"]
                    qty_fields = ["Qty.", "Qty", "quantity"]
                    price_fields = ["Avg. cost", "Avg.", "ATP", "avg_price", "Price"]
                else:
                    df = pd.read_excel(file)
                    # Excel fields: Name, Exchange, Status, Action, Qty, ATP, LTP, LTP %, Gain/loss, Gain/loss %
                    # Also support: Client ID, Company Name, ISIN, MarketCap, Sector, Total Quantity, Avg Trading Price, LTP, Invested Value, Market Value, Overall Gain/Loss
                    symbol_fields = ["Company Name", "Name", "Instrument", "symbol", "Symbol"]
                    qty_fields = ["Total Quantity", "Qty", "Qty.", "quantity"]
                    price_fields = ["Avg Trading Price", "ATP", "Avg.", "Avg. cost", "Price", "avg_price"]
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"Error reading file: {e}")
                return
            date = datetime.date.today().isoformat()
            if st.button("Upload as Transactions"):
                errors = []
                success_count = 0
                for idx, row in df.iterrows():
                    symbol = next((row.get(f) for f in symbol_fields if row.get(f) is not None), None)
                    qty_val = next((row.get(f) for f in qty_fields if row.get(f) is not None), None)
                    price_val = next((row.get(f) for f in price_fields if row.get(f) is not None), None)
                    # fallback for Zerodha positions: sometimes qty is like '12 Shares'
                    if isinstance(qty_val, str) and "Share" in qty_val:
                        try:
                            qty_val = int(qty_val.split()[0])
                        except Exception:
                            qty_val = None
                    if not symbol or qty_val is None or price_val is None:
                        row_num = idx
                        errors.append(f"Row {row_num}: Missing required fields.")
                        continue
                    try:
                        qty = int(qty_val)
                        price = float(price_val)
                        self.db.insert_transaction(date, demat, symbol, qty, price, "BUY", strategy)
                        success_count += 1
                    except Exception as e:
                        row_num = idx
                        errors.append(f"Row {row_num}: {e}")
                if success_count:
                    st.success(f"{success_count} holdings uploaded as BUY transactions.")
                if errors:
                    st.error("Some rows failed to upload:")
                    for err in errors:
                        st.write(err)

    def upload_trades(self):
        st.subheader("Upload Daily Trade Log (CSV/XLSX)")
        file = st.file_uploader("Choose trade log", type=["csv", "xlsx"])
        demat = st.text_input("Enter Demat", "Zerodha")
        strategy = st.text_input("Enter Strategy", "Swing")
        if file:
            try:
                df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"Error reading file: {e}")
                return
            if st.button("Upload Trades"):
                errors = []
                success_count = 0
                for idx, row in df.iterrows():
                    symbol = row.get("Symbol") or row.get("symbol")
                    qty_val = row.get("Qty") or row.get("quantity")
                    price_val = row.get("Price") or row.get("price")
                    side = row.get("Side") or row.get("side") or "BUY"
                    if not symbol or qty_val is None or price_val is None:
                        row_num = idx
                        errors.append(f"Row {row_num}: Missing required fields.")
                        continue
                    try:
                        qty = int(qty_val)
                        price = float(price_val)
                        self.db.insert_transaction(str(row.get("Date") or datetime.date.today()), demat, symbol, qty, price, side.upper(), strategy)
                        success_count += 1
                    except Exception as e:
                        row_num = idx
                        errors.append(f"Row {row_num}: {e}")
                if success_count:
                    st.success(f"{success_count} trades uploaded.")
                if errors:
                    st.error("Some rows failed to upload:")
                    for err in errors:
                        st.write(err)

    def portfolio(self):
        st.subheader("Portfolio Overview")
        tx = self.db.fetch_transactions()
        if tx.empty:
            st.info("No transactions yet.")
        symbols = tx["symbol"].unique().tolist()
        prices = self.utils.get_mock_prices(symbols)
        try:
            holdings = self.utils.calculate_holdings(tx, prices)
        except Exception as e:
            st.error(f"Error calculating holdings: {e}")
            return
        if holdings.empty:
            st.info("No open positions.")
            return
        tab1, tab2, tab3, tab4 = st.tabs(["By Strategy", "By Demat", "Overall Portfolio", "Averaging Candidates"])
        with tab1:
            strat_group = holdings.groupby(["strategy"], as_index=False).agg({
                "pnl": "sum",
                "pnl_pct": "mean",
                "current_value": "sum",
                "net_qty": "sum"
            })
            total_value = strat_group["current_value"].sum()
            strat_group["allocation_%"] = (strat_group["current_value"] / total_value * 100).round(2) if total_value != 0 else 0
            st.dataframe(strat_group, use_container_width=True)
            st.write("#### Top Winners (by Strategy)")
            winners_strat = self.get_top_performers(holdings, group_by="strategy", top_n=3, ascending=False)
            st.markdown(self.df_to_html(winners_strat, 'pnl_pct', 'green'), unsafe_allow_html=True)
            st.write("#### Top Losers (by Strategy)")
            losers_strat = self.get_top_performers(holdings, group_by="strategy", top_n=3, ascending=True)
            st.markdown(self.df_to_html(losers_strat, 'pnl_pct', 'red'), unsafe_allow_html=True)
        with tab2:
            demat_group = holdings.groupby(["demat"], as_index=False).agg({
                "pnl": "sum",
                "pnl_pct": "mean",
                "current_value": "sum",
                "net_qty": "sum"
            })
            total_value = demat_group["current_value"].sum()
            demat_group["allocation_%"] = (demat_group["current_value"] / total_value * 100).round(2) if total_value != 0 else 0
            st.dataframe(demat_group, use_container_width=True)
            st.write("#### Top Winners (by Demat)")
            winners_demat = self.get_top_performers(holdings, group_by="demat", top_n=3, ascending=False)
            st.markdown(self.df_to_html(winners_demat, 'pnl_pct', 'green'), unsafe_allow_html=True)
            st.write("#### Top Losers (by Demat)")
            losers_demat = self.get_top_performers(holdings, group_by="demat", top_n=3, ascending=True)
            st.markdown(self.df_to_html(losers_demat, 'pnl_pct', 'red'), unsafe_allow_html=True)
        with tab3:
            st.write("### Overall Portfolio")
            overall_group = holdings.agg({
                "investment": "sum",
                "current_value": "sum",
                "pnl": "sum",
                "net_qty": "sum"
            })
            pnl_pct = (overall_group["pnl"] / overall_group["investment"] * 100) if overall_group["investment"] != 0 else 0
            num_holdings = len(holdings)
            avg_holding_size = overall_group["net_qty"] / num_holdings if num_holdings > 0 else 0
            metrics_table = pd.DataFrame({
                "Metric": [
                    "Total Invested",
                    "Current Value",
                    "PnL",
                    "PnL %",
                    "Number of Holdings",
                    "Avg Holding Size"
                ],
                "Value": [
                    f"₹{overall_group['investment']:.2f}",
                    f"₹{overall_group['current_value']:.2f}",
                    f"₹{overall_group['pnl']:.2f}",
                    f"{pnl_pct:.2f}%",
                    f"{num_holdings}",
                    f"{avg_holding_size:.2f}"
                ]
            })
            st.table(metrics_table)
            holdings_disp = holdings.copy().reset_index(drop=True)
            total_value = holdings_disp["current_value"].sum()
            holdings_disp["allocation_%"] = (holdings_disp["current_value"] / total_value * 100).round(2) if total_value != 0 else 0
            st.dataframe(holdings_disp.reset_index(drop=True), use_container_width=True)
            st.markdown("---")
            st.write("#### Top Winners (Overall)")
            winners = self.get_top_performers(holdings, group_by=None, top_n=5, ascending=False)
            st.markdown(self.df_to_html(winners, 'pnl_pct', 'green'), unsafe_allow_html=True)
            st.write("#### Top Losers (Overall)")
            losers = self.get_top_performers(holdings, group_by=None, top_n=5, ascending=True)
            st.markdown(self.df_to_html(losers, 'pnl_pct', 'red'), unsafe_allow_html=True)
            st.markdown("---")
        with tab4:
            threshold = st.slider("Averaging Trigger % (CMP below Avg Price)", 1, 50, 10)
            signal_rule = 1 - (threshold / 100)
            # Auto-detect price column
            price_col = None
            for col in ["cmp", "current_price", "price", "ltp", "close", "market_price"]:
                if col in holdings.columns:
                    price_col = col
                    break
            if price_col and "avg_price" in holdings.columns:
                candidates = holdings[holdings[price_col] < holdings["avg_price"] * signal_rule].copy().reset_index(drop=True)
                candidates["cmp_drop_%"] = ((candidates["avg_price"] - candidates[price_col]) / candidates["avg_price"] * 100).round(2)
                show_cols = ["symbol", price_col, "avg_price", "cmp_drop_%", "pnl_pct", "investment"]
                st.write(f"### Averaging Candidates ({len(candidates)})")
                if not candidates.empty:
                    st.dataframe(candidates[show_cols], use_container_width=True)
                else:
                    st.info("No averaging candidates found for the selected threshold.")
            elif not price_col:
                st.info("No price column (current_price, price, ltp, close, market_price) found in holdings.")
            else:
                st.info("No avg_price column found in holdings.")

    def df_to_html(self, df, color_col, color):
        if df.empty:
            return "<i>No data</i>"
        def get_style(col, val):
            if col == color_col:
                return f"color:{color};font-weight:bold;"
            if col == "allocation_%":
                return "color:blue;font-weight:bold;" if val > 0 else ""
            if col == "investment":
                return "color:orange;font-weight:bold;" if val > 0 else ""
            if col == "pnl":
                return "color:green;font-weight:bold;" if val > 0 else "color:red;font-weight:bold;"
            return ""
        html = '<table style="width:100%;border-collapse:collapse;">'
        html += "<tr>" + "".join([f"<th style='border:1px solid #ddd;padding:4px;text-align:left'>{col}</th>" for col in df.columns]) + "</tr>"
        for _, row in df.iterrows():
            html += "<tr>"
            for col in df.columns:
                val = row[col]
                style = get_style(col, val)
                html += f"<td style='border:1px solid #ddd;padding:4px;{style}'>{val}</td>"
            html += "</tr>"
        html += "</table>"
        return html

    def cash_ledger(self):
        st.subheader("Cash Balance Management")
        demat = st.text_input("Enter Demat", "Zerodha")
        amount = st.number_input("Amount (+ve deposit / -ve withdrawal)", value=0.0)
        note = st.text_input("Note", "Deposit/Withdraw")
        if st.button("Add Cash Entry"):
            self.db.insert_cash(datetime.date.today().isoformat(), demat, amount, note)
            st.success("Cash entry added.")
        st.dataframe(self.db.fetch_cash())

    def export(self):
        st.subheader("Export Transactions and Holdings")
        tx = self.db.fetch_transactions()
        if tx.empty:
            st.info("No data available.")
        else:
            prices = self.utils.get_mock_prices(tx["symbol"].unique())
            holdings = self.utils.calculate_holdings(tx, prices)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                tx.to_excel(writer, index=False, sheet_name="Transactions")
                holdings.to_excel(writer, index=False, sheet_name="Holdings")
            st.download_button("Download Excel", data=output.getvalue(), file_name="portfolio_export.xlsx")

    def watchlist(self):
        st.subheader("Watchlist & Social Tagging")
        with st.form("add_watchlist_form"):
            symbol = st.text_input("Symbol")
            tag = st.text_input("Tag (e.g. 'Momentum', 'Long Term', 'Social', etc.)")
            note = st.text_area("Note")
            submitted = st.form_submit_button("Add to Watchlist")
            if submitted and symbol:
                self.db.add_to_watchlist(symbol, tag, note)
                st.success(f"Added {symbol} to watchlist.")
        watchlist_df = self.db.fetch_watchlist()
        if not watchlist_df.empty:
            st.dataframe(watchlist_df)
            remove_id = st.number_input("Remove by ID", min_value=1, step=1)
            if st.button("Remove from Watchlist"):
                self.db.remove_from_watchlist(remove_id)
                st.success(f"Removed ID {remove_id} from watchlist.")
                watchlist_df = self.db.fetch_watchlist()
                st.dataframe(watchlist_df)
        else:
            st.info("Watchlist is empty.")
