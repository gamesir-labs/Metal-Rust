# API coverage

This file is generated from `api/metal-cpp-inventory.json` and
`api/coverage.json`. The ledger has one explicit entry for every public
declaration in the local Apple metal-cpp snapshot.

Reference digest: `925aa6c677b28fb9fe1a54a217bea1efd3f145c57e0e49e5b82d9d47810ff43d`.

Statuses:

- `implemented`: a pinned/generated or handwritten audited FFI mapping exists; the public facade may group several C++ overloads into one checked Rust operation.
- `availability`: an implemented API is represented, but object creation is gated by the Apple framework/runtime capability query.
- `substitute`: C++ ownership, helper, scalar, or pointer shape is
  grouped into a safe Rust value or RAII abstraction.
- `unimplemented`: no audited safe facade mapping exists yet.

Generated Metal bindings are implementation sources behind
`metal-rust-ffi`; they are not re-exported as raw Objective-C APIs.
The `rust` target in the ledger preserves selector-level traceability,
while the evidence and notes identify the safe facade grouping or
substitution that callers actually use.

Total declarations: **5226**.
Implemented: **2073**; availability-gated: **2401**; substituted: **752**; unimplemented: **0**.

| Framework | Implemented | Availability | Substitute | Unimplemented | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Foundation | 116 | 3 | 183 | 0 | 302 |
| Metal | 1919 | 2007 | 569 | 0 | 4495 |
| MetalFX | 16 | 391 | 0 | 0 | 407 |
| QuartzCore | 22 | 0 | 0 | 0 | 22 |

## Header summary

Each reference header is retained in the ledger so a new or removed
header cannot disappear behind a framework-level percentage.

