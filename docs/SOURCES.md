# Source and provenance

## Apple metal-cpp

The migration reference is the official Apple metal-cpp distribution pinned at
`third_party/metal-cpp`. The gitlink is locked to
`27c4382b7151d55a51692cdcb27aaa98752240de`, the
`release/metal-cpp_macOS27_iOS27` revision. It contains 136 headers across
Foundation, Metal, MetalFX, and QuartzCore.

`api/metal-cpp-inventory.json` records both that Git revision and a SHA-256
digest of every included header path and file content. The digest remains the
content-level guard even when a submodule is moved or repackaged.

The reference is Apache License 2.0, Copyright Apple Inc. 2024, as stated in
`metal-cpp/LICENSE.txt`. Metal-Rust follows Apache-2.0 and does not link to or
ship the metal-cpp C++ implementation; it calls the Apple frameworks through
the audited `metal-rust-ffi` crate.

## Rust Objective-C bindings

The FFI crate uses the version-pinned `objc2`, `objc2-foundation`, and
`objc2-metal` crates. Their raw declarations remain implementation details and
are never re-exported from the public facade. QuartzCore declarations are
similarly kept behind the FFI boundary. Missing framework bindings may be
added locally only when the same ownership, availability, panic, and
`SAFETY:` audit rules are applied.

MetalFX is weak-linked by the FFI build script. Descriptor construction first
checks the runtime class registry, so a system without MetalFX returns an
owned `Unsupported` error instead of loading a missing framework or sending a
selector to a nonexistent class.

## Updating the reference

After changing the reference snapshot, regenerate the inventory and review the
digest and every new/removed declaration:

```sh
git submodule update --init --checkout
python3 scripts/generate_api_inventory.py
git diff -- api/metal-cpp-inventory.json
python3 scripts/check-api-coverage.py
```

An inventory drift is a required review event, not a reason to mark a symbol
as covered without a safe Rust mapping.
