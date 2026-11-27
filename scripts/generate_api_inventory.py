#!/usr/bin/env python3
"""Generate a stable declaration inventory from the checked-out metal-cpp headers.

The parser intentionally records source declarations instead of trying to
generate Rust bindings.  The inventory is the review boundary: code can use
objc2 or a hand-audited Objective-C declaration, but every metal-cpp symbol
must first appear here and then receive a coverage mapping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable


FRAMEWORKS = ("Foundation", "Metal", "MetalFX", "QuartzCore")
PRIVATE_HEADERS = {
    "CAPrivate.hpp",
    "MTLFXPrivate.hpp",
    "MTLPrivate.hpp",
    "NSPrivate.hpp",
}
SUPPORT_HEADERS = {
    "CADefines.hpp",
    "MTLDefines.hpp",
    "MTLHeaderBridge.hpp",
    "MTLVersion.hpp",
    "NSDefines.hpp",
    "NSObjCRuntime.hpp",
}
UMBRELLA_HEADERS = {"Foundation.hpp", "Metal.hpp", "MetalFX.hpp", "QuartzCore.hpp"}
INTERNAL_MACRO_PREFIXES = (
    "_NS_",
    "_MTL",
    "_CA",
    "_MTLFX",
    "_CAPRIVATE",
    "NS_",
    "MTL_",
    "MTLFX_",
    "CA_",
)


def mask_source(source: str) -> str:
    """Remove comments and literals while preserving byte positions and lines."""

    source = re.sub(
        r"//[^\n]*|/\*.*?\*/",
        lambda match: "".join("\n" if char == "\n" else " " for char in match.group()),
        source,
        flags=re.DOTALL,
    )
    return re.sub(
        r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
        lambda match: "".join("\n" if char == "\n" else " " for char in match.group()),
        source,
    )


def matching_brace(source: str, opening: int) -> int | None:
    pairs = {"{": "}", "(": ")", "[": "]"}
    closing = pairs[source[opening]]
    depth = 0
    for index in range(opening, len(source)):
        char = source[index]
        if char == source[opening]:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
    return None


def line_number(source: str, position: int) -> int:
    return source.count("\n", 0, position) + 1


def compact(statement: str) -> str:
    return re.sub(r"\s+", " ", statement).strip()


def namespace_at(source: str, position: int) -> str:
    ranges: list[tuple[int, int, str]] = []
    for match in re.finditer(r"\bnamespace\s+([A-Za-z_]\w*(?:::\w+)*)\s*\{", source):
        end = matching_brace(source, source.find("{", match.start()))
        if end is not None and match.start() < position < end:
            ranges.append((match.start(), end, match.group(1)))
    ranges.sort()
    return "::".join(name for _, _, name in ranges)


def inside_type(position: int, type_ranges: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        item
        for item in type_ranges
        if item["body_start"] < position < item["body_end"]
    ]
    return min(candidates, key=lambda item: item["body_end"] - item["body_start"], default=None)


def split_top_level(body: str) -> list[str]:
    statements: list[str] = []
    start = 0
    braces = parens = brackets = 0
    for index, char in enumerate(body):
        if char == "{":
            braces += 1
        elif char == "}":
            braces = max(0, braces - 1)
        elif char == "(":
            parens += 1
        elif char == ")":
            parens = max(0, parens - 1)
        elif char == "[":
            brackets += 1
        elif char == "]":
            brackets = max(0, brackets - 1)
        elif char == ";" and braces == parens == brackets == 0:
            statements.append(body[start : index + 1])
            start = index + 1
    trailing = body[start:].strip()
    if trailing:
        statements.append(trailing)
    return statements


def remove_private_implementation_blocks(source: str) -> str:
    """Remove nested preprocessor blocks used for metal-cpp implementation glue."""

    lines = source.splitlines(keepends=True)
    output: list[str] = []
    skipping = False
    depth = 0
    for line in lines:
        if not skipping and re.search(r"^\s*#if\s+defined\([^)]*PRIVATE_IMPLEMENTATION", line):
            skipping = True
            depth = 1
            output.append("".join("\n" if char == "\n" else " " for char in line))
            continue
        if skipping:
            if re.match(r"^\s*#if\b", line):
                depth += 1
            elif re.match(r"^\s*#endif\b", line):
                depth -= 1
            output.append("".join("\n" if char == "\n" else " " for char in line))
            if depth == 0:
                skipping = False
            continue
        output.append(line)
    return "".join(output)


def enum_members(body: str) -> list[tuple[str, str | None]]:
    members: list[tuple[str, str | None]] = []
    start = 0
    parens = brackets = braces = 0
    pieces: list[str] = []
    for char in body:
        if char == "(":
            parens += 1
        elif char == ")":
            parens = max(0, parens - 1)
        elif char == "[":
            brackets += 1
        elif char == "]":
            brackets = max(0, brackets - 1)
        elif char == "{":
            braces += 1
        elif char == "}":
            braces = max(0, braces - 1)
        elif char == "," and parens == brackets == braces == 0:
            pieces.append(body[start : body.find(",", start)])
            start = body.find(",", start) + 1
    pieces.append(body[start:])
    for piece in pieces:
        piece = compact(piece)
        if not piece:
            continue
        match = re.match(r"([A-Za-z_]\w*)\s*(?:=\s*(.*))?$", piece)
        if match:
            members.append((match.group(1), match.group(2)))
    return members


def header_role(header: Path) -> str:
    if header.name in PRIVATE_HEADERS:
        return "private"
    if header.name in UMBRELLA_HEADERS:
        return "umbrella"
    if header.name in SUPPORT_HEADERS:
        return "support"
    return "public"


def add_record(
    records: list[dict[str, Any]],
    *,
    framework: str,
    header: str,
    source: str,
    position: int,
    kind: str,
    name: str,
    qualified_name: str,
    signature: str,
    parent: str | None = None,
    visibility: str = "public",
    value: str | None = None,
) -> None:
    records.append(
        {
            "id": f"{framework}/{header}:{line_number(source, position)}:{kind}:{qualified_name}",
            "framework": framework,
            "header": header,
            "line": line_number(source, position),
            "kind": kind,
            "name": name,
            "qualified_name": qualified_name,
            "parent": parent,
            "visibility": visibility,
            "signature": compact(signature),
            "value": compact(value) if value else None,
            "status": "unmapped",
            "mapping": None,
        }
    )


def scan_header(framework: str, root: Path, path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    relative = path.relative_to(root).as_posix()
    raw = path.read_text(encoding="utf-8")
    source = mask_source(raw)
    # metal-cpp puts all inline Objective-C message-send implementations after
    # the public declaration block.  They are implementation detail, not a
    # second API surface, and otherwise look like duplicate functions and
    # constants to a source scanner.
    source = remove_private_implementation_blocks(source)
    inline_marker = re.search(r"(?m)^\s*_(?:NS|MTL|MTLFX|CA)_INLINE\b", source)
    if inline_marker:
        source = source[: inline_marker.start()]
    role = header_role(path)
    header = {
        "path": relative,
        "role": role,
        "sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "lines": raw.count("\n") + 1,
    }
    records: list[dict[str, Any]] = []
    if role == "private":
        return header, records

    type_ranges: list[dict[str, Any]] = []
    class_pattern = re.compile(
        r"(?:template\s*<[^{}]*>\s*)*\b(class|struct)\s+(?:_NS_EXPORT\s+)?"
        r"([A-Za-z_]\w*)\s*(?:final\s*)?(?::[^{};]*)?\{"
    )
    for match in class_pattern.finditer(source):
        opening = source.find("{", match.start())
        closing = matching_brace(source, opening)
        if closing is None:
            continue
        namespace = namespace_at(source, match.start())
        name = match.group(2)
        qualified = f"{namespace}::{name}" if namespace else name
        item = {
            "body_start": opening,
            "body_end": closing,
            "kind": match.group(1),
            "name": name,
            "qualified_name": qualified,
        }
        type_ranges.append(item)
        add_record(
            records,
            framework=framework,
            header=relative,
            source=source,
            position=match.start(),
            kind=match.group(1),
            name=name,
            qualified_name=qualified,
            signature=source[match.start() : opening + 1],
        )

    enum_pattern = re.compile(
        r"\b_(NS|MTL|MTLFX|CA)_(ENUM|OPTIONS)\s*\(\s*([^,]+),\s*([A-Za-z_]\w*)\s*\)\s*\{"
    )
    enum_ranges: list[tuple[int, int]] = []
    for match in enum_pattern.finditer(source):
        opening = source.find("{", match.start())
        closing = matching_brace(source, opening)
        if closing is None:
            continue
        namespace = namespace_at(source, match.start())
        name = match.group(4)
        qualified = f"{namespace}::{name}" if namespace else name
        kind = "options" if match.group(2) == "OPTIONS" else "enum"
        enum_ranges.append((opening, closing))
        add_record(
            records,
            framework=framework,
            header=relative,
            source=source,
            position=match.start(),
            kind=kind,
            name=name,
            qualified_name=qualified,
            signature=source[match.start() : opening + 1],
            value=match.group(3),
        )
        if kind == "options":
            add_record(
                records,
                framework=framework,
                header=relative,
                source=source,
                position=match.start(),
                kind="alias",
                name=name,
                qualified_name=qualified,
                signature=f"using {name} = {match.group(3)};",
                value=match.group(3),
            )
        for member, value in enum_members(source[opening + 1 : closing]):
            add_record(
                records,
                framework=framework,
                header=relative,
                source=source,
                position=opening + 1,
                kind="enum_member",
                name=member,
                qualified_name=f"{qualified}::{member}",
                signature=member if value is None else f"{member} = {value}",
                parent=qualified,
                value=value,
            )

    bare_enum_pattern = re.compile(
        r"\benum(?:\s+class)?\s+([A-Za-z_]\w*)\s*(?::\s*[^{}]+)?\{"
    )
    for match in bare_enum_pattern.finditer(source):
        if any(start <= match.start() <= end for start, end in enum_ranges):
            continue
        opening = source.find("{", match.start())
        closing = matching_brace(source, opening)
        if closing is None:
            continue
        namespace = namespace_at(source, match.start())
        name = match.group(1)
        qualified = f"{namespace}::{name}" if namespace else name
        add_record(
            records,
            framework=framework,
            header=relative,
            source=source,
            position=match.start(),
            kind="enum",
            name=name,
            qualified_name=qualified,
            signature=source[match.start() : opening + 1],
        )
        for member, value in enum_members(source[opening + 1 : closing]):
            add_record(
                records,
                framework=framework,
                header=relative,
                source=source,
                position=opening + 1,
                kind="enum_member",
                name=member,
                qualified_name=f"{qualified}::{member}",
                signature=member if value is None else f"{member} = {value}",
                parent=qualified,
                value=value,
            )

    for item in type_ranges:
        body = source[item["body_start"] + 1 : item["body_end"]]
        body = re.sub(r"(?m)^\s*(public|private|protected)\s*:", r"\n\1:;\n", body)
        access = "public" if item["kind"] == "struct" else "private"
        offset = item["body_start"] + 1
        for statement in split_top_level(body):
            clean = compact(statement)
            if not clean:
                continue
            access_match = re.match(r"^(public|private|protected)\s*:\s*;?$", clean)
            if access_match:
                access = access_match.group(1)
                continue
            if access != "public":
                continue
            if re.search(r"\b(class|struct|enum)\b", clean):
                continue
            if "(" in clean and ")" in clean and not re.match(r"^(if|for|while|switch)\s*\(", clean):
                method_name = re.search(r"([~A-Za-z_]\w*|operator\s*[^\s(]+)\s*\(", clean)
                name = method_name.group(1).replace(" ", "") if method_name else item["name"]
                add_record(
                    records,
                    framework=framework,
                    header=relative,
                    source=source,
                    position=offset + body.find(statement),
                    kind="method",
                    name=name,
                    qualified_name=f"{item['qualified_name']}::{name}",
                    signature=clean,
                    parent=item["qualified_name"],
                )
            elif clean.endswith(";") and not clean.startswith(("friend ", "static_assert")):
                field_name = re.search(r"([A-Za-z_]\w*)\s*(?:\[[^]]*\])?\s*;\s*$", clean)
                if field_name:
                    name = field_name.group(1)
                    add_record(
                        records,
                        framework=framework,
                        header=relative,
                        source=source,
                        position=offset + body.find(statement),
                        kind="field",
                        name=name,
                        qualified_name=f"{item['qualified_name']}::{name}",
                        signature=clean,
                        parent=item["qualified_name"],
                    )

    alias_pattern = re.compile(r"\busing\s+([A-Za-z_]\w*)\s*=\s*([^;]+);|\btypedef\s+([^;]+?)\s+([A-Za-z_]\w*)\s*;")
    for match in alias_pattern.finditer(source):
        if inside_type(match.start(), type_ranges) is not None:
            continue
        name = match.group(1) or match.group(4)
        if not name or name.startswith("_") or name == "name":
            continue
        namespace = namespace_at(source, match.start())
        qualified = f"{namespace}::{name}" if namespace else name
        rhs = match.group(2) or match.group(3) or ""
        add_record(
            records,
            framework=framework,
            header=relative,
            source=source,
            position=match.start(),
            kind="alias",
            name=name,
            qualified_name=qualified,
            signature=source[match.start() : source.find(";", match.start()) + 1],
            value=rhs,
        )

    constant_pattern = re.compile(
        r"(?m)^\s*_(?:NS|MTL|MTLFX|CA)_CONST\s*\([^,]+,\s*([A-Za-z_]\w*)\s*\)\s*;"
        r"|^\s*(?:(?:static\s+)?constexpr|const)\s+[A-Za-z_:][^;=()]*\s+([A-Za-z_]\w*)\s*=\s*[^;]+;"
    )
    for match in constant_pattern.finditer(source):
        if inside_type(match.start(), type_ranges) is not None:
            continue
        name = match.group(1) or match.group(2)
        if not name or name.startswith("_") or name in {"if", "for", "while"}:
            continue
        namespace = namespace_at(source, match.start())
        qualified = f"{namespace}::{name}" if namespace else name
        add_record(
            records,
            framework=framework,
            header=relative,
            source=source,
            position=match.start(),
            kind="constant",
            name=name,
            qualified_name=qualified,
            signature=source[match.start() : source.find(";", match.start()) + 1],
        )

    function_pattern = re.compile(r"(?m)^\s*(?!#)(?!class\b|struct\b|enum\b)([^;{}\n]*\([^;{}\n]*\))\s*;")
    for match in function_pattern.finditer(source):
        if inside_type(match.start(), type_ranges) is not None:
            continue
        statement = compact(match.group(1) + ";")
        if not statement or statement.startswith(("using ", "typedef ")):
            continue
        name_match = re.search(r"([A-Za-z_]\w*)\s*\([^()]*\)\s*;?$", statement)
        if not name_match:
            continue
        name = name_match.group(1)
        if name.startswith("_"):
            continue
        namespace = namespace_at(source, match.start())
        qualified = f"{namespace}::{name}" if namespace else name
        add_record(
            records,
            framework=framework,
            header=relative,
            source=source,
            position=match.start(),
            kind="function",
            name=name,
            qualified_name=qualified,
            signature=statement,
        )

    macro_pattern = re.compile(r"(?m)^\s*#define\s+([A-Za-z_]\w*)\b(?:\([^\n]*\))?")
    for match in macro_pattern.finditer(raw):
        name = match.group(1)
        if name.startswith(INTERNAL_MACRO_PREFIXES) or name in {"MTLSTR"}:
            if name != "MTLSTR":
                continue
        add_record(
            records,
            framework=framework,
            header=relative,
            source=raw,
            position=match.start(),
            kind="macro",
            name=name,
            qualified_name=name,
            signature=compact(raw[match.start() : raw.find("\n", match.start())]),
        )
    return header, records


def reference_digest(root: Path, headers: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for header in headers:
        digest.update(header["path"].encode())
        digest.update(b"\0")
        digest.update(header["sha256"].encode())
        digest.update(b"\n")
    return digest.hexdigest()


def git_revision(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def generate(root: Path) -> dict[str, Any]:
    headers: list[dict[str, Any]] = []
    declarations: list[dict[str, Any]] = []
    for framework in FRAMEWORKS:
        for path in sorted((root / framework).glob("*.hpp")):
            header, records = scan_header(framework, root, path)
            headers.append({"framework": framework, **header})
            declarations.extend(records)
    declarations.sort(key=lambda item: (item["framework"], item["header"], item["line"], item["kind"], item["qualified_name"], item["signature"]))
    for index, declaration in enumerate(declarations, start=1):
        declaration["ordinal"] = index
    return {
        "schema": 1,
        "generator": "scripts/generate_api_inventory.py",
        "reference": {
            "name": "Apple metal-cpp",
            "relative_root": "third_party/metal-cpp",
            "license": "Apache-2.0",
            "git_revision": git_revision(root),
            "header_count": len(headers),
            "content_sha256": reference_digest(root, headers),
        },
        "headers": headers,
        "declarations": declarations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, help="metal-cpp checkout root")
    parser.add_argument("--output", type=Path, default=Path("api/metal-cpp-inventory.json"))
    parser.add_argument("--check", action="store_true", help="fail if the checked-in inventory would change")
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    root = (args.reference or repository / "third_party" / "metal-cpp").resolve()
    if not root.is_dir():
        parser.error(f"reference root does not exist: {root}")
    inventory = generate(root)
    encoded = json.dumps(inventory, indent=2, sort_keys=False) + "\n"
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        if current != encoded:
            print(f"inventory drift detected: {args.output}")
            return 1
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(f"headers={len(inventory['headers'])} declarations={len(inventory['declarations'])}")
    print(f"reference_sha256={inventory['reference']['content_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
