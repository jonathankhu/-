# /// script
# requires-python = ">=3.10"
# dependencies = ["xlrd", "pandas"]
# ///
"""把 114-1 在學生人數統計表（.xls）轉成整齊的 CSV。

只讀第一個工作表，每一列輸出為 college, dept_raw, program_raw, gender, count。
"""
import re
from pathlib import Path

import pandas as pd
import xlrd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "東華大學統計資料" / "在學人數統計表" / "114-1在學生人數統計表1141020--網路公告-10035人.xls"
OUT = Path(__file__).resolve().parent / "enrollment_114-1.csv"

# col0（學制別）裡的「XX 合計N」是該學制區段的小計列，本身要排除，
# 但告訴我們接下來的資料列屬於哪個學制。碩士在職專班（碩專班）在原始檔的
# 學制別欄位從未出現過文字，只能從它的「合計3」小計列判斷。
HEADER_PROGRAM = {
    "博士班 合計1": "博士班",
    "碩士班 合計2": "碩士班",
    "碩專班 合計3": "碩士在職專班",
    "學士班 合計4": "學士班",
}
PROGRAM_LABELS = {"博士班", "碩士班", "學士班"}


def strip_note(s: str) -> str:
    return re.sub(r"[（(].*?[）)]", "", s).strip()


def resolve_merged_column(sh, col):
    """把一欄裡因合併儲存格而留白的格子，還原成合併範圍左上角的值。

    有一列（114-1 的「應用物理博士班一般組(106起)」那列）系所欄是空的，
    但它既不屬於上一個系所的合併範圍，也不屬於下一個系所的合併範圍——
    報表本身的合併範圍少算了一列。這種「孤兒列」無法用合併資訊還原，
    只能先標成 None，之後用下一列的值回填（內容上它明顯是接在它之後
    才出現名稱的系所）。
    """
    n = sh.nrows
    merge_label = {}
    for r0, r1, c0, c1 in sh.merged_cells:
        if c0 == col:
            label = sh.cell_value(r0, col)
            for r in range(r0, r1):
                merge_label[r] = label

    values = []
    for r in range(n):
        raw = str(sh.cell_value(r, col)).strip()
        if raw:
            values.append(raw)
        elif r in merge_label:
            values.append(merge_label[r])
        else:
            values.append(None)  # 孤兒列，稍後回填

    last_seen = None
    for r in range(n - 1, -1, -1):
        if values[r] is not None:
            last_seen = values[r]
        else:
            values[r] = last_seen
    return values


def main():
    wb = xlrd.open_workbook(SRC, formatting_info=True)
    sh = wb.sheet_by_index(0)

    college_col = resolve_merged_column(sh, 1)
    dept_col = resolve_merged_column(sh, 2)

    rows = []
    program = None

    for r in range(sh.nrows):
        c0 = str(sh.cell_value(r, 0)).strip()

        if c0 == "備註：":
            break  # 以下都是備註文字，不是資料

        if c0 in HEADER_PROGRAM:
            program = HEADER_PROGRAM[c0]
            continue

        if c0 in PROGRAM_LABELS:
            program = c0

        if program is None:
            continue  # 標題列、表頭列、總計列

        dept = dept_col[r]
        if dept is None:
            continue

        female_raw = sh.cell_value(r, 5)
        male_raw = sh.cell_value(r, 6)
        female = int(female_raw) if female_raw != "" else 0
        male = int(male_raw) if male_raw != "" else 0

        rows.append((strip_note(college_col[r]), dept, program, "女", female))
        rows.append((strip_note(college_col[r]), dept, program, "男", male))

    df = pd.DataFrame(rows, columns=["college", "dept_raw", "program_raw", "gender", "count"])
    df = (
        df.groupby(["college", "dept_raw", "program_raw", "gender"], as_index=False, sort=False)["count"]
        .sum()
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"寫入 {OUT}，共 {len(df)} 列，總人數 {df['count'].sum()}")


if __name__ == "__main__":
    main()
