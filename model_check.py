"""Check educational 2D model CSV inputs without changing the source files."""
import argparse
import csv
import json
import math
from pathlib import Path


def validate(nodes_path, members_path):
    errors = []

    def issue(path, line, code, message):
        errors.append({"file": Path(path).name, "line": line, "code": code, "message": message})

    def rows(path, columns):
        try:
            with Path(path).open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream, strict=True)
                header = reader.fieldnames
                if header is None or len(header) != len(columns) or set(header) != set(columns):
                    issue(path, 1, "HEADER", "Expected exactly these columns: " + ", ".join(columns))
                    return
                try:
                    for row in reader:
                        if None in row or any(value is None for value in row.values()):
                            issue(path, reader.line_num, "ROW_WIDTH", "Row has a different number of fields from the header")
                            continue
                        yield reader.line_num, {key: value.strip() for key, value in row.items()}
                except csv.Error as exc:
                    issue(path, reader.line_num, "CSV", str(exc))
        except (OSError, UnicodeError) as exc:
            issue(path, None, "READ", str(exc))

    nodes = {}
    seen_nodes = set()
    for line, row in rows(nodes_path, ["node_id", "x_m", "y_m"]):
        node_id = row["node_id"]
        if not node_id:
            issue(nodes_path, line, "NODE_ID", "node_id must not be empty")
            continue
        if node_id in seen_nodes:
            issue(nodes_path, line, "DUPLICATE_NODE", "Repeated node_id: " + node_id)
            continue
        seen_nodes.add(node_id)
        try:
            xy = (float(row["x_m"]), float(row["y_m"]))
            if not all(math.isfinite(value) for value in xy):
                raise ValueError("nonfinite coordinate")
        except ValueError:
            issue(nodes_path, line, "COORDINATE", "x_m and y_m must be finite numbers")
            continue
        nodes[node_id] = xy

    if not nodes:
        issue(nodes_path, None, "NO_NODES", "No valid nodes were found")
    seen_members = set()
    valid_members = 0
    for line, row in rows(members_path, ["member_id", "start_node_id", "end_node_id"]):
        member_id = row["member_id"]
        if not member_id:
            issue(members_path, line, "MEMBER_ID", "member_id must not be empty")
            continue
        if member_id in seen_members:
            issue(members_path, line, "DUPLICATE_MEMBER", "Repeated member_id: " + member_id)
            continue
        seen_members.add(member_id)
        start, end = row["start_node_id"], row["end_node_id"]
        missing = sorted({key for key in (start, end) if key not in nodes})
        if missing:
            issue(members_path, line, "UNKNOWN_NODE", "Missing or invalid node reference: " + ", ".join(missing))
            continue
        if nodes[start] == nodes[end]:
            issue(members_path, line, "ZERO_LENGTH", "Both endpoints have identical coordinates")
            continue
        valid_members += 1
    if not valid_members:
        issue(members_path, None, "NO_MEMBERS", "No valid members were found")
    return {"ok": not errors, "valid_nodes": len(nodes), "valid_members": valid_members, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nodes", type=Path)
    parser.add_argument("members", type=Path)
    args = parser.parse_args()
    report = validate(args.nodes, args.members)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
