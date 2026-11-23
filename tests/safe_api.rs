#![forbid(unsafe_code)]

use metal_rust::{
    ClearColor, Device, ErrorKind, Layer, MAX_TIMESTAMP_COUNTERS, Origin, PixelFormat, Region,
    ResourceOptions, Size, SpatialScalerDescriptor, TemporalScalerDescriptor, TextureDescriptor,
    TextureUsage,
};
use static_assertions::assert_not_impl_any;

assert_not_impl_any!(metal_rust::Device: Send, Sync);
assert_not_impl_any!(metal_rust::CommandQueue: Send, Sync);
assert_not_impl_any!(metal_rust::Library: Send, Sync);
assert_not_impl_any!(metal_rust::RenderPipelineState: Send, Sync);
assert_not_impl_any!(metal_rust::ComputePipelineState: Send, Sync);
assert_not_impl_any!(metal_rust::Buffer: Send, Sync);
assert_not_impl_any!(metal_rust::Texture: Send, Sync);
assert_not_impl_any!(metal_rust::CommandBuffer: Send, Sync);

#[test]
fn checked_value_constructors_are_stable() {
    fn assert_owned_clone<T: Clone>() {}

    assert_owned_clone::<metal_rust::metal::Heap>();
    assert_owned_clone::<metal_rust::metal4::CommandQueue>();
    assert_owned_clone::<metal_rust::foundation::NotificationName>();
    let region = Region::new(Origin::new(1, 2, 0), Size::new(8, 4, 1));
    assert_eq!(region.size.width, 8);
    assert_ne!(
        TextureUsage::SHADER_READ.union(TextureUsage::RENDER_TARGET),
        TextureUsage::UNKNOWN
    );
    assert_eq!(
        TextureUsage::SHADER_READ.union(TextureUsage::UNKNOWN),
        TextureUsage::SHADER_READ
    );
    assert_eq!(ResourceOptions::SHARED, ResourceOptions::default());
    assert_eq!(ClearColor::new(0.1, 0.2, 0.3, 1.0).alpha, 1.0);
    assert_eq!(
        metal_rust::metal::CPUCacheMode::CPUCacheModeWriteCombined.as_raw(),
        1
    );
    let usage = metal_rust::metal::ResourceUsage::ResourceUsageRead
        | metal_rust::metal::ResourceUsage::ResourceUsageWrite;
    assert_ne!(usage.as_raw(), 0);
    let sizes = metal_rust::metal::AccelerationStructureSizes {
        acceleration_structure_size: 1024,
        build_scratch_buffer_size: 512,
        refit_scratch_buffer_size: 256,
    };
    assert_eq!(sizes.acceleration_structure_size, 1024);

    assert!(metal_rust::metal::CPUCacheMode::try_from(1usize).is_ok());
    assert!(metal_rust::metal::CPUCacheMode::try_from(99usize).is_err());
    assert!(metal_rust::metal::ResourceUsage::from_bits(3).is_some());
    assert!(metal_rust::metal::ResourceUsage::from_bits(usize::MAX).is_none());

    let _: metal_rust::foundation::TimeInterval = 0.5;
}

