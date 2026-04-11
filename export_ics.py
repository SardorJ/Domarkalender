import argparse
import os
from app import write_calendar_ics


def main() -> int:
    parser = argparse.ArgumentParser(description="Export uppdrag CSV to ICS.")
    parser.add_argument("--csv", default=os.environ.get("UPPDRAG_CSV_PATH", "uppdrag.csv"))
    parser.add_argument("--out", default="calendar.ics")
    args = parser.parse_args()

    write_calendar_ics(args.csv, args.out)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
