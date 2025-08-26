import pandas as pd

class PortfolioUtils:
    @staticmethod
    def calculate_holdings(transactions, price_lookup):
        if transactions.empty:
            return pd.DataFrame()
        transactions["signed_qty"] = transactions.apply(
            lambda x: x["qty"] if x["side"].upper() == "BUY" else -x["qty"], axis=1
        )
        grouped = transactions.groupby(["demat", "strategy", "symbol"], as_index=False).apply(
            lambda g: pd.Series({
                "net_qty": g["signed_qty"].sum(),
                "avg_price": ((g["qty"] * g["price"]).sum() / g["qty"].sum()) if g["qty"].sum() > 0 else 0
            })
        ).reset_index()
        grouped = grouped[grouped["net_qty"] > 0]
        grouped["cmp"] = grouped["symbol"].map(price_lookup).fillna(0)
        grouped["investment"] = grouped["net_qty"] * grouped["avg_price"]
        grouped["current_value"] = grouped["net_qty"] * grouped["cmp"]
        grouped["pnl"] = grouped["current_value"] - grouped["investment"]
        grouped["pnl_pct"] = (grouped["pnl"] / grouped["investment"] * 100).round(2)
        return grouped

    @staticmethod
    def get_mock_prices(symbols):
        import random
        return {s: random.uniform(100, 2000) for s in symbols}
