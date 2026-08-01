from __future__ import annotations

import importlib
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from google.protobuf.message import Message
from grpc_tools import protoc


@dataclass
class ProtoSchema:
    proto_dir: Path
    out_dir: Path
    modules: list[ModuleType] = field(default_factory=list)
    _messages: dict[str, type[Message]] = field(default_factory=dict)

    def message(self, name: str) -> type[Message]:
        try:
            return self._messages[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._messages))
            raise KeyError(f"unknown protobuf message {name!r}; available: {available}") from exc


def protobuf(proto_dir: str | Path, *, include_dirs: list[str | Path] | None = None) -> ProtoSchema:
    root = Path(proto_dir).resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)

    proto_files = sorted(root.rglob("*.proto"))
    if not proto_files:
        raise FileNotFoundError(f"no .proto files found under {root}")

    out_dir = Path(tempfile.mkdtemp(prefix="be-the-cowboy-proto-"))
    includes = [root]
    if include_dirs:
        includes.extend(Path(path).resolve() for path in include_dirs)

    args = ["grpc_tools.protoc"]
    args.extend(f"-I{path}" for path in includes)
    args.append(f"--python_out={out_dir}")
    args.extend(str(path) for path in proto_files)

    result = protoc.main(args)
    if result != 0:
        raise RuntimeError(f"protoc failed with exit code {result}")

    sys.path.insert(0, str(out_dir))
    schema = ProtoSchema(proto_dir=root, out_dir=out_dir)
    try:
        for generated in sorted(out_dir.rglob("*_pb2.py")):
            module_name = ".".join(generated.relative_to(out_dir).with_suffix("").parts)
            module = importlib.import_module(module_name)
            schema.modules.append(module)
            collect_messages(schema, module)
    finally:
        try:
            sys.path.remove(str(out_dir))
        except ValueError:
            pass

    return schema


def collect_messages(schema: ProtoSchema, module: ModuleType) -> None:
    descriptor = getattr(module, "DESCRIPTOR")
    for message in descriptor.message_types_by_name.values():
        cls = getattr(module, message.name)
        schema._messages[message.full_name] = cls
        schema._messages[message.name] = cls