| Framework | Header | Implemented | Availability | Substitute | Unimplemented | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Foundation | `Foundation/NSArray.hpp` | 0 | 0 | 9 | 0 | 9 |
| Foundation | `Foundation/NSAutoreleasePool.hpp` | 0 | 0 | 6 | 0 | 6 |
| Foundation | `Foundation/NSBundle.hpp` | 6 | 0 | 2 | 0 | 8 |
| Foundation | `Foundation/NSData.hpp` | 0 | 0 | 3 | 0 | 3 |
| Foundation | `Foundation/NSDate.hpp` | 0 | 0 | 3 | 0 | 3 |
| Foundation | `Foundation/NSDictionary.hpp` | 0 | 0 | 8 | 0 | 8 |
| Foundation | `Foundation/NSEnumerator.hpp` | 0 | 0 | 9 | 0 | 9 |
| Foundation | `Foundation/NSError.hpp` | 16 | 0 | 7 | 0 | 23 |
| Foundation | `Foundation/NSLock.hpp` | 0 | 0 | 10 | 0 | 10 |
| Foundation | `Foundation/NSNotification.hpp` | 5 | 0 | 6 | 0 | 11 |
| Foundation | `Foundation/NSNumber.hpp` | 0 | 0 | 54 | 0 | 54 |
| Foundation | `Foundation/NSObjCRuntime.hpp` | 5 | 0 | 0 | 0 | 5 |
| Foundation | `Foundation/NSObject.hpp` | 0 | 0 | 11 | 0 | 11 |
| Foundation | `Foundation/NSProcessInfo.hpp` | 38 | 3 | 3 | 0 | 44 |
| Foundation | `Foundation/NSRange.hpp` | 3 | 0 | 5 | 0 | 8 |
| Foundation | `Foundation/NSSet.hpp` | 0 | 0 | 6 | 0 | 6 |
| Foundation | `Foundation/NSSharedPtr.hpp` | 0 | 0 | 13 | 0 | 13 |
| Foundation | `Foundation/NSString.hpp` | 34 | 0 | 23 | 0 | 57 |
| Foundation | `Foundation/NSTypes.hpp` | 7 | 0 | 3 | 0 | 10 |
| Foundation | `Foundation/NSURL.hpp` | 2 | 0 | 2 | 0 | 4 |
| Metal | `Metal/MTL4AccelerationStructure.hpp` | 11 | 165 | 23 | 0 | 199 |
| Metal | `Metal/MTL4Archive.hpp` | 1 | 7 | 0 | 0 | 8 |
| Metal | `Metal/MTL4ArgumentTable.hpp` | 2 | 16 | 5 | 0 | 23 |
| Metal | `Metal/MTL4BinaryFunction.hpp` | 1 | 2 | 0 | 0 | 3 |
| Metal | `Metal/MTL4BinaryFunctionDescriptor.hpp` | 4 | 8 | 1 | 0 | 13 |
| Metal | `Metal/MTL4CommandAllocator.hpp` | 2 | 8 | 0 | 0 | 10 |
| Metal | `Metal/MTL4CommandBuffer.hpp` | 1 | 15 | 6 | 0 | 22 |
| Metal | `Metal/MTL4CommandEncoder.hpp` | 4 | 10 | 4 | 0 | 18 |
| Metal | `Metal/MTL4CommandQueue.hpp` | 31 | 14 | 12 | 0 | 57 |
| Metal | `Metal/MTL4CommitFeedback.hpp` | 1 | 2 | 3 | 0 | 6 |
| Metal | `Metal/MTL4Compiler.hpp` | 3 | 20 | 30 | 0 | 53 |
| Metal | `Metal/MTL4CompilerTask.hpp` | 6 | 3 | 0 | 0 | 9 |
| Metal | `Metal/MTL4ComputeCommandEncoder.hpp` | 0 | 18 | 20 | 0 | 38 |
| Metal | `Metal/MTL4ComputePipeline.hpp` | 1 | 17 | 0 | 0 | 18 |
| Metal | `Metal/MTL4Counters.hpp` | 9 | 12 | 1 | 0 | 22 |
| Metal | `Metal/MTL4FunctionDescriptor.hpp` | 1 | 2 | 0 | 0 | 3 |
| Metal | `Metal/MTL4LibraryDescriptor.hpp` | 1 | 8 | 0 | 0 | 9 |
| Metal | `Metal/MTL4LibraryFunctionDescriptor.hpp` | 1 | 6 | 0 | 0 | 7 |
| Metal | `Metal/MTL4LinkingDescriptor.hpp` | 3 | 13 | 10 | 0 | 26 |
| Metal | `Metal/MTL4MachineLearningCommandEncoder.hpp` | 0 | 3 | 1 | 0 | 4 |
| Metal | `Metal/MTL4MachineLearningPipeline.hpp` | 3 | 14 | 3 | 0 | 20 |
| Metal | `Metal/MTL4MeshRenderPipeline.hpp` | 1 | 52 | 1 | 0 | 54 |
| Metal | `Metal/MTL4PipelineDataSetSerializer.hpp` | 5 | 4 | 3 | 0 | 12 |
| Metal | `Metal/MTL4PipelineState.hpp` | 19 | 12 | 1 | 0 | 32 |
| Metal | `Metal/MTL4RenderCommandEncoder.hpp` | 4 | 26 | 17 | 0 | 47 |
| Metal | `Metal/MTL4RenderPass.hpp` | 1 | 31 | 2 | 0 | 34 |
| Metal | `Metal/MTL4RenderPipeline.hpp` | 7 | 63 | 11 | 0 | 81 |
| Metal | `Metal/MTL4SpecializedFunctionDescriptor.hpp` | 1 | 8 | 0 | 0 | 9 |
| Metal | `Metal/MTL4StitchedFunctionDescriptor.hpp` | 1 | 4 | 2 | 0 | 7 |
| Metal | `Metal/MTL4TileRenderPipeline.hpp` | 1 | 18 | 0 | 0 | 19 |
| Metal | `Metal/MTLAccelerationStructure.hpp` | 100 | 232 | 15 | 0 | 347 |
| Metal | `Metal/MTLAccelerationStructureCommandEncoder.hpp` | 4 | 26 | 4 | 0 | 34 |
| Metal | `Metal/MTLAccelerationStructureTypes.hpp` | 16 | 0 | 19 | 0 | 35 |
| Metal | `Metal/MTLAllocation.hpp` | 1 | 1 | 0 | 0 | 2 |
| Metal | `Metal/MTLArgument.hpp` | 49 | 94 | 7 | 0 | 150 |
| Metal | `Metal/MTLArgumentEncoder.hpp` | 14 | 5 | 10 | 0 | 29 |
| Metal | `Metal/MTLBinaryArchive.hpp` | 8 | 12 | 3 | 0 | 23 |
| Metal | `Metal/MTLBlitCommandEncoder.hpp` | 25 | 2 | 7 | 0 | 34 |
| Metal | `Metal/MTLBlitPass.hpp` | 3 | 14 | 2 | 0 | 19 |
| Metal | `Metal/MTLBuffer.hpp` | 9 | 1 | 2 | 0 | 12 |
| Metal | `Metal/MTLCaptureManager.hpp` | 9 | 19 | 4 | 0 | 32 |
| Metal | `Metal/MTLCaptureScope.hpp` | 1 | 2 | 2 | 0 | 5 |
| Metal | `Metal/MTLCommandBuffer.hpp` | 71 | 10 | 9 | 0 | 90 |
| Metal | `Metal/MTLCommandEncoder.hpp` | 26 | 3 | 3 | 0 | 32 |
| Metal | `Metal/MTLCommandQueue.hpp` | 9 | 6 | 4 | 0 | 19 |
| Metal | `Metal/MTLComputeCommandEncoder.hpp` | 33 | 4 | 11 | 0 | 48 |
| Metal | `Metal/MTLComputePass.hpp` | 5 | 16 | 0 | 0 | 21 |
| Metal | `Metal/MTLComputePipeline.hpp` | 16 | 29 | 12 | 0 | 57 |
| Metal | `Metal/MTLCounters.hpp` | 26 | 34 | 4 | 0 | 64 |
| Metal | `Metal/MTLDataType.hpp` | 98 | 0 | 0 | 0 | 98 |
| Metal | `Metal/MTLDepthStencil.hpp` | 21 | 29 | 1 | 0 | 51 |
| Metal | `Metal/MTLDevice.hpp` | 156 | 89 | 58 | 0 | 303 |
| Metal | `Metal/MTLDrawable.hpp` | 1 | 5 | 4 | 0 | 10 |
| Metal | `Metal/MTLDynamicLibrary.hpp` | 8 | 4 | 1 | 0 | 13 |
| Metal | `Metal/MTLEvent.hpp` | 4 | 13 | 6 | 0 | 23 |
| Metal | `Metal/MTLFence.hpp` | 1 | 3 | 0 | 0 | 4 |
| Metal | `Metal/MTLFunctionConstantValues.hpp` | 2 | 2 | 3 | 0 | 7 |
| Metal | `Metal/MTLFunctionDescriptor.hpp` | 9 | 13 | 3 | 0 | 25 |
| Metal | `Metal/MTLFunctionHandle.hpp` | 1 | 4 | 0 | 0 | 5 |
| Metal | `Metal/MTLFunctionLog.hpp` | 5 | 7 | 1 | 0 | 13 |
| Metal | `Metal/MTLFunctionStitching.hpp` | 11 | 21 | 17 | 0 | 49 |
| Metal | `Metal/MTLGPUAddress.hpp` | 0 | 0 | 1 | 0 | 1 |
| Metal | `Metal/MTLHeap.hpp` | 16 | 29 | 0 | 0 | 45 |
| Metal | `Metal/MTLIOCommandBuffer.hpp` | 6 | 16 | 5 | 0 | 27 |
| Metal | `Metal/MTLIOCommandQueue.hpp` | 15 | 21 | 1 | 0 | 37 |
| Metal | `Metal/MTLIOCompressor.hpp` | 3 | 0 | 5 | 0 | 8 |
| Metal | `Metal/MTLIndirectCommandBuffer.hpp` | 15 | 41 | 4 | 0 | 60 |
| Metal | `Metal/MTLIndirectCommandEncoder.hpp` | 33 | 0 | 2 | 0 | 35 |
| Metal | `Metal/MTLIntersectionFunctionTable.hpp` | 18 | 11 | 6 | 0 | 35 |
| Metal | `Metal/MTLLibrary.hpp` | 108 | 25 | 24 | 0 | 157 |
| Metal | `Metal/MTLLinkedFunctions.hpp` | 1 | 3 | 8 | 0 | 12 |
| Metal | `Metal/MTLLogState.hpp` | 12 | 7 | 3 | 0 | 22 |
| Metal | `Metal/MTLParallelRenderCommandEncoder.hpp` | 1 | 7 | 0 | 0 | 8 |
| Metal | `Metal/MTLPipeline.hpp` | 10 | 6 | 2 | 0 | 18 |
| Metal | `Metal/MTLPixelFormat.hpp` | 141 | 0 | 0 | 0 | 141 |
| Metal | `Metal/MTLRasterizationRate.hpp` | 5 | 33 | 9 | 0 | 47 |
| Metal | `Metal/MTLRenderCommandEncoder.hpp` | 111 | 46 | 42 | 0 | 199 |
| Metal | `Metal/MTLRenderPass.hpp` | 60 | 76 | 1 | 0 | 137 |
| Metal | `Metal/MTLRenderPipeline.hpp` | 88 | 184 | 40 | 0 | 312 |
| Metal | `Metal/MTLResidencySet.hpp` | 2 | 17 | 3 | 0 | 22 |
| Metal | `Metal/MTLResource.hpp` | 40 | 13 | 1 | 0 | 54 |
| Metal | `Metal/MTLResourceStateCommandEncoder.hpp` | 13 | 4 | 2 | 0 | 19 |
| Metal | `Metal/MTLResourceStatePass.hpp` | 3 | 14 | 2 | 0 | 19 |
| Metal | `Metal/MTLResourceViewPool.hpp` | 2 | 10 | 1 | 0 | 13 |
| Metal | `Metal/MTLSampler.hpp` | 24 | 39 | 0 | 0 | 63 |
| Metal | `Metal/MTLStageInputOutputDescriptor.hpp` | 70 | 34 | 0 | 0 | 104 |
| Metal | `Metal/MTLTensor.hpp` | 42 | 36 | 20 | 0 | 98 |
| Metal | `Metal/MTLTexture.hpp` | 114 | 16 | 8 | 0 | 138 |
| Metal | `Metal/MTLTextureViewPool.hpp` | 1 | 1 | 2 | 0 | 4 |
| Metal | `Metal/MTLTypes.hpp` | 29 | 0 | 4 | 0 | 33 |
| Metal | `Metal/MTLVersion.hpp` | 0 | 0 | 4 | 0 | 4 |
| Metal | `Metal/MTLVertexDescriptor.hpp` | 66 | 30 | 0 | 0 | 96 |
| Metal | `Metal/MTLVisibleFunctionTable.hpp` | 2 | 7 | 1 | 0 | 10 |
| MetalFX | `MetalFX/MTL4FXFrameInterpolator.hpp` | 1 | 1 | 0 | 0 | 2 |
| MetalFX | `MetalFX/MTL4FXSpatialScaler.hpp` | 1 | 1 | 0 | 0 | 2 |
| MetalFX | `MetalFX/MTL4FXTemporalDenoisedScaler.hpp` | 1 | 1 | 0 | 0 | 2 |
| MetalFX | `MetalFX/MTL4FXTemporalScaler.hpp` | 1 | 1 | 0 | 0 | 2 |
| MetalFX | `MetalFX/MTLFXFrameInterpolator.hpp` | 3 | 106 | 0 | 0 | 109 |
| MetalFX | `MetalFX/MTLFXSpatialScaler.hpp` | 4 | 40 | 0 | 0 | 44 |
| MetalFX | `MetalFX/MTLFXTemporalDenoisedScaler.hpp` | 3 | 133 | 0 | 0 | 136 |
| MetalFX | `MetalFX/MTLFXTemporalScaler.hpp` | 2 | 108 | 0 | 0 | 110 |
| QuartzCore | `QuartzCore/CAMetalDrawable.hpp` | 2 | 0 | 0 | 0 | 2 |
| QuartzCore | `QuartzCore/CAMetalLayer.hpp` | 20 | 0 | 0 | 0 | 20 |