#[test]
fn foundation_native_substitutes_and_owned_objects_are_safe() {
    use metal_rust::foundation::{
        Array, Bundle, COCOA_ERROR_DOMAIN, Condition, Number, ProcessInfo, StringExt, URL,
    };

    let values: Array<u32> = vec![1, 2, 3];
    assert_eq!(values.len(), 3);
    let cloned_values = values.clone();
    assert_eq!(cloned_values.into_iter().sum::<u32>(), 6);
    drop(values);
    assert_eq!("Metal".character(1), Some('e'));
    assert_eq!(Number::from(42_u64).as_u64(), 42);
    assert_eq!(COCOA_ERROR_DOMAIN.as_str(), "NSCocoaErrorDomain");

    let condition = Condition::new();
    condition.signal();
    condition.wait();

    let path = std::env::temp_dir().join("metal-rust-foundation-url");
    let url = URL::from_file_path(&path).expect("UTF-8 temporary path");
    assert_eq!(url.file_path(), path);

    let process = ProcessInfo::current();
    assert!(process.process_identifier() > 0);
    assert!(process.processor_count() > 0);
    assert!(process.active_processor_count() > 0);
    assert!(process.physical_memory() > 0);

    let bundle = Bundle::main();
    let _ = bundle.is_loaded();

    let center = metal_rust::foundation::NotificationCenter::default_center();
    let deliveries = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
    let callback_deliveries = std::sync::Arc::clone(&deliveries);
    let registration = center.add_observer("MetalRustSafeNotification", move |notification| {
        assert_eq!(notification.name(), "MetalRustSafeNotification");
        callback_deliveries.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
    });
    center.post("MetalRustSafeNotification");
    assert_eq!(deliveries.load(std::sync::atomic::Ordering::SeqCst), 1);
    drop(registration);
    center.post("MetalRustSafeNotification");
    assert_eq!(deliveries.load(std::sync::atomic::Ordering::SeqCst), 1);
}

#[test]
fn generated_descriptor_properties_are_runtime_checked() {
    use metal_rust::metal::{ComputePipelineDescriptor, SamplerAddressMode, SamplerDescriptor};

    if let Ok(sampler) = SamplerDescriptor::new() {
        sampler.set_normalized_coordinates(false).unwrap();
        assert!(!sampler.normalized_coordinates().unwrap());
        sampler
            .set_s_address_mode(SamplerAddressMode::SamplerAddressModeClampToEdge)
            .unwrap();
        assert_eq!(
            sampler.s_address_mode().unwrap(),
            SamplerAddressMode::SamplerAddressModeClampToEdge
        );
        assert!(sampler.set_lod_min_clamp(f32::NAN).is_err());
        sampler.set_lod_min_clamp(0.5).unwrap();
        assert_eq!(sampler.lod_min_clamp().unwrap(), 0.5);
    }

    if let Ok(pipeline) = ComputePipelineDescriptor::new() {
        pipeline.set_label("generated-safe-property").unwrap();
        assert_eq!(
            pipeline.label().unwrap().as_deref(),
            Some("generated-safe-property")
        );
    }
}

#[test]
fn texture_descriptor_rejects_invalid_dimensions_and_mips() {
    let zero_width = TextureDescriptor::new_2d(
        PixelFormat::RGBA8_UNORM,
        0,
        1,
        ResourceOptions::SHARED,
        TextureUsage::SHADER_READ,
    )
    .err()
    .expect("zero width must be rejected before Metal");
    assert_eq!(zero_width.kind(), ErrorKind::InvalidArgument);

    let descriptor = TextureDescriptor::new_2d(
        PixelFormat::RGBA8_UNORM,
        1,
        1,
        ResourceOptions::SHARED,
        TextureUsage::SHADER_READ,
    )
    .expect("one-by-one descriptor is valid");
    let zero_mips = match descriptor.set_mipmap_level_count(0) {
        Ok(()) => panic!("zero mip levels must be rejected before Metal"),
        Err(error) => error,
    };
    assert_eq!(zero_mips.kind(), ErrorKind::InvalidArgument);
}

#[test]
fn metalfx_descriptors_reject_zero_dimensions_without_runtime_creation() {
    let spatial = match SpatialScalerDescriptor::new() {
        Ok(descriptor) => descriptor,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected spatial descriptor error: {error}"),
    };
    let spatial_error = match spatial.configure(
        PixelFormat::RGBA8_UNORM,
        PixelFormat::RGBA8_UNORM,
        0,
        1080,
        1920,
        1080,
    ) {
        Ok(()) => panic!("spatial zero width must be rejected"),
        Err(error) => error,
    };
    assert_eq!(spatial_error.kind(), ErrorKind::InvalidArgument);

    let temporal = match TemporalScalerDescriptor::new() {
        Ok(descriptor) => descriptor,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected temporal descriptor error: {error}"),
    };
    let temporal_error = match temporal.configure(
        PixelFormat::RGBA8_UNORM,
        PixelFormat::RGBA8_UNORM,
        PixelFormat::RGBA8_UNORM,
        PixelFormat::RGBA8_UNORM,
        1920,
        1080,
        0,
        1080,
    ) {
        Ok(()) => panic!("temporal zero width must be rejected"),
        Err(error) => error,
    };
    assert_eq!(temporal_error.kind(), ErrorKind::InvalidArgument);
}

