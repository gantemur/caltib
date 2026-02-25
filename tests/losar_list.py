from datetime import date
import caltib

TRADITIONS = [
    ("Karana", "karana"),
    ("Tsurphu", "tsurphu"),
    ("Phugpa", "phugpa"),
    ("Bhutan", "bhutan"),
    ("Mongol", "mongol"),
]

Y0, Y1 = 1700, 1950


def mmdd(d: date) -> str:
    return f"{d.month:02d}-{d.day:02d}"


def main():
    headers = ["Year"] + [name for name, _ in TRADITIONS]
    colw = [5] + [max(6, len(h)) for h in headers[1:]]

    line = "  ".join(h.ljust(w) for h, w in zip(headers, colw))
    print(line)
    print("-" * len(line))

    march_hits = []  # (date, year, tradition)

    for Y in range(Y0, Y1 + 1):
        row = [str(Y).ljust(colw[0])]
        for (name, eng), w in zip(TRADITIONS, colw[1:]):
            ny = caltib.new_year_day(Y, engine=eng)
            d = ny["date"]
            row.append(mmdd(d).ljust(w))
            if d.month == 3:
                march_hits.append((d, Y, name))
        print("  ".join(row))

    print("\nMarch New Year occurrences:")
    if not march_hits:
        print("(none)")
        return

    march_hits.sort()
    for d, Y, name in march_hits:
        print(f"{d.isoformat()}  {name}  (Y={Y})")


if __name__ == "__main__":
    main()