## Declaration-kind summary

The machine-readable inventory preserves the original qualified name
and signature for every class, method, enum, option, field, constant,
alias, function, and macro.

| Framework | Kind | Implemented | Availability | Substitute | Unimplemented | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Foundation | `alias` | 0 | 0 | 14 | 0 | 14 |
| Foundation | `class` | 5 | 0 | 19 | 0 | 24 |
| Foundation | `constant` | 25 | 3 | 0 | 0 | 28 |
| Foundation | `enum` | 3 | 0 | 0 | 0 | 3 |
| Foundation | `enum_member` | 47 | 0 | 0 | 0 | 47 |
| Foundation | `field` | 5 | 0 | 4 | 0 | 9 |
| Foundation | `macro` | 0 | 0 | 1 | 0 | 1 |
| Foundation | `method` | 27 | 0 | 144 | 0 | 171 |
| Foundation | `options` | 2 | 0 | 0 | 0 | 2 |
| Foundation | `struct` | 2 | 0 | 1 | 0 | 3 |
| Metal | `alias` | 2 | 0 | 66 | 0 | 68 |
| Metal | `class` | 226 | 1 | 5 | 0 | 232 |
| Metal | `constant` | 0 | 27 | 0 | 0 | 27 |
| Metal | `enum` | 104 | 0 | 0 | 0 | 104 |
| Metal | `enum_member` | 918 | 0 | 0 | 0 | 918 |
| Metal | `field` | 152 | 0 | 0 | 0 | 152 |
| Metal | `function` | 1 | 0 | 8 | 0 | 9 |
| Metal | `macro` | 0 | 0 | 4 | 0 | 4 |
| Metal | `method` | 450 | 1979 | 486 | 0 | 2915 |
| Metal | `options` | 24 | 0 | 0 | 0 | 24 |
| Metal | `struct` | 42 | 0 | 0 | 0 | 42 |
| MetalFX | `class` | 13 | 4 | 0 | 0 | 17 |
| MetalFX | `enum` | 0 | 1 | 0 | 0 | 1 |
| MetalFX | `enum_member` | 3 | 0 | 0 | 0 | 3 |
| MetalFX | `method` | 0 | 386 | 0 | 0 | 386 |
| QuartzCore | `class` | 2 | 0 | 0 | 0 | 2 |
| QuartzCore | `method` | 20 | 0 | 0 | 0 | 20 |

The machine-readable ledger is checked with:

```sh
python3 scripts/generate_api_inventory.py --check
python3 scripts/check-api-coverage.py
```

A changed reference digest requires regenerating the inventory and reviewing every new or removed ID.