#[test]
fn metalfx_scaler_creation_is_runtime_gated() {
    let Some(device) = Device::system_default() else {
        return;
    };
    let spatial = match SpatialScalerDescriptor::new() {
        Ok(descriptor) => descriptor,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected spatial descriptor error: {error}"),
    };
    spatial
        .configure(
            PixelFormat::BGRA8_UNORM,
            PixelFormat::BGRA8_UNORM,
            1920,
            1080,
            3840,
            2160,
        )
        .expect("valid spatial configuration");
    if spatial.supports_device(&device) {
        let scaler = match spatial.new_scaler(&device) {
            Ok(scaler) => scaler,
            Err(error) if error.kind() == ErrorKind::Unsupported => return,
            Err(error) => panic!("unexpected spatial scaler error: {error}"),
        };
        assert_ne!(scaler.output_texture_usage(), 0);
        scaler
            .set_input_content_size(1920, 1080)
            .expect("valid spatial content size");
    }

    let temporal = match TemporalScalerDescriptor::new() {
        Ok(descriptor) => descriptor,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected temporal descriptor error: {error}"),
    };
    temporal
        .configure(
            PixelFormat::BGRA8_UNORM,
            PixelFormat::DEPTH32_FLOAT,
            PixelFormat::RG16_FLOAT,
            PixelFormat::BGRA8_UNORM,
            1920,
            1080,
            3840,
            2160,
        )
        .expect("valid temporal configuration");
    match temporal.supported_input_content_min_scale(&device) {
        Ok(minimum) => assert!(minimum.is_finite() && minimum > 0.0),
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected temporal minimum-scale error: {error}"),
    }
    match temporal.supported_input_content_max_scale(&device) {
        Ok(maximum) => assert!(maximum.is_finite() && maximum > 0.0),
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected temporal maximum-scale error: {error}"),
    }
    if temporal.supports_device(&device) {
        let scaler = match temporal.new_scaler(&device) {
            Ok(scaler) => scaler,
            Err(error) if error.kind() == ErrorKind::Unsupported => return,
            Err(error) => panic!("unexpected temporal scaler error: {error}"),
        };
        assert_ne!(scaler.output_texture_usage(), 0);
        scaler
            .set_input_content_size(1920, 1080)
            .expect("valid temporal content size");
    }
}

#[test]
fn mtl4fx_temporal_scaler_is_runtime_gated() {
    let Some(device) = Device::system_default() else {
        return;
    };
    if !device
        .supports_family(metal_rust::metal::GPUFamily::GPUFamilyMetal4)
        .unwrap_or(false)
    {
        return;
    }
    let descriptor = match TemporalScalerDescriptor::new() {
        Ok(value) => value,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected temporal descriptor error: {error}"),
    };
    if !descriptor.supports_metal4_fx(&device) {
        return;
    }
    descriptor
        .configure(
            PixelFormat::RGBA16_FLOAT,
            PixelFormat::DEPTH32_FLOAT,
            PixelFormat::RG16_FLOAT,
            PixelFormat::RGBA16_FLOAT,
            960,
            540,
            1920,
            1080,
        )
        .expect("valid temporal configuration");
    let compiler = device
        .new_mtl4_compiler(&metal_rust::metal4::CompilerDescriptor::new().unwrap())
        .expect("Metal 4 compiler");
    let scaler = match descriptor.new_mtl4_scaler(&device, &compiler) {
        Ok(value) => value,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected MTL4FX temporal scaler error: {error}"),
    };
    scaler
        .set_input_content_width(960)
        .expect("valid input content width");
    scaler
        .set_input_content_height(540)
        .expect("valid input content height");
    scaler
        .set_jitter_offset_x(0.25)
        .expect("valid jitter offset");
    scaler
        .set_motion_vector_scale_x(480.0)
        .expect("valid motion vector scale");
    assert_eq!(
        scaler.set_jitter_offset_x(f32::NAN).unwrap_err().kind(),
        ErrorKind::InvalidArgument
    );
    assert_eq!(
        scaler.set_input_content_width(0).unwrap_err().kind(),
        ErrorKind::InvalidArgument
    );
}

