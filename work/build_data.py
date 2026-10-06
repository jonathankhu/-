# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""把 data/ 裡的三個標準 CSV 整理成網頁可以直接載入的 docs/data.js。

輸出是一個 JS 檔（不是 .json），指定 window.BI_DATA = {...}，
這樣網頁用 <script src="data.js"> 載入就能直接雙擊打開，
不需要另外架伺服器去 fetch 本機檔案。
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs" / "data.js"


def build_enrollment():
    df = pd.read_csv(DATA / "enrollment.csv", encoding="utf-8-sig")
    agg = (
        df.groupby(["semester", "college", "dept", "degree", "gender"], as_index=False)["count"]
        .sum()
    )
    agg["count"] = agg["count"].astype(int)
    return agg.to_dict(orient="records")


def build_leave():
    df = pd.read_csv(DATA / "leave.csv", encoding="utf-8-sig")
    agg = (
        df.groupby(
            ["semester", "college", "dept", "degree", "gender", "reason"], as_index=False
        )[["new_leave", "on_leave_end"]]
        .sum()
    )
    agg["new_leave"] = agg["new_leave"].astype(int)
    agg["on_leave_end"] = agg["on_leave_end"].astype(int)
    return agg.to_dict(orient="records")


def build_depts():
    df = pd.read_csv(DATA / "dept_mapping.csv", encoding="utf-8-sig")
    records = []
    for row in df.itertuples(index=False):
        aliases = str(row.aliases) if pd.notna(row.aliases) and str(row.aliases).strip() else ""
        records.append(
            {
                "dept": row.dept,
                "college": row.college,
                "aliases": [a for a in aliases.split(";") if a],
            }
        )
    return records


def main():
    enrollment = build_enrollment()
    leave = build_leave()
    depts = build_depts()

    total_1141 = sum(r["count"] for r in enrollment if r["semester"] == "114-1")
    assert total_1141 == 10035, f"114-1 在學人數合計應為 10035，實際是 {total_1141}"
    print(f"核對：114-1 在學人數合計 = {total_1141}（正確）")

    payload = {"enrollment": enrollment, "leave": leave, "depts": depts}
    js = "window.BI_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(js, encoding="utf-8")

    size_kb = OUT.stat().st_size / 1024
    print(
        f"寫入 {OUT}（{size_kb:.1f} KB）："
        f"enrollment {len(enrollment)} 列、leave {len(leave)} 列、depts {len(depts)} 筆"
    )


if __name__ == "__main__":
    main()
