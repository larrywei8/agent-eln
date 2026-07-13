#!/usr/bin/env python3
"""ELN query wrapper: run SQL and print a table, zero config.

  python tools/query.py "SELECT type, count(*) FROM records GROUP BY 1"
  python tools/query.py --tsv "SELECT * FROM records LIMIT 5" > out.tsv
  python tools/query.py --json "SELECT ..."
  python tools/query.py --file queries/foo.sql

Tables: records(id,type,name,status,project,path,who,created_date,tags)
        edges(src,dst,rel)
        backlinks(id,backlink,value)
"""
import os, sys, csv, json, argparse
sys.path.insert(0, os.path.dirname(__file__))
import registry as R

DB = os.path.join(R.ROOT, "index", "data.duckdb")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sql", nargs="?", help="SQL query (alternative to --file)")
    ap.add_argument("--file", help="Read SQL from file")
    ap.add_argument("--tsv", action="store_true", help="TSV output")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    sql = open(args.file).read() if args.file else args.sql
    if not sql:
        ap.error("must provide SQL or --file")
    if not os.path.exists(DB):
        sys.exit(f"{DB} not found; run `python tools/index.py` first.")
    try:
        import duckdb
    except ImportError:
        sys.exit("duckdb required: pip install duckdb")

    con = duckdb.connect(DB, read_only=True)
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()

    if args.json:
        print(json.dumps([dict(zip(cols, r)) for r in rows], ensure_ascii=False, indent=2, default=str))
    elif args.tsv:
        w = csv.writer(sys.stdout, delimiter="\t")
        w.writerow(cols); w.writerows(rows)
    else:
        widths = [max(len(str(c)), *(len(str(r[i])) for r in rows) if rows else [0]) for i, c in enumerate(cols)]
        fmt = "  ".join(f"{{:<{w}}}" for w in widths)
        print(fmt.format(*cols))
        print(fmt.format(*("-" * w for w in widths)))
        for r in rows:
            print(fmt.format(*(str(x) if x is not None else "" for x in r)))
        print(f"\n({len(rows)} rows)")

if __name__ == "__main__":
    main()