#[test]
fn metal_layer_is_owned_and_configurable_without_a_device() {
    let layer = match Layer::new() {
        Ok(layer) => layer,
        Err(error) if error.kind() == ErrorKind::InvalidArgument => {
            assert!(error.message().contains("main thread"));
            return;
        }
        Err(error) => panic!("unexpected layer error: {error}"),
    };
    layer.set_pixel_format(PixelFormat::BGRA8_UNORM);
    assert!(layer.device().is_none());
}

#[test]
fn default_device_has_an_owned_name() {
    let Some(device) = Device::system_default() else {
        return;
    };
    assert!(!device.name().is_empty());
}

#[test]
fn counter_count_is_checked_before_metal() {
    let Some(device) = Device::system_default() else {
        return;
    };
    let zero = device.new_timestamp_counter_heap(0).err().unwrap();
    assert_eq!(zero.kind(), ErrorKind::InvalidArgument);
    let too_large = device
        .new_timestamp_counter_heap(MAX_TIMESTAMP_COUNTERS + 1)
        .err()
        .unwrap();
    assert_eq!(too_large.kind(), ErrorKind::InvalidArgument);
}

#[test]
fn metal4_counter_heap_is_safe_when_available() {
    let Some(device) = Device::system_default() else {
        return;
    };
    match device.new_timestamp_counter_heap(2) {
        Ok(heap) => assert_eq!(heap.count(), 2),
        Err(error) if error.kind() == ErrorKind::Unsupported => {}
        Err(error) => panic!("unexpected Metal error: {error}"),
    }
}

