# Metal-Rust

**Safe Rust interfaces for Apple Metal and Metal 4.**

`metal-rust` is the low-overhead Rust foundation for applications that need
direct access to Apple's GPU APIs without exposing Objective-C pointers,
selectors, retain/release calls, or unchecked ranges to application code.
The API follows Apple's metal-cpp surface while keeping ownership and
message-send invariants inside the audited implementation layer.

This project works together with
[`egui-mtl4`](https://github.com/maple-quartz18/egui-mtl4), an experimental
egui painter built on the Metal 4 APIs exposed here:

```text
egui application
      |
egui-mtl4::Painter
      |
metal-rust
      |
Metal 4 / CAMetalLayer
```

Use `metal-rust` directly for a renderer, or add `egui-mtl4` when the
application needs egui UI rendering on the same Metal 4 device and queue.

## Safety Boundary

- The public `metal-rust` crate uses `#![forbid(unsafe_code)]`.
- Raw Objective-C interop is confined to the separately audited
  `metal-rust-ffi` crate.
- Public APIs expose owned Rust values and typed RAII objects, not Objective-C
  pointers, selectors, `NSError **`, retain/release operations, or unchecked
  ranges.
- APIs whose synchronization contracts are not represented safely remain
  unavailable.

The facade covers core Metal resources and submission, Metal 4 command
objects, counter heaps, capture, MetalFX descriptors, and CAMetalLayer
drawable ownership. API coverage is tracked in
[`api/coverage.json`](api/coverage.json) against the metal-cpp inventory.

## Using With egui

For a Metal 4 application with an egui overlay:

```toml
[dependencies]
egui = "0.36"
metal-rust = { git = "https://github.com/maple-quartz18/Metal-Rust" }
egui-mtl4 = { git = "https://github.com/maple-quartz18/egui-mtl4" }
```

Create one `metal_rust::Device`, one Metal 4 command queue, and one
`egui_mtl4::Painter` from that device. Register scene textures with the
painter when egui displays them, then pass the layer's residency set to
`Painter::render`.

The projects are intentionally separate:

- `metal-rust` provides the low-level safe Metal and Metal 4 API.
- `egui-mtl4` provides egui mesh translation, texture uploads, clipping,
  frame slots, and Metal 4 UI drawing.

The application remains responsible for the window, `CAMetalLayer`, drawable
lifetime, presentation, and residency of external textures.

## Development

The fork currently tracks the audited Metal 4 API additions used by
`egui-mtl4`. Use the tested fork revision in production applications until
the corresponding APIs are available from your chosen upstream.

```sh
cargo fmt --all -- --check
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
```

## License

The project and `metal-rust-ffi` are licensed under Apache-2.0. The low-level
binding is independent of the GPL-3.0-only `egui-mtl4` painter.
