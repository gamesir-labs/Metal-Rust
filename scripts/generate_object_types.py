#!/usr/bin/env python3
"""Generate opaque owned RAII types for Objective-C framework classes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from generate_value_types import EXTENSIBLE_MANUAL_TYPES, MANUAL_TYPES, RUST_INTEGERS


NAMESPACES = {
    "CA": "quartz_core",
    "MTL": "metal",
    "MTL4": "metal4",
    "MTL4FX": "metal4_fx",
    "MTLFX": "metal_fx",
    "NS": "foundation",
}

CANONICAL_OBJECT_PATHS = {
    "MTL::Buffer": "crate::Buffer",
    "MTL::CompileOptions": "crate::CompileOptions",
    "MTL::Device": "crate::Device",
    "MTL::Function": "crate::Function",
    "MTL::Library": "crate::Library",
    "MTL::Texture": "crate::Texture",
}

PRIMITIVE_RETURNS = {
    "bool": "bool",
    "float": "f32",
    "double": "f64",
    "CFTimeInterval": "f64",
    "NS::UInteger": "usize",
    "UInteger": "usize",
    "size_t": "usize",
    "uint64_t": "u64",
    "uint32_t": "u32",
    "unsigned long long": "u64",
    "NS::Integer": "isize",
    "Integer": "isize",
    "int": "i32",
}

RUST_KEYWORDS = {
    "as", "break", "const", "continue", "crate", "else", "enum", "extern", "false",
    "fn", "for", "if", "impl", "in", "let", "loop", "match", "mod", "move", "mut",
    "pub", "ref", "return", "self", "Self", "static", "struct", "super", "trait",
    "true", "type", "unsafe", "use", "where", "while", "async", "await", "dyn",
}

CUSTOM_PROPERTY_SETTERS = {
    ("MTLFX::FrameInterpolatorDescriptor", "uiTextureFormat"): "setUITextureFormat",
    ("MTLFX::FrameInterpolatorBase", "uiTexture"): "setUITexture",
}

CUSTOM_PROPERTY_NAMES = {
    "uiTexture": "setUITexture",
    "uiTextureFormat": "setUITextureFormat",
}

# These concrete generated owners have stronger handwritten setters in the
# corresponding MetalFX module. The handwritten implementations validate
# dimensions/finiteness more strictly than a generic inherited-property shim.
INHERITED_PROPERTY_EXCLUSIONS = {
    "MTL4FX::TemporalScaler",
}

CUSTOM_STATIC_DEVICE_SELECTORS = {
    ("MTLFX::TemporalDenoisedScalerDescriptor", "supportedInputContentMinScale"): "supportedInputContentMinScaleForDevice",
    ("MTLFX::TemporalDenoisedScalerDescriptor", "supportedInputContentMaxScale"): "supportedInputContentMaxScaleForDevice",
}

MATRIX_PROPERTIES = {
    "MTLFX::TemporalDenoisedScalerBase": [
        ("worldToViewMatrix", "world_to_view_matrix", "setWorldToViewMatrix", "world_to_view", "set_world_to_view"),
        ("viewToClipMatrix", "view_to_clip_matrix", "setViewToClipMatrix", "view_to_clip", "set_view_to_clip"),
    ],
}


def property_setter(parent: str, name: str) -> str:
    return CUSTOM_PROPERTY_SETTERS.get(
        (parent, name),
        CUSTOM_PROPERTY_NAMES.get(name, f"set{name[0].upper()}{name[1:]}"),
    )


def base_class(
    declaration: dict[str, Any],
) -> str | None:
    signature = declaration.get("signature", "")
    match = re.search(
        r"public NS::(?:Copying|Referencing)<[^,]+,\s*([^>]+)>",
        signature,
    )
    if match is None:
        return None
    base = match.group(1).strip()
    return base if "::" in base else f"{declaration['qualified_name'].split('::', 1)[0]}::{base}"


def inherited_properties(
    declarations: list[dict[str, Any]],
    own: dict[str, list[Any]],
) -> dict[str, list[Any]]:
    bases = {
        declaration["qualified_name"]: base_class(declaration)
        for declaration in declarations
        if declaration["kind"] == "class"
    }
    result = {name: list(values) for name, values in own.items()}

    def collect(name: str, seen: set[str] | None = None) -> list[Any]:
        seen = set() if seen is None else seen
        if name in seen:
            return []
        seen.add(name)
        values = list(result.get(name, []))
        base = bases.get(name)
        if base:
            values.extend(collect(base, seen))
        return values

    for name in bases:
        if name in INHERITED_PROPERTY_EXCLUSIONS:
            continue
        combined = list(dict.fromkeys(collect(name)))
        if combined:
            result[name] = combined
    return result


def snake_case(name: str) -> str:
    result: list[str] = []
    for index, character in enumerate(name):
        if character.isupper() and index and (
            not name[index - 1].isupper()
            or (index + 1 < len(name) and name[index + 1].islower())
        ):
            result.append("_")
        result.append(character.lower())
    value = "".join(result)
    return f"r#{value}" if value in RUST_KEYWORDS else value


def method_parts(declaration: dict[str, Any]) -> tuple[str, str] | None:
    signature = declaration["signature"]
    try:
        arguments = signature.split("(", 1)[1].rsplit(")", 1)[0].strip()
        return_type = signature.split(declaration["name"], 1)[0].strip()
    except (IndexError, ValueError):
        return None
    if arguments or return_type.startswith("static "):
        return None
    return_type = return_type.removesuffix("const").strip()
    rust_type = PRIMITIVE_RETURNS.get(return_type)
    if rust_type is None:
        return None
    return rust_type, snake_case(declaration["name"])


def generated_property_methods(
    declarations: list[dict[str, Any]],
) -> dict[str, list[tuple[str, str, str, bool]]]:
    methods = [declaration for declaration in declarations if declaration["kind"] == "method"]
    names = {(declaration.get("parent"), declaration["name"]) for declaration in methods}
    result: dict[str, list[tuple[str, str, str, bool]]] = defaultdict(list)
    for declaration in methods:
        signature = declaration["signature"]
        parts = method_parts(declaration)
        name = declaration["name"]
        if parts is None or not name:
            continue
        setter = property_setter(declaration["parent"], name)
        writable = (declaration.get("parent"), setter) in names
        if not writable and not signature.rstrip().endswith(" const;"):
            continue
        rust_type, rust_name = parts
        result[declaration["parent"]].append((name, rust_name, rust_type, writable))
    return inherited_properties(declarations, result)


def enum_return_parts(
    declaration: dict[str, Any], declarations: list[dict[str, Any]]
) -> tuple[str, str] | None:
    if declaration["kind"] != "method":
        return None
    signature = declaration["signature"]
    arguments = signature.split("(", 1)[1].rsplit(")", 1)[0].strip()
    return_type = signature.split(declaration["name"], 1)[0].strip()
    if arguments or return_type.startswith("static "):
        return None
    namespace = declaration["parent"].split("::", 1)[0]
    qualified_type = return_type if "::" in return_type else f"{namespace}::{return_type}"
    types = {
        item["qualified_name"]: item
        for item in declarations
        if item["framework"] in {"Foundation", "Metal"}
        and item["kind"] in {"enum", "options"}
    }
    type_declaration = types.get(qualified_type)
    if type_declaration is None:
        return None
    raw_type = RUST_INTEGERS.get(type_declaration["value"])
    if raw_type is None:
        return None
    return qualified_type.rsplit("::", 1)[-1], raw_type


def generated_enum_properties(
    declarations: list[dict[str, Any]],
) -> dict[str, list[tuple[str, str, str, str, bool]]]:
    methods = [declaration for declaration in declarations if declaration["kind"] == "method"]
    names = {(declaration.get("parent"), declaration["name"]) for declaration in methods}
    result: dict[str, list[tuple[str, str, str, str, bool]]] = defaultdict(list)
    for declaration in methods:
        parts = enum_return_parts(declaration, declarations)
        name = declaration["name"]
        if parts is None or not name:
            continue
        setter = property_setter(declaration["parent"], name)
        writable = (declaration.get("parent"), setter) in names
        if not writable and not declaration["signature"].rstrip().endswith(" const;"):
            continue
        type_name, raw_type = parts
        result[declaration["parent"]].append(
            (name, snake_case(name), type_name, raw_type, writable)
        )
    return inherited_properties(declarations, result)


def generated_object_properties(
    declarations: list[dict[str, Any]],
) -> dict[str, list[tuple[str, str, str, bool]]]:
    methods = [declaration for declaration in declarations if declaration["kind"] == "method"]
    names = {(declaration.get("parent"), declaration["name"]) for declaration in methods}
    classes = {
        declaration["qualified_name"]
        for declaration in declarations
        if declaration["kind"] == "class" and "::" in declaration["qualified_name"]
    }
    result: dict[str, list[tuple[str, str, str, bool]]] = defaultdict(list)
    for declaration in methods:
        signature = declaration["signature"]
        arguments = signature.split("(", 1)[1].rsplit(")", 1)[0].strip()
        return_type = signature.split(declaration["name"], 1)[0].strip()
        if arguments or not return_type.endswith("*"):
            continue
        base = return_type.removeprefix("const ").removesuffix("*").strip()
        namespace = declaration["parent"].split("::", 1)[0]
        qualified_type = base if "::" in base else f"{namespace}::{base}"
        name = declaration["name"]
        setter = property_setter(declaration["parent"], name) if name else ""
        writable = (declaration.get("parent"), setter) in names
        if qualified_type not in classes or (
            not writable and not signature.rstrip().endswith(" const;")
        ):
            continue
        result[declaration["parent"]].append(
            (name, snake_case(name), qualified_type, writable)
        )
    return inherited_properties(declarations, result)


def generated_bool_setters(
    declarations: list[dict[str, Any]],
) -> dict[str, list[tuple[str, str]]]:
    methods = [declaration for declaration in declarations if declaration["kind"] == "method"]
    names = {(declaration.get("parent"), declaration["name"]) for declaration in methods}
    result: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for declaration in methods:
        name = declaration["name"]
        signature = declaration["signature"]
        if not name.startswith("set") or not signature.startswith("void "):
            continue
        arguments = signature.split("(", 1)[1].rsplit(")", 1)[0].strip()
        if not arguments.startswith("bool ") or "," in arguments:
            continue
        getter = name[3:4].lower() + name[4:]
        is_getter = f"is{name[3:]}"
        if (
            (declaration.get("parent"), getter) not in names
            and (declaration.get("parent"), is_getter) not in names
        ):
            continue
        result[declaration["parent"]].append((name, snake_case(name)))
    return inherited_properties(declarations, result)


def generated_command_buffer_encoders(declarations: list[dict[str, Any]]) -> set[str]:
    result = set()
    for declaration in declarations:
        if declaration["kind"] != "method" or declaration["name"] != "encodeToCommandBuffer":
            continue
        signature = declaration["signature"].replace(" ", "")
        if signature.startswith("voidencodeToCommandBuffer(MTL::CommandBuffer*"):
            result.add(declaration["parent"])
    return result


def generated_metal4_command_buffer_encoders(declarations: list[dict[str, Any]]) -> set[str]:
    result = set()
    for declaration in declarations:
        if declaration["kind"] != "method" or declaration["name"] != "encodeToCommandBuffer":
            continue
        signature = declaration["signature"].replace(" ", "")
        if signature.startswith("voidencodeToCommandBuffer(MTL4::CommandBuffer*"):
            result.add(declaration["parent"])
    return result


def generated_metalfx_compiler_factories(
    declarations: list[dict[str, Any]],
) -> dict[str, list[tuple[str, str, str]]]:
    result: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for declaration in declarations:
        if declaration["kind"] != "method":
            continue
        signature = declaration["signature"].replace(" ", "")
        if "(constMTL::Device*" not in signature or "constMTL4::Compiler*" not in signature:
            continue
        return_type = declaration["signature"].split(declaration["name"], 1)[0].strip()
        target = return_type.removesuffix("*").strip()
        if not target.startswith("MTL4FX::"):
            continue
        result[declaration["parent"]].append(
            (declaration["name"], snake_case(declaration["name"]), target)
        )
    return result


def generated_static_device_queries(
    declarations: list[dict[str, Any]],
) -> dict[str, list[tuple[str, str, str, str]]]:
    result: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for declaration in declarations:
        if declaration["kind"] != "method":
            continue
        signature = declaration["signature"]
        if not signature.startswith(("static bool ", "static float ")):
            continue
        arguments = signature.split("(", 1)[1].rsplit(")", 1)[0]
        if "MTL::Device*" not in arguments or "," in arguments:
            continue
        return_type = "bool" if signature.startswith("static bool ") else "f32"
        selector = CUSTOM_STATIC_DEVICE_SELECTORS.get(
            (declaration["parent"], declaration["name"]), declaration["name"]
        )
        result[declaration["parent"]].append(
            (declaration["name"], snake_case(declaration["name"]), return_type, selector)
        )
    return result


def default_constructible_classes(declarations: list[dict[str, Any]]) -> set[str]:
    methods: dict[str, set[str]] = defaultdict(set)
    for declaration in declarations:
        if declaration["kind"] != "method":
            continue
        signature = declaration["signature"]
        arguments = signature.split("(", 1)[1].rsplit(")", 1)[0].strip()
        if not arguments:
            methods[declaration["parent"]].add(declaration["name"])
    return {
        parent
        for parent, names in methods.items()
        if {"alloc", "init"}.issubset(names)
        and parent.startswith(("MTL::", "MTL4::", "MTLFX::", "MTL4FX::"))
    }


def runtime_class_name(qualified_name: str) -> str:
    namespace, name = qualified_name.split("::", 1)
    return f"{namespace}{name}"


def generated_method_paths(declarations: list[dict[str, Any]]) -> dict[str, str]:
    constructors = default_constructible_classes(declarations)
    primitive_properties = generated_property_methods(declarations)
    enum_properties = generated_enum_properties(declarations)
    object_properties = generated_object_properties(declarations)
    bool_setters = generated_bool_setters(declarations)
    command_buffer_encoders = generated_command_buffer_encoders(declarations)
    metal4_command_buffer_encoders = generated_metal4_command_buffer_encoders(declarations)
    static_device_queries = generated_static_device_queries(declarations)
    metalfx_compiler_factories = generated_metalfx_compiler_factories(declarations)
    paths: dict[tuple[str, str], str] = {}
    for parent, methods in primitive_properties.items():
        for selector, rust_name, rust_type, writable in methods:
            prefix = f"metal::generated_object_types::{object_path(parent)}"
            paths[(parent, selector)] = f"{prefix}::try_{rust_name}"
            if writable and rust_type != "bool":
                setter = property_setter(parent, selector)
                paths[(parent, setter)] = f"{prefix}::try_{snake_case(setter)}"
    for parent, methods in enum_properties.items():
        for selector, rust_name, _type_name, _raw_type, writable in methods:
            prefix = f"metal::generated_object_types::{object_path(parent)}"
            paths[(parent, selector)] = f"{prefix}::try_{rust_name}"
            if writable:
                setter = property_setter(parent, selector)
                paths[(parent, setter)] = f"{prefix}::try_{snake_case(setter)}"
    for parent, methods in object_properties.items():
        for selector, rust_name, _qualified_type, writable in methods:
            prefix = f"metal::generated_object_types::{object_path(parent)}"
            paths[(parent, selector)] = f"{prefix}::try_{rust_name}"
            if writable:
                setter = property_setter(parent, selector)
                paths[(parent, setter)] = f"{prefix}::try_{snake_case(setter)}"
    for parent, methods in bool_setters.items():
        for selector, rust_name in methods:
            paths[(parent, selector)] = (
                f"metal::generated_object_types::{object_path(parent)}::try_{rust_name}"
            )
    for parent in command_buffer_encoders:
        paths[(parent, "encodeToCommandBuffer")] = (
            f"metal::generated_object_types::{object_path(parent)}::encode_to_command_buffer"
        )
    for parent in metal4_command_buffer_encoders:
        paths[(parent, "encodeToCommandBuffer")] = (
            f"metal::generated_object_types::{object_path(parent)}::encode_to_metal4_command_buffer"
        )
    for parent, factories in metalfx_compiler_factories.items():
        prefix = f"metal::generated_object_types::{object_path(parent)}"
        for selector_name, rust_name, _target in factories:
            paths[(parent, selector_name)] = f"{prefix}::{rust_name}"
    for parent, queries in static_device_queries.items():
        for selector_name, rust_name, _return_type, _objc_selector in queries:
            paths[(parent, selector_name)] = (
                f"metal::generated_object_types::{object_path(parent)}::{rust_name}"
            )
    for parent, properties in MATRIX_PROPERTIES.items():
        prefix = f"metal::generated_object_types::{object_path(parent)}"
        for selector, rust_name, setter, _helper_get, _helper_set in properties:
            paths[(parent, selector)] = f"{prefix}::{rust_name}"
            paths[(parent, setter)] = f"{prefix}::set_{rust_name}"

    result: dict[str, str] = {}
    for declaration in declarations:
        if declaration["kind"] != "method":
            continue
        parent = declaration.get("parent", "")
        if parent in constructors and declaration["name"] in {"alloc", "init"}:
            arguments = declaration["signature"].split("(", 1)[1].rsplit(")", 1)[0].strip()
            if not arguments:
                result[declaration["id"]] = (
                    f"metal::generated_object_types::{object_path(parent)}::new"
                )
                continue
        path = paths.get((parent, declaration["name"]))
        if path is not None:
            result[declaration["id"]] = path
    return result


def load_inventory(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    declarations = value.get("declarations")
    if not isinstance(declarations, list):
        raise ValueError("inventory.declarations must be a list")
    return declarations


def object_path(qualified_name: str) -> str:
    namespace, name = qualified_name.split("::", 1)
    return f"{NAMESPACES[namespace]}::{name}"


def render(declarations: list[dict[str, Any]]) -> str:
    classes: dict[str, list[str]] = defaultdict(list)
    for declaration in declarations:
        if declaration["kind"] != "class" or "::" not in declaration["qualified_name"]:
            continue
        namespace, name = declaration["qualified_name"].split("::", 1)
        classes[NAMESPACES[namespace]].append(name)

    properties = generated_property_methods(declarations)
    enum_properties = generated_enum_properties(declarations)
    object_properties = generated_object_properties(declarations)
    bool_setters = generated_bool_setters(declarations)
    command_buffer_encoders = generated_command_buffer_encoders(declarations)
    metal4_command_buffer_encoders = generated_metal4_command_buffer_encoders(declarations)
    static_device_queries = generated_static_device_queries(declarations)
    metalfx_compiler_factories = generated_metalfx_compiler_factories(declarations)
    constructors = default_constructible_classes(declarations)
    object_bases = {
        declaration["qualified_name"]: base_class(declaration)
        for declaration in declarations
        if declaration["kind"] == "class"
    }
    lines = [
        "//! Generated opaque owned wrappers for framework object classes.",
        "//!",
        "//! Methods are covered separately only after their safe contracts are implemented.",
        "",
        "use crate::foundation::Error as FrameworkError;",
        "use crate::ThreadBound;",
        "use objc2::rc::Retained;",
        "use objc2::runtime::{AnyClass, AnyObject};",
        "use objc2::{msg_send, sel};",
        "use objc2_foundation::NSString;",
        "",
        "macro_rules! owned_object {",
        "    ($name:ident, $qualified:literal) => {",
        "        #[doc = concat!(\"Owned opaque wrapper for `\", $qualified, \"`.\")]",
        "        #[derive(Clone)]",
        "        pub struct $name {",
        "            _inner: Retained<AnyObject>,",
        "            _thread_bound: ThreadBound,",
        "        }",
        "",
        "        #[allow(dead_code)]",
        "        impl $name {",
        "            pub(crate) const fn from_inner(inner: Retained<AnyObject>) -> Self {",
        "                Self { _inner: inner, _thread_bound: ThreadBound::new() }",
        "            }",
        "",
        "            pub(crate) fn as_inner(&self) -> &AnyObject {",
        "                &self._inner",
        "            }",
        "",
        "            fn responds_to(&self, selector: objc2::runtime::Sel) -> bool {",
        "                // SAFETY: Every Objective-C object implements respondsToSelector:,",
        "                // and Sel/bool use the runtime's declared ABI encodings.",
        "                unsafe { msg_send![&*self._inner, respondsToSelector: selector] }",
        "            }",
        "        }",
        "    };",
        "}",
        "",
    ]
    reverse = {value: key for key, value in NAMESPACES.items()}
    for module in sorted(classes):
        lines += [f"/// Owned object types from the `{reverse[module]}` namespace.", f"pub mod {module} {{", "    use super::*;", ""]
        for name in sorted(set(classes[module])):
            lines.append(f'    owned_object!({name}, "{reverse[module]}::{name}");')
            qualified_name = f"{reverse[module]}::{name}"
            methods = sorted(set(properties.get(qualified_name, [])))
            enum_methods = sorted(set(enum_properties.get(qualified_name, [])))
            object_methods = sorted(set(object_properties.get(qualified_name, [])))
            setters = sorted(set(bool_setters.get(qualified_name, [])))
            constructible = qualified_name in constructors
            encodes_command_buffer = qualified_name in command_buffer_encoders
            encodes_metal4_command_buffer = qualified_name in metal4_command_buffer_encoders
            device_queries = sorted(set(static_device_queries.get(qualified_name, [])))
            compiler_factories = sorted(set(metalfx_compiler_factories.get(qualified_name, [])))
            matrix_properties = MATRIX_PROPERTIES.get(qualified_name, [])
            base = object_bases.get(qualified_name)
            base_known = base in object_bases
            if methods or enum_methods or object_methods or setters or constructible or encodes_command_buffer or encodes_metal4_command_buffer or device_queries or compiler_factories or matrix_properties or base_known:
                lines += [f"    impl {name} {{"]
                if base_known:
                    base_namespace, base_name = base.split("::", 1)
                    base_path = (
                        base_name
                        if base_namespace == reverse[module]
                        else f"super::{NAMESPACES[base_namespace]}::{base_name}"
                    )
                    base_method = snake_case(base_name).removeprefix("r#")
                    lines += [
                        f"        /// Returns the inherited `{base}` view with retained ownership.",
                        f"        pub fn as_{base_method}(&self) -> {base_path} {{",
                        f"            {base_path}::from_inner(self._inner.clone())",
                        "        }",
                    ]
                if constructible:
                    runtime_name = runtime_class_name(qualified_name)
                    lines += [
                        f"        /// Creates a default `{qualified_name}` when `{runtime_name}` is available.",
                        "        pub fn new() -> Result<Self, FrameworkError> {",
                        f"            let class = AnyClass::get(c\"{runtime_name}\").ok_or_else(||",
                        f"                FrameworkError::unsupported(\"{runtime_name} is unavailable on this system\")",
                        "            )?;",
                        "            // SAFETY: `new` follows Objective-C retained-return conventions;",
                        "            // the inventory declares both alloc and zero-argument init.",
                        "            let inner = unsafe { msg_send![class, new] };",
                        "            Ok(Self::from_inner(inner))",
                        "        }",
                    ]
                for selector, rust_name, rust_type, writable in methods:
                    lines += [
                        f"        /// Reads `{qualified_name}::{selector}` when the runtime selector is available.",
                        f"        pub fn {rust_name}(&self) -> Result<{rust_type}, FrameworkError> {{",
                        f"            if !self.responds_to(sel!({selector})) {{",
                        f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{selector} is unavailable\"));",
                        "            }",
                        "            // SAFETY: The selector is present and the inventory declares this",
                        "            // property getter with the exact primitive return type below.",
                        f"            Ok(unsafe {{ msg_send![&*self._inner, {selector}] }})",
                        "        }",
                    ]
                    if writable and rust_type != "bool":
                        setter = property_setter(qualified_name, selector)
                        lines += [
                            "",
                            f"        /// Writes `{qualified_name}::{setter}` after validation.",
                            f"        pub fn set_{rust_name}(&self, value: {rust_type}) -> Result<(), FrameworkError> {{",
                        ]
                        if rust_type in {"f32", "f64"}:
                            lines += [
                                "            if !value.is_finite() {",
                                f"                return Err(FrameworkError::invalid_argument(\"{qualified_name}::{setter} requires a finite value\"));",
                                "            }",
                            ]
                        lines += [
                            f"            if !self.responds_to(sel!({setter}:)) {{",
                            f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{setter} is unavailable\"));",
                            "            }",
                            "            // SAFETY: The selector is present and the input has the exact",
                            "            // primitive representation declared by the inventory.",
                            f"            unsafe {{ let _: () = msg_send![&*self._inner, {setter}: value]; }}",
                            "            Ok(())",
                            "        }",
                        ]
                for selector, rust_name, type_name, raw_type, writable in enum_methods:
                    manual_qualified = next(
                        (
                            candidate
                            for candidate in MANUAL_TYPES
                            if candidate.endswith(f"::{type_name}")
                        ),
                        None,
                    )
                    value_path = (
                        f"crate::{type_name}"
                        if manual_qualified is not None
                        else f"super::super::generated_value_types::{type_name}"
                    )
                    lines += [
                        f"        /// Reads `{qualified_name}::{selector}` when the runtime selector is available.",
                        f"        pub fn {rust_name}(&self) -> Result<{value_path}, FrameworkError> {{",
                        f"            if !self.responds_to(sel!({selector})) {{",
                        f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{selector} is unavailable\"));",
                        "            }",
                        "            // SAFETY: The selector is present and the inventory declares this",
                        f"            // property getter with the `{raw_type}` enum representation.",
                        f"            let raw: {raw_type} = unsafe {{ msg_send![&*self._inner, {selector}] }};",
                    ]
                    if manual_qualified in MANUAL_TYPES - set(EXTENSIBLE_MANUAL_TYPES):
                        lines += [
                            f"            {value_path}::try_from_system_raw(raw).ok_or_else(||",
                            f"                FrameworkError::unsupported(\"{qualified_name}::{selector} returned an unknown value\")",
                            "            )",
                            "        }",
                        ]
                    else:
                        lines += [
                            f"            Ok({value_path}::from_system_raw(raw))",
                            "        }",
                        ]
                    if writable:
                        setter = property_setter(qualified_name, selector)
                        lines += [
                            "",
                            f"        /// Writes `{qualified_name}::{setter}` after value and selector checks.",
                            f"        pub fn {snake_case(setter)}(&self, value: {value_path}) -> Result<(), FrameworkError> {{",
                            "            if !value.is_valid() {",
                            f"                return Err(FrameworkError::invalid_argument(\"{qualified_name}::{setter} received an undeclared value\"));",
                            "            }",
                            f"            if !self.responds_to(sel!({setter}:)) {{",
                            f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{setter} is unavailable\"));",
                            "            }",
                            f"            let raw: {raw_type} = value.as_raw();",
                            "            // SAFETY: The selector is present and the generated value has",
                            "            // been checked against its declared values or option bits.",
                            f"            unsafe {{ let _: () = msg_send![&*self._inner, {setter}: raw]; }}",
                            "            Ok(())",
                            "        }",
                        ]
                for selector, rust_name, target, writable in object_methods:
                    setter = property_setter(qualified_name, selector)
                    if target == "NS::String":
                        lines += [
                            f"        /// Reads `{qualified_name}::{selector}` as an owned string.",
                            f"        pub fn {rust_name}(&self) -> Result<Option<std::string::String>, FrameworkError> {{",
                            f"            if !self.responds_to(sel!({selector})) {{",
                            f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{selector} is unavailable\"));",
                            "            }",
                            "            // SAFETY: The selector is present and is declared to return NSString.",
                            f"            let value: Option<Retained<NSString>> = unsafe {{ msg_send![&*self._inner, {selector}] }};",
                            "            Ok(value.map(|value| value.to_string()))",
                            "        }",
                        ]
                        if writable:
                            lines += [
                                "",
                                f"        /// Writes `{qualified_name}::{setter}` from a borrowed Rust string.",
                                f"        pub fn set_{rust_name}(&self, value: &str) -> Result<(), FrameworkError> {{",
                                f"            if !self.responds_to(sel!({setter}:)) {{",
                                f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{setter} is unavailable\"));",
                                "            }",
                                "            let value = NSString::from_str(value);",
                                "            // SAFETY: The selector is present and receives a live NSString.",
                                f"            unsafe {{ let _: () = msg_send![&*self._inner, {setter}: &*value]; }}",
                                "            Ok(())",
                                "        }",
                            ]
                    else:
                        target_path = object_path(target)
                        target_type = CANONICAL_OBJECT_PATHS.get(
                            target,
                            f"super::super::generated_object_types::{target_path}",
                        )
                        lines += [
                            f"        /// Reads `{qualified_name}::{selector}` as an owned object.",
                            f"        pub fn {rust_name}(&self) -> Result<Option<{target_type}>, FrameworkError> {{",
                            f"            if !self.responds_to(sel!({selector})) {{",
                            f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{selector} is unavailable\"));",
                            "            }",
                            "            // SAFETY: The selector is present and its retained object result",
                            "            // is kept inside the generated owned wrapper.",
                            f"            let value: Option<Retained<AnyObject>> = unsafe {{ msg_send![&*self._inner, {selector}] }};",
                            (
                                f"            value.map({target_type}::from_any_object).transpose()"
                                if target in CANONICAL_OBJECT_PATHS
                                else f"            Ok(value.map(super::super::generated_object_types::{target_path}::from_inner))"
                            ),
                            "        }",
                        ]
                        if writable:
                            lines += [
                                "",
                                f"        /// Writes `{qualified_name}::{setter}` from a type-checked wrapper.",
                                f"        pub fn set_{rust_name}(&self, value: Option<&{target_type}>) -> Result<(), FrameworkError> {{",
                                f"            if !self.responds_to(sel!({setter}:)) {{",
                                f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{setter} is unavailable\"));",
                                "            }",
                                "            // SAFETY: The selector is present and the wrapper preserves the",
                                "            // Objective-C class identity declared for this property.",
                                (
                                    f"            unsafe {{ let _: () = msg_send![&*self._inner, {setter}: value.map({target_type}::as_any_object)]; }}"
                                    if target in CANONICAL_OBJECT_PATHS
                                    else f"            unsafe {{ let _: () = msg_send![&*self._inner, {setter}: value.map({target_type}::as_inner)]; }}"
                                ),
                                "            Ok(())",
                                "        }",
                            ]
                for selector, rust_name in setters:
                    lines += [
                        f"        /// Writes `{qualified_name}::{selector}` when the runtime selector is available.",
                        "        pub fn " + rust_name + "(&self, value: bool) -> Result<(), FrameworkError> {",
                        f"            if !self.responds_to(sel!({selector}:)) {{",
                        f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{selector} is unavailable\"));",
                        "            }",
                        "            // SAFETY: The selector is present and bool covers the property's",
                        "            // complete valid input domain declared by the inventory.",
                        f"            unsafe {{ let _: () = msg_send![&*self._inner, {selector}: value]; }}",
                        "            Ok(())",
                        "        }",
                    ]
                if encodes_command_buffer:
                    lines += [
                        "        /// Encodes work into a mutably borrowed command buffer after an availability check.",
                        "        pub fn encode_to_command_buffer(&self, command_buffer: &mut crate::CommandBuffer) -> Result<(), FrameworkError> {",
                        "            if !self.responds_to(sel!(encodeToCommandBuffer:)) {",
                        f"                return Err(FrameworkError::unsupported(\"{qualified_name}::encodeToCommandBuffer is unavailable\"));",
                        "            }",
                        "            // SAFETY: the selector is present, the argument conforms to",
                        "            // MTLCommandBuffer, and its mutable borrow prevents concurrent encoding.",
                        "            unsafe { let _: () = msg_send![&*self._inner, encodeToCommandBuffer: &*command_buffer.inner]; }",
                        "            Ok(())",
                        "        }",
                    ]
                if encodes_metal4_command_buffer:
                    lines += [
                        "        /// Mechanically encodes work into an active Metal 4 recording scope.",
                        "        pub(crate) fn encode_to_metal4_command_buffer(&self, command_buffer: &mut crate::RecordingCommandBuffer) -> Result<(), FrameworkError> {",
                        "            if !self.responds_to(sel!(encodeToCommandBuffer:)) {",
                        f"                return Err(FrameworkError::unsupported(\"{qualified_name}::encodeToCommandBuffer is unavailable\"));",
                        "            }",
                        "            // SAFETY: selector availability is checked and RecordingCommandBuffer",
                        "            // proves that the retained MTL4CommandBuffer is inside begin/end recording.",
                        "            unsafe { let _: () = msg_send![&*self._inner, encodeToCommandBuffer: command_buffer.inner.as_inner()]; }",
                        "            Ok(())",
                        "        }",
                    ]
                for selector_name, rust_name, target in compiler_factories:
                    target_path = object_path(target)
                    objc_selector = f"{selector_name}WithDevice"
                    lines += [
                        f"        /// Creates `{target}` using a Metal device and Metal 4 compiler.",
                        f"        pub fn {rust_name}(&self, device: &crate::Device, compiler: &super::super::generated_object_types::metal4::Compiler) -> Result<super::super::generated_object_types::{target_path}, FrameworkError> {{",
                        f"            if !self.responds_to(sel!({objc_selector}:compiler:)) {{",
                        f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{objc_selector}:compiler: is unavailable\"));",
                        "            }",
                        "            // SAFETY: selector availability and both Objective-C object identities are checked.",
                        f"            let value: Option<Retained<AnyObject>> = unsafe {{ msg_send![&*self._inner, {objc_selector}: &*device.inner, compiler: compiler.as_inner()] }};",
                        f"            value.map(super::super::generated_object_types::{target_path}::from_inner).ok_or_else(|| FrameworkError::unsupported(\"MetalFX could not create {target}\"))",
                        "        }",
                    ]
                for _selector_name, rust_name, return_type, objc_selector in device_queries:
                    lines += [
                        f"        /// Runs `{qualified_name}::{objc_selector}` after class and selector availability checks.",
                        f"        pub fn {rust_name}(device: &crate::Device) -> Result<{return_type}, FrameworkError> {{",
                        f"            let class = AnyClass::get(c\"{runtime_class_name(qualified_name)}\").ok_or_else(|| FrameworkError::unsupported(\"{runtime_class_name(qualified_name)} is unavailable\"))?;",
                        f"            let selector = sel!({objc_selector}:);",
                        "            // SAFETY: every Objective-C class object implements respondsToSelector:.",
                        "            let available: bool = unsafe { msg_send![class, respondsToSelector: selector] };",
                        "            if !available {",
                        f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{objc_selector} is unavailable\"));",
                        "            }",
                        "            // SAFETY: class and selector availability were checked and the",
                        "            // inventory declares the exact primitive return and MTLDevice argument ABI.",
                        f"            let value: {return_type} = unsafe {{ msg_send![class, {objc_selector}: &*device.inner] }};",
                    ]
                    if return_type == "f32":
                        lines += [
                            "            if !value.is_finite() {",
                            "                return Err(FrameworkError::unsupported(\"MetalFX returned a non-finite scale\"));",
                            "            }",
                        ]
                    lines += ["            Ok(value)", "        }"]
                for selector, rust_name, setter, helper_get, helper_set in matrix_properties:
                    lines += [
                        f"        /// Reads `{qualified_name}::{selector}` through the aligned SIMD ABI bridge.",
                        f"        pub fn {rust_name}(&self) -> Result<crate::Matrix4x4, FrameworkError> {{",
                        f"            if !self.responds_to(sel!({selector})) {{",
                        f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{selector} is unavailable\"));",
                        "            }",
                        f"            let value = crate::metal_fx::matrix::{helper_get}(&self._inner);",
                        "            if !value.is_finite() {",
                        "                return Err(FrameworkError::unsupported(\"MetalFX returned a non-finite matrix\"));",
                        "            }",
                        "            Ok(value)",
                        "        }",
                        f"        /// Writes `{qualified_name}::{setter}` through the aligned SIMD ABI bridge.",
                        f"        pub fn set_{rust_name}(&self, value: crate::Matrix4x4) -> Result<(), FrameworkError> {{",
                        "            if !value.is_finite() {",
                        "                return Err(FrameworkError::invalid_argument(\"matrix components must be finite\"));",
                        "            }",
                        f"            if !self.responds_to(sel!({setter}:)) {{",
                        f"                return Err(FrameworkError::unsupported(\"{qualified_name}::{setter} is unavailable\"));",
                        "            }",
                        f"            crate::metal_fx::matrix::{helper_set}(&self._inner, value);",
                        "            Ok(())",
                        "        }",
                    ]
                lines += ["    }"]
        lines += ["}", ""]

    source = "\n".join(lines)
    formatted = subprocess.run(
        ["rustfmt", "--edition", "2024", "--emit", "stdout"],
        input=source,
        check=False,
        capture_output=True,
        text=True,
    )
    if formatted.returncode != 0:
        raise RuntimeError(f"rustfmt failed for generated object types: {formatted.stderr}")
    return formatted.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=Path("api/metal-cpp-inventory.json"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("crates/metal-rust-ffi/src/Metal/MTLGeneratedObjectTypes.rs"),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    declarations = load_inventory(args.inventory)
    output = render(declarations)
    count = sum(
        declaration["kind"] == "class" and "::" in declaration["qualified_name"]
        for declaration in declarations
    )
    property_count = sum(len(methods) for methods in generated_property_methods(declarations).values())
    enum_property_count = sum(
        len(methods) for methods in generated_enum_properties(declarations).values()
    )
    object_property_count = sum(
        len(methods) for methods in generated_object_properties(declarations).values()
    )
    setter_count = sum(len(methods) for methods in generated_bool_setters(declarations).values())
    constructor_count = len(default_constructible_classes(declarations))
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != output:
            print(f"generated object types are stale: {args.output}", file=sys.stderr)
            return 1
        print(
            f"generated object types are current: {count} classes, "
            f"{constructor_count} constructors, {property_count} properties, "
            f"{enum_property_count} enum properties, {object_property_count} object properties, "
            f"{setter_count} boolean setters"
        )
        return 0
    args.output.write_text(output, encoding="utf-8")
    print(
        f"generated {count} owned object types, {constructor_count} constructors, "
        f"{property_count} primitive properties, {enum_property_count} enum properties, "
        f"{object_property_count} object properties, and {setter_count} boolean setters"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