#[test]
fn metal4_texture_readback_round_trip_when_available() {
    let Some(device) = Device::system_default() else {
        return;
    };
    let queue = match device.new_mtl4_command_queue() {
        Ok(queue) => queue,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected Metal 4 queue error: {error}"),
    };
    let texture_descriptor = TextureDescriptor::new_2d(
        PixelFormat::RGBA8_UNORM,
        2,
        2,
        ResourceOptions::SHARED,
        TextureUsage::SHADER_READ,
    )
    .expect("readable texture descriptor is valid");
    let texture = match device.new_texture(&texture_descriptor) {
        Ok(texture) => texture,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected readback texture error: {error}"),
    };
    let source = [1_u8, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];
    let mut upload = [0_u8; 40];
    upload[..source.len()].copy_from_slice(&source);
    texture
        .replace_region_2d(Region::new_2d(0, 0, 2, 2), 0, &upload, 8)
        .expect("shared texture can be initialized");
    let buffer = match device.new_buffer(source.len(), ResourceOptions::SHARED) {
        Ok(buffer) => buffer,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected readback buffer error: {error}"),
    };
    let residency_descriptor = metal_rust::metal::ResidencySetDescriptor::new()
        .expect("residency-set descriptor is available");
    residency_descriptor
        .set_initial_capacity(2)
        .expect("residency capacity is valid");
    let residency = match device.new_residency_set(&residency_descriptor) {
        Ok(residency) => residency,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected residency-set error: {error}"),
    };
    residency
        .add_allocations(&[
            metal_rust::metal::ResidencyAllocation::Texture(&texture),
            metal_rust::metal::ResidencyAllocation::Buffer(&buffer),
        ])
        .expect("readback resources can be made resident");
    residency
        .commit()
        .expect("residency changes can be committed");
    queue
        .add_residency_set(&residency)
        .expect("residency set can be attached to queue");

    let allocator = match device.new_mtl4_command_allocator() {
        Ok(allocator) => allocator,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected Metal 4 allocator error: {error}"),
    };
    let mut command_buffer = match device
        .new_mtl4_command_buffer()
        .and_then(|buffer| buffer.begin(&allocator, None))
    {
        Ok(command_buffer) => command_buffer,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected Metal 4 command-buffer error: {error}"),
    };
    {
        let encoder = command_buffer
            .compute_encoder()
            .expect("Metal 4 compute encoder is available");
        encoder
            .copy_texture_to_buffer(
                &texture,
                metal_rust::metal4::TextureRegionSelection {
                    slice: 0,
                    level: 0,
                    region: Region::new_2d(0, 0, 2, 2),
                },
                &buffer,
                metal_rust::metal4::BufferImageLayout {
                    offset: 0,
                    bytes_per_row: 8,
                    bytes_per_image: source.len(),
                },
                None,
            )
            .expect("texture copy can be encoded");
        encoder.end().expect("compute encoder can end");
    }
    queue
        .submit(
            vec![command_buffer.end().expect("command buffer can end")],
            None,
        )
        .expect("Metal 4 submission succeeds")
        .wait()
        .expect("Metal 4 submission completes");
    assert_eq!(
        buffer
            .read(0, source.len())
            .expect("readback buffer is readable"),
        source
    );
}

#[test]
fn core_submission_smoke_when_available() {
    let Some(device) = Device::system_default() else {
        return;
    };
    let queue = match device.new_command_queue(Some(2)) {
        Ok(queue) => queue,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected queue error: {error}"),
    };
    queue.set_label(Some("metal-rust-safe-api-test"));
    assert_eq!(queue.label().as_deref(), Some("metal-rust-safe-api-test"));

    let buffer = match device.new_buffer(64, ResourceOptions::SHARED) {
        Ok(buffer) => buffer,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected buffer error: {error}"),
    };
    assert_eq!(buffer.length(), 64);
    buffer
        .write(4, &[1, 2, 3, 4])
        .expect("shared buffer is writable");
    assert_eq!(
        buffer.read(4, 4).expect("shared buffer is readable"),
        [1, 2, 3, 4]
    );
    let range_error = match buffer.write(63, &[1, 2]) {
        Ok(()) => panic!("buffer range must be checked"),
        Err(error) => error,
    };
    assert_eq!(range_error.kind(), ErrorKind::InvalidArgument);
    let read_range_error = match buffer.read(63, 2) {
        Ok(_) => panic!("buffer read range must be checked"),
        Err(error) => error,
    };
    assert_eq!(read_range_error.kind(), ErrorKind::InvalidArgument);

    let destination = match device.new_buffer(64, ResourceOptions::SHARED) {
        Ok(buffer) => buffer,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected destination buffer error: {error}"),
    };
    let private_destination = match device.new_buffer(64, ResourceOptions::PRIVATE) {
        Ok(buffer) => buffer,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected private destination error: {error}"),
    };
    let mut command_buffer = match queue.command_buffer() {
        Ok(command_buffer) => command_buffer,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected command buffer error: {error}"),
    };
    let (completion_sender, completion_receiver) = std::sync::mpsc::channel();
    command_buffer
        .on_complete(move |result| {
            let _ = completion_sender.send(result);
        })
        .expect("completion handler registration");
    let (readback, mismatched_readback) = {
        let blit = match command_buffer.blit_encoder() {
            Ok(blit) => blit,
            Err(error) if error.kind() == ErrorKind::Unsupported => return,
            Err(error) => panic!("unexpected blit encoder error: {error}"),
        };
        blit.copy_buffer(&buffer, 4, &destination, 8, 4)
            .expect("checked shared-buffer copy must encode");
        blit.copy_buffer(&buffer, 4, &private_destination, 8, 4)
            .expect("checked private-buffer copy must encode");
        let readback = blit
            .read_buffer(&private_destination, 8, 4)
            .expect("private buffer readback uses staging");
        let mismatched_readback = blit
            .read_buffer(&private_destination, 8, 4)
            .expect("second staged readback is recorded");
        blit.end_encoding();
        (readback, mismatched_readback)
    };
    let completed = command_buffer
        .commit()
        .wait()
        .expect("command buffer completes");
    assert_eq!(
        completed.status(),
        metal_rust::CommandBufferStatus::Completed,
        "command buffer did not complete"
    );
    assert_eq!(completed.resolve_buffer(readback).unwrap(), [1, 2, 3, 4]);
    completion_receiver
        .recv_timeout(std::time::Duration::from_secs(1))
        .expect("completion callback delivery")
        .expect("completion callback result");

    let other_completed = queue
        .command_buffer()
        .expect("second command buffer")
        .commit()
        .wait()
        .expect("second command buffer completes");
    let mismatch = other_completed
        .resolve_buffer(mismatched_readback)
        .expect_err("submission identity mismatch must be rejected");
    assert_eq!(mismatch.kind(), ErrorKind::InvalidArgument);
}

