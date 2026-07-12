from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    import originpro as op

    output_dir = Path("outputs/fig12_polygon_probe").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    svg_path = output_dir / "probe.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120" viewBox="0 0 200 120">'
        '<path d="M 10 110 L 70 15 L 190 95 Z" fill="#fcbf6e" stroke="#566b44" stroke-width="2"/>'
        "</svg>",
        encoding="utf-8",
    )
    result = {"status": "started", "objects": [], "svg_path": str(svg_path)}
    try:
        op.attach()
        op.new(asksave=False)
        graph = op.new_graph(lname="Fig12PolygonProbe", template="LINE")
        layer = graph[0]
        for object_type in (4, 6, 11):
            record = {"object_type": object_type}
            try:
                obj = layer.obj.GraphObjects.Add(object_type)
                record["created"] = obj is not None
                if obj is not None:
                    record["dir"] = [
                        name for name in dir(obj)
                        if any(token in name.lower() for token in ("set", "get", "data", "point", "vertex", "x", "y"))
                    ]
                    try:
                        record["object_type_readback"] = obj.GetObjectType()
                        record["type_name"] = obj.GetTypeName()
                    except Exception as exc:
                        record["type_error"] = f"{exc.__class__.__name__}: {exc}"
            except Exception as exc:
                record["created"] = False
                record["error"] = f"{exc.__class__.__name__}: {exc}"
            result["objects"].append(record)
        commands = [
            ("layer_s", layer, f'draw -paths -s fig12_path_layer_s "{svg_path.as_posix()}";'),
            ("layer_plain", layer, f'draw -paths fig12_path_layer_plain "{svg_path.as_posix()}";'),
            ("layer_d", layer, f'draw -paths -d fig12_path_layer_d "{svg_path.as_posix()}";'),
            ("graph_s", graph, f'draw -paths -s fig12_path_graph_s "{svg_path.as_posix()}";'),
            ("graph_plain", graph, f'draw -paths fig12_path_graph_plain "{svg_path.as_posix()}";'),
            ("graph_d", graph, f'draw -paths -d fig12_path_graph_d "{svg_path.as_posix()}";'),
        ]
        result["path_commands"] = []
        for name, owner, command in commands:
            record = {"name": name, "command": command}
            try:
                record["return"] = owner.lt_exec(command)
            except Exception as exc:
                record["error"] = f"{exc.__class__.__name__}: {exc}"
            result["path_commands"].append(record)
        result["path_objects_after_import"] = []
        for item in layer.obj.GraphObjects:
            record = {
                "name": item.GetName(),
                "object_type": item.GetObjectType(),
                "type_name": item.GetTypeName(),
            }
            if record["object_type"] == 34:
                record["dir"] = [
                    name for name in dir(item)
                    if any(token in name.lower() for token in ("set", "get", "data", "point", "path", "x", "y", "dx", "dy"))
                ]
                for prop in ("GetX", "GetY", "GetDX", "GetDY", "GetLeft", "GetTop", "GetWidth", "GetHeight"):
                    try:
                        record[prop] = getattr(item, prop)()
                    except Exception as exc:
                        record[prop] = f"{exc.__class__.__name__}: {exc}"
            result["path_objects_after_import"].append(record)
        result["path_object_supported"] = any(
            item.get("object_type") == 34
            and str(item.get("name", "")).upper() in {
                "FIG12_PATH_LAYER_PLAIN", "FIG12_PATH_GRAPH_PLAIN"
            }
            for item in result["path_objects_after_import"]
        )
        png_path = output_dir / "probe.png"
        opju_path = output_dir / "probe.opju"
        graph.save_fig(str(png_path), type="png", replace=True, width=805)
        op.save(str(opju_path))
        result["png_path"] = str(png_path)
        result["png_exists"] = png_path.is_file()
        result["opju_path"] = str(opju_path)
        result["opju_exists"] = opju_path.is_file()
        result["status"] = "ok" if result["path_object_supported"] else "unsupported"
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{exc.__class__.__name__}: {exc}"
    finally:
        try:
            op.detach()
            result["release"] = "op.detach()"
        except Exception as exc:
            result["release"] = f"op.detach() failed: {exc.__class__.__name__}: {exc}"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
