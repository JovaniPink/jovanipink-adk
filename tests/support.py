from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable


def rewrite_archive(
    payload: bytes,
    *,
    mutate: dict[str, bytes] | None = None,
    transform_json: dict[str, Callable[[dict[str, object]], None]] | None = None,
    append: list[tuple[zipfile.ZipInfo | str, bytes]] | None = None,
) -> bytes:
    mutate = mutate or {}
    transform_json = transform_json or {}
    output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(payload), "r") as source,
        zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target,
    ):
        for item in source.infolist():
            content = source.read(item)
            if item.filename in mutate:
                content = mutate[item.filename]
            if item.filename in transform_json:
                value = json.loads(content)
                transform_json[item.filename](value)
                content = json.dumps(
                    value, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            target.writestr(item, content)
        for name, content in append or []:
            target.writestr(name, content)
    return output.getvalue()