#[test]
fn shader_pipeline_and_render_compute_encoders_smoke_when_available() {
    let Some(device) = Device::system_default() else {
        return;
    };
    let source = r#"
        #include <metal_stdlib>
        using namespace metal;

        kernel void compute_main(device uint *data [[buffer(0)]],
                                 uint id [[thread_position_in_grid]]) {
            if (id == 0) {
                data[0] = 42;
            }
        }

        struct VertexOut {
            float4 position [[position]];
        };

        vertex VertexOut vertex_main(uint vertex_id [[vertex_id]]) {
            constexpr float2 positions[3] = {
                float2(-1.0, -1.0), float2(3.0, -1.0), float2(-1.0, 3.0)
            };
            return VertexOut{float4(positions[vertex_id], 0.0, 1.0)};
        }

        fragment float4 fragment_main() {
            return float4(1.0, 0.0, 0.0, 1.0);
        }
    "#;
    let library =
        match device.new_library_from_source(source, Some(&metal_rust::CompileOptions::strict())) {
            Ok(library) => library,
            Err(error) if error.kind() == ErrorKind::Unsupported => return,
            Err(error) => panic!("unexpected shader compilation error: {error}"),
        };
    let compute_function = library
        .function("compute_main")
        .expect("compute function exists");
    let vertex_function = library
        .function("vertex_main")
        .expect("vertex function exists");
    let fragment_function = library
        .function("fragment_main")
        .expect("fragment function exists");
    let compute_pipeline = match device.new_compute_pipeline(&compute_function) {
        Ok(pipeline) => pipeline,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected compute pipeline error: {error}"),
    };
    let render_pipeline =
        match device.new_render_pipeline(&metal_rust::RenderPipelineDescriptor::new(
            &vertex_function,
            Some(&fragment_function),
            PixelFormat::BGRA8_UNORM,
        )) {
            Ok(pipeline) => pipeline,
            Err(error) if error.kind() == ErrorKind::Unsupported => return,
            Err(error) => panic!("unexpected render pipeline error: {error}"),
        };
    assert!(compute_pipeline.max_total_threads_per_threadgroup() > 0);

    let texture_descriptor = TextureDescriptor::new_2d(
        PixelFormat::BGRA8_UNORM,
        4,
        4,
        ResourceOptions::SHARED,
        TextureUsage::RENDER_TARGET,
    )
    .expect("render texture descriptor is valid");
    let texture = match device.new_texture(&texture_descriptor) {
        Ok(texture) => texture,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected texture error: {error}"),
    };
    let buffer = match device.new_buffer(16, ResourceOptions::SHARED) {
        Ok(buffer) => buffer,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected shader buffer error: {error}"),
    };
    let queue = match device.new_command_queue(None) {
        Ok(queue) => queue,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected shader queue error: {error}"),
    };
    let mut command_buffer = match queue.command_buffer() {
        Ok(command_buffer) => command_buffer,
        Err(error) if error.kind() == ErrorKind::Unsupported => return,
        Err(error) => panic!("unexpected shader command buffer error: {error}"),
    };
    {
        let encoder = command_buffer
            .compute_encoder(&metal_rust::ComputePassDescriptor::new())
            .expect("compute encoder exists");
        encoder.set_pipeline(&compute_pipeline);
        encoder
            .set_buffer(&buffer, 0, 0)
            .expect("compute buffer binding is valid");
        encoder
            .dispatch_1d(1, 1)
            .expect("one-thread dispatch is valid");
        encoder.end_encoding();
    }
    {
        let pass = metal_rust::RenderPassDescriptor::new();
        pass.set_color_attachment(0, &texture, ClearColor::new(0.0, 0.0, 0.0, 1.0))
            .expect("color attachment index is valid");
        let encoder = command_buffer
            .render_encoder(&pass)
            .expect("render encoder exists");
        encoder.set_pipeline(&render_pipeline);
        encoder
            .set_viewport(metal_rust::Viewport::new(0.0, 0.0, 4.0, 4.0, 0.0, 1.0))
            .expect("finite viewport is valid");
        encoder
            .draw_primitives(metal_rust::PrimitiveType::Triangle, 0, 3)
            .expect("triangle draw is valid");
        encoder.end_encoding();
    }
    let texture_readback = {
        let blit = command_buffer.blit_encoder().expect("texture blit encoder");
        let readback = blit
            .read_texture(
                &texture,
                Region::new_2d(0, 0, texture.width(), texture.height()),
            )
            .expect("texture staging readback");
        blit.end_encoding();
        readback
    };
    let completed = command_buffer
        .commit()
        .wait()
        .expect("command buffer completes");
    assert_eq!(
        completed.status(),
        metal_rust::CommandBufferStatus::Completed,
        "shader command buffer did not complete"
    );
    let image = completed
        .resolve_texture(texture_readback)
        .expect("texture readback resolves against its submission");
    assert_eq!((image.width, image.height), (4, 4));
    assert!(image.bytes_per_row >= 16);
    assert_eq!(&image.bytes[..4], &[0, 0, 255, 255]);
}

