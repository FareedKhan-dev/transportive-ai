"""data.py: real refund histories from UCI Online Retail II (CC BY 4.0, Chen 2012)."""
import pandas as pd


def load(path="data/online_retail_II.xlsx"):
    df = pd.concat(pd.read_excel(path, sheet_name=None).values(), ignore_index=True)
    df["pence"] = (df["Quantity"] * df["Price"] * 100).round().astype("int64")
    return df.dropna(subset=["Customer ID"])


def histories(df):
    cancel = df["Invoice"].astype(str).str.startswith("C")             # C marks a cancellation
    sales = df[~cancel].sort_values("InvoiceDate")
    totals, past, out = sales.groupby("Invoice")["pence"].sum(), sales.groupby(["Customer ID", "StockCode"]), {}
    for key, rows in df[cancel].groupby(["Customer ID", "StockCode"]):
        if key not in past.groups:
            continue
        earlier = past.get_group(key)
        for when, pence in zip(rows["InvoiceDate"], rows["pence"]):
            prior = earlier[earlier["InvoiceDate"] < when]
            if len(prior):
                inv = prior["Invoice"].iloc[-1]
                out.setdefault(inv, {"invoice": inv, "charged": int(totals[inv]), "refunds": []})["refunds"].append(-int(pence))
    return list(out.values())