#[test]
fn drawable_and_capture_paths_are_runtime_gated() {
    let Some(device) = Device::system_default() else {
        return;
    };
    let layer = match Layer::with_device(&device) {
        Ok(layer) => layer,
        Err(error) if error.kind() == ErrorKind::InvalidArgument => return,
        Err(error) => panic!("unexpected layer error: {error}"),
    };
    layer.set_pixel_format(PixelFormat::BGRA8_UNORM);
    if let Ok(drawable) = layer.next_drawable() {
        let queue = match device.new_command_queue(None) {
            Ok(queue) => queue,
            Err(error) if error.kind() == ErrorKind::Unsupported => return,
            Err(error) => panic!("unexpected drawable queue error: {error}"),
        };
        let mut command_buffer = queue.command_buffer().expect("drawable command buffer");
        command_buffer.present_drawable(&drawable);
        command_buffer
            .commit()
            .wait()
            .expect("drawable command buffer completes");
    }

    let path = std::env::temp_dir().join(format!(
        "metal-rust-safe-api-{}.gputrace",
        std::process::id()
    ));
    match metal_rust::CaptureSession::start(&device, &path) {
        Ok(session) => session.finish(),
        Err(error) if error.kind() == ErrorKind::Unsupported => {}
        Err(error) => panic!("unexpected capture error: {error}"),
    }
    let _ = std::fs::remove_file(path);
}
