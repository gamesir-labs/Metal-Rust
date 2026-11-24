#!/usr/bin/env python3
"""Generate the explicit metal-cpp to safe-Rust coverage ledger."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from generate_value_types import EXTENSIBLE_MANUAL_TYPES, MANUAL_TYPES
from generate_struct_types import MANUAL_STRUCTS, snake_case
from generate_facade_types import (
    available_object_names,
    generated_facade_alias_paths,
    generated_facade_method_paths,
    module_for,
)


ACTUAL_CLASSES = {
    "NS::Bundle": "foundation::Bundle",
    "NS::Notification": "foundation::Notification",
    "NS::NotificationCenter": "foundation::NotificationCenter",
    "NS::ProcessInfo": "foundation::ProcessInfo",
    "NS::URL": "foundation::URL",
    "MTL4::CounterHeap": "metal4::TimestampCounterHeap",
    "MTL::CaptureManager": "metal::CaptureSession",
    "MTL::Device": "metal::Device",
    "MTL::Function": "metal::Function",
    "MTL::Library": "metal::Library",
    "MTL::CommandQueue": "metal::CommandQueue",
    "MTL::CommandBuffer": "metal::CommandBuffer",
    "MTL::Buffer": "metal::Buffer",
    "MTL::Texture": "metal::Texture",
    "MTL::TextureDescriptor": "metal::TextureDescriptor",
    "MTL::CompileOptions": "metal::CompileOptions",
    "MTL::RenderCommandEncoder": "metal::RenderCommandEncoder",
    "MTL::ComputeCommandEncoder": "metal::ComputeCommandEncoder",
    "MTL::BlitCommandEncoder": "metal::BlitCommandEncoder",
    "MTL::ComputePassDescriptor": "metal::ComputePassDescriptor",
    "MTL4::CommandBuffer": "metal4::AvailableCommandBuffer",
    "MTL4::CommandEncoder": "metal4::RecordingComputeEncoder",
    "MTL4::ComputeCommandEncoder": "metal4::RecordingComputeEncoder",
    "MTL4::MachineLearningCommandEncoder": "metal4::RecordingMachineLearningEncoder",
    "MTL4::RenderCommandEncoder": "metal4::RecordingRenderEncoder",
    "MTL::RenderPipelineState": "metal::RenderPipelineState",
    "MTL::RenderPipelineDescriptor": "metal::RenderPipelineDescriptor",
    "MTL::RenderPassDescriptor": "metal::RenderPassDescriptor",
    "MTL::ComputePipelineState": "metal::ComputePipelineState",
    "MTLFX::SpatialScalerDescriptor": "metal_fx::SpatialScalerDescriptor",
    "MTLFX::SpatialScaler": "metal_fx::SpatialScaler",
    "MTLFX::TemporalScalerDescriptor": "metal_fx::TemporalScalerDescriptor",
    "MTLFX::TemporalScaler": "metal_fx::TemporalScaler",
    "CA::MetalLayer": "quartz_core::Layer",
    "CA::MetalDrawable": "quartz_core::Drawable",
}

FOUNDATION_SUBSTITUTE_CLASSES = {
    "NS::Array": "foundation::Array",
    "NS::AutoreleasePool": "foundation::Object",
    "NS::Condition": "foundation::Condition",
    "NS::Copying": "foundation::Copying",
    "NS::Data": "foundation::Data",
    "NS::Date": "foundation::Date",
    "NS::Dictionary": "foundation::Dictionary",
    "NS::Enumerator": "foundation::Enumerator",
    "NS::Error": "foundation::Error",
    "NS::FastEnumeration": "foundation::Enumerator",
    "NS::Locking": "foundation::Locking",
    "NS::Number": "foundation::Number",
    "NS::Object": "foundation::Object",
    "NS::Referencing": "foundation::Object",
    "NS::SecureCoding": "foundation::SecureCoding",
    "NS::Set": "foundation::Set",
    "NS::String": "foundation::String",
    "NS::Value": "foundation::Value",
    "SharedPtr": "foundation::Object",
}

TYPESTATE_SUBSTITUTE_CLASSES = {
    "MTL4::CommandBuffer",
    "MTL4::CommandEncoder",
    "MTL4::ComputeCommandEncoder",
    "MTL4::MachineLearningCommandEncoder",
    "MTL4::RenderCommandEncoder",
}

FOUNDATION_SUBSTITUTE_METHODS = {
    ("NS::Bundle", "alloc"): "foundation::Bundle::main",
    ("NS::Bundle", "init"): "foundation::Bundle::main",
    ("NS::Bundle", "unload"): "foundation::Bundle",
    ("NS::NotificationCenter", "removeObserver"): "foundation::Registration",
    ("NS::Notification", "object"): "foundation::Notification::object_description",
    ("NS::Notification", "userInfo"): "foundation::Notification::user_info_description",
    ("NS::Array", "array"): "foundation::Array::from",
    ("NS::Array", "alloc"): "foundation::Array::new",
    ("NS::Array", "init"): "foundation::Array::from",
    ("NS::Array", "count"): "foundation::Array::len",
    ("NS::Array", "objectEnumerator"): "foundation::enumerate",
    ("NS::AutoreleasePool", "alloc"): "foundation::Object",
    ("NS::AutoreleasePool", "init"): "foundation::Object",
    ("NS::AutoreleasePool", "drain"): "foundation::Object",
    ("NS::AutoreleasePool", "addObject"): "foundation::Object",
    ("NS::AutoreleasePool", "showPools"): "foundation::Object",
    ("NS::Data", "bytes"): "foundation::Data::as_slice",
    ("NS::Data", "length"): "foundation::Data::len",
    ("NS::Date", "dateWithTimeIntervalSinceNow"): "foundation::date_with_time_interval_since_now",
    ("NS::Dictionary", "dictionary"): "foundation::Dictionary::from_iter",
    ("NS::Dictionary", "alloc"): "foundation::Dictionary::new",
    ("NS::Dictionary", "init"): "foundation::Dictionary::from_iter",
    ("NS::Dictionary", "count"): "foundation::Dictionary::len",
    ("NS::Set", "alloc"): "foundation::Set::new",
    ("NS::Set", "init"): "foundation::Set::from_iter",
    ("NS::Set", "count"): "foundation::Set::len",
    ("NS::Set", "objectEnumerator"): "foundation::enumerate",
    ("NS::String", "string"): "foundation::String::from",
    ("NS::String", "alloc"): "foundation::String::new",
    ("NS::String", "init"): "foundation::String::from",
    ("NS::String", "character"): "foundation::StringExt::character",
    ("NS::String", "length"): "foundation::String::len",
    ("NS::String", "cString"): "foundation::String::as_bytes",
    ("NS::String", "utf8String"): "foundation::String::as_bytes",
    ("NS::String", "maximumLengthOfBytes"): "foundation::String::len",
    ("NS::String", "lengthOfBytes"): "foundation::String::len",
    ("NS::String", "isEqualToString"): "foundation::is_equal",
    ("NS::String", "rangeOfString"): "foundation::StringExt::range_of",
    ("NS::String", "fileSystemRepresentation"): "foundation::String::as_bytes",
    ("NS::String", "stringByAppendingString"): "foundation::append_string",
    ("NS::String", "caseInsensitiveCompare"): "foundation::StringExt::compare_case_insensitive",
    ("NS::Copying", "copy"): "foundation::Copying::copy_owned",
    ("NS::Error", "alloc"): "foundation::Error",
    ("NS::Error", "init"): "foundation::Error",
    ("NS::Error", "code"): "foundation::Error::code",
    ("NS::Error", "domain"): "foundation::Error::domain",
    ("NS::FastEnumeration", "countByEnumerating"): "foundation::enumerate",
    ("NS::Enumerator", "nextObject"): "foundation::Enumerator::next",
    ("NS::Locking", "lock"): "foundation::Locking::with_lock",
    ("NS::Locking", "unlock"): "foundation::Locking::with_lock",
    ("NS::Referencing", "retain"): "foundation::Object",
    ("NS::Referencing", "release"): "foundation::Object",
    ("NS::Referencing", "autorelease"): "foundation::Object",
    ("NS::Referencing", "retainCount"): "foundation::Object",
    ("NS::Object", "hash"): "foundation::Object::object_hash",
    ("NS::Object", "isEqual"): "foundation::Object::object_is_equal",
    ("NS::Condition", "alloc"): "foundation::Condition::new",
    ("NS::Condition", "init"): "foundation::Condition::new",
    ("NS::Condition", "wait"): "foundation::Condition::wait",
    ("NS::Condition", "waitUntilDate"): "foundation::Condition::wait_until",
    ("NS::Condition", "signal"): "foundation::Condition::signal",
    ("NS::Condition", "broadcast"): "foundation::Condition::broadcast",
    ("NS::Value", "value"): "foundation::Value::new",
    ("NS::Value", "alloc"): "foundation::Value::new",
    ("NS::Value", "init"): "foundation::Value::new",
    ("NS::Value", "getValue"): "foundation::Value::downcast_ref",
    ("NS::Value", "objCType"): "foundation::Value::downcast_ref",
    ("NS::Value", "isEqualToValue"): "foundation::Value::downcast_ref",
    ("NS::Value", "pointerValue"): "foundation::Value::downcast_ref",
    ("NS::URL", "alloc"): "foundation::URL::from_file_path",
    ("NS::URL", "init"): "foundation::URL::from_file_path",
    ("NS::Number", "number"): "foundation::Number::from",
    ("NS::Number", "alloc"): "foundation::Number::from",
    ("NS::Number", "init"): "foundation::Number::from",
    ("NS::Number", "charValue"): "foundation::Number::as_i64",
    ("NS::Number", "unsignedCharValue"): "foundation::Number::as_u64",
    ("NS::Number", "shortValue"): "foundation::Number::as_i64",
    ("NS::Number", "unsignedShortValue"): "foundation::Number::as_u64",
    ("NS::Number", "intValue"): "foundation::Number::as_i64",
    ("NS::Number", "unsignedIntValue"): "foundation::Number::as_u64",
    ("NS::Number", "longValue"): "foundation::Number::as_i64",
    ("NS::Number", "unsignedLongValue"): "foundation::Number::as_u64",
    ("NS::Number", "longLongValue"): "foundation::Number::as_i64",
    ("NS::Number", "unsignedLongLongValue"): "foundation::Number::as_u64",
    ("NS::Number", "floatValue"): "foundation::Number::as_f64",
    ("NS::Number", "doubleValue"): "foundation::Number::as_f64",
    ("NS::Number", "boolValue"): "foundation::Number::as_bool",
    ("NS::Number", "integerValue"): "foundation::Number::as_i64",
    ("NS::Number", "unsignedIntegerValue"): "foundation::Number::as_u64",
    ("NS::Number", "compare"): "foundation::Number::compare",
    ("NS::Number", "isEqualToNumber"): "foundation::is_equal",
    ("SharedPtr", "SharedPtr"): "foundation::Object",
    ("SharedPtr", "~SharedPtr"): "foundation::Object",
    ("SharedPtr", "operator="): "foundation::Object",
    ("SharedPtr", "get"): "foundation::Object",
    ("SharedPtr", "operator->"): "foundation::Object",
    ("SharedPtr", "operatorbool"): "foundation::Object",
    ("SharedPtr", "reset"): "foundation::Object",
    ("SharedPtr", "detach"): "foundation::Object",
    ("NS::Range", "Make"): "foundation::Range::new",
    ("NS::Range", "Range"): "foundation::Range::new",
    ("NS::Range", "Equal"): "foundation::is_equal",
    ("NS::Range", "LocationInRange"): "foundation::Range::contains",
    ("NS::Range", "Max"): "foundation::Range::end",
}

ACTUAL_VALUES = {
    "MTL::ClearColor": "metal::ClearColor",
    "MTL::CommandBufferStatus": "metal::CommandBufferStatus",
    "MTL::Origin": "metal::Origin",
    "MTL::PixelFormat": "metal::PixelFormat",
    "MTL::PrimitiveType": "metal::PrimitiveType",
    "MTL::Region": "metal::Region",
    "MTL::ResourceOptions": "metal::ResourceOptions",
    "MTL::Size": "metal::Size",
    "MTL::StorageMode": "metal::StorageMode",
    "MTL::TextureType": "metal::TextureType",
    "MTL::TextureUsage": "metal::TextureUsage",
    "MTL::Viewport": "metal::Viewport",
    "MTLFX::SpatialScalerColorProcessingMode": "metal_fx::SpatialScalerColorProcessingMode",
}

MANUAL_ENUM_MEMBERS = {
    ("MTL::CommandBufferStatus", "CommandBufferStatusNotEnqueued"): "metal::CommandBufferStatus::NotEnqueued",
    ("MTL::CommandBufferStatus", "CommandBufferStatusEnqueued"): "metal::CommandBufferStatus::Enqueued",
    ("MTL::CommandBufferStatus", "CommandBufferStatusCommitted"): "metal::CommandBufferStatus::Committed",
    ("MTL::CommandBufferStatus", "CommandBufferStatusScheduled"): "metal::CommandBufferStatus::Scheduled",
    ("MTL::CommandBufferStatus", "CommandBufferStatusCompleted"): "metal::CommandBufferStatus::Completed",
    ("MTL::CommandBufferStatus", "CommandBufferStatusError"): "metal::CommandBufferStatus::Error",
    ("MTL::PrimitiveType", "PrimitiveTypePoint"): "metal::PrimitiveType::Point",
    ("MTL::PrimitiveType", "PrimitiveTypeLine"): "metal::PrimitiveType::Line",
    ("MTL::PrimitiveType", "PrimitiveTypeLineStrip"): "metal::PrimitiveType::LineStrip",
    ("MTL::PrimitiveType", "PrimitiveTypeTriangle"): "metal::PrimitiveType::Triangle",
    ("MTL::PrimitiveType", "PrimitiveTypeTriangleStrip"): "metal::PrimitiveType::TriangleStrip",
    ("MTL::StorageMode", "StorageModeShared"): "metal::StorageMode::Shared",
    ("MTL::StorageMode", "StorageModeManaged"): "metal::StorageMode::Managed",
    ("MTL::StorageMode", "StorageModePrivate"): "metal::StorageMode::Private",
    ("MTL::StorageMode", "StorageModeMemoryless"): "metal::StorageMode::Memoryless",
    ("MTL::TextureType", "TextureType2D"): "metal::TextureType::D2",
    ("MTL::TextureType", "TextureType2DArray"): "metal::TextureType::D2Array",
    ("MTL::TextureType", "TextureType1D"): "metal::TextureType::D1",
    ("MTL::TextureType", "TextureType1DArray"): "metal::TextureType::D1Array",
    ("MTL::TextureType", "TextureType2DMultisample"): "metal::TextureType::D2Multisample",
    ("MTL::TextureType", "TextureType2DMultisampleArray"): "metal::TextureType::D2MultisampleArray",
    ("MTL::TextureType", "TextureType3D"): "metal::TextureType::D3",
    ("MTL::TextureType", "TextureTypeCube"): "metal::TextureType::Cube",
    ("MTL::TextureType", "TextureTypeCubeArray"): "metal::TextureType::CubeArray",
    ("MTL::TextureType", "TextureTypeTextureBuffer"): "metal::TextureType::TextureBuffer",
    ("MTLFX::SpatialScalerColorProcessingMode", "SpatialScalerColorProcessingModePerceptual"): "metal_fx::SpatialScalerColorProcessingMode::PERCEPTUAL",
    ("MTLFX::SpatialScalerColorProcessingMode", "SpatialScalerColorProcessingModeLinear"): "metal_fx::SpatialScalerColorProcessingMode::LINEAR",
    ("MTLFX::SpatialScalerColorProcessingMode", "SpatialScalerColorProcessingModeHDR"): "metal_fx::SpatialScalerColorProcessingMode::HDR",
}

ACTUAL_METHODS = {
    ("NS::Bundle", "mainBundle"): "foundation::Bundle::main",
    ("NS::Bundle", "load"): "foundation::Bundle::load",
    ("NS::Bundle", "isLoaded"): "foundation::Bundle::is_loaded",
    ("NS::Notification", "name"): "foundation::Notification::name",
    ("NS::NotificationCenter", "addObserver"): "foundation::NotificationCenter::add_observer",
    ("NS::ProcessInfo", "processInfo"): "foundation::ProcessInfo::current",
    ("NS::ProcessInfo", "setProcessName"): "foundation::ProcessInfo::set_process_name",
    ("NS::ProcessInfo", "processIdentifier"): "foundation::ProcessInfo::process_identifier",
    ("NS::ProcessInfo", "operatingSystem"): "foundation::ProcessInfo::operating_system_version",
    ("NS::ProcessInfo", "operatingSystemVersion"): "foundation::ProcessInfo::operating_system_version",
    ("NS::ProcessInfo", "isOperatingSystemAtLeastVersion"): "foundation::ProcessInfo::is_operating_system_at_least",
    ("NS::ProcessInfo", "processorCount"): "foundation::ProcessInfo::processor_count",
    ("NS::ProcessInfo", "activeProcessorCount"): "foundation::ProcessInfo::active_processor_count",
    ("NS::ProcessInfo", "physicalMemory"): "foundation::ProcessInfo::physical_memory",
    ("NS::ProcessInfo", "systemUptime"): "foundation::ProcessInfo::system_uptime",
    ("NS::ProcessInfo", "disableSuddenTermination"): "foundation::ProcessInfo::disable_sudden_termination",
    ("NS::ProcessInfo", "enableSuddenTermination"): "foundation::ProcessInfo::enable_sudden_termination",
    ("NS::ProcessInfo", "automaticTerminationSupportEnabled"): "foundation::ProcessInfo::automatic_termination_support_enabled",
    ("NS::ProcessInfo", "setAutomaticTerminationSupportEnabled"): "foundation::ProcessInfo::set_automatic_termination_support_enabled",
    ("NS::ProcessInfo", "thermalState"): "foundation::ProcessInfo::thermal_state",
    ("NS::ProcessInfo", "isLowPowerModeEnabled"): "foundation::ProcessInfo::is_low_power_mode_enabled",
    ("NS::ProcessInfo", "isiOSAppOnMac"): "foundation::ProcessInfo::is_ios_app_on_mac",
    ("NS::ProcessInfo", "isMacCatalystApp"): "foundation::ProcessInfo::is_mac_catalyst_app",
    ("NS::ProcessInfo", "isDeviceCertified"): "foundation::ProcessInfo::is_device_certified",
    ("NS::ProcessInfo", "hasPerformanceProfile"): "foundation::ProcessInfo::has_performance_profile",
    ("NS::URL", "alloc"): "foundation::URL::from_file_path",
    ("NS::URL", "init"): "foundation::URL::from_file_path",
    ("NS::URL", "fileSystemRepresentation"): "foundation::URL::file_path",
    ("MTL4::CounterHeap", "count"): "metal::TimestampCounterHeap::count",
    ("MTL::CaptureManager", "sharedCaptureManager"): "metal::CaptureSession::start",
    ("MTL::Device", "name"): "metal::Device::name",
    ("MTL::CommandQueue", "label"): "metal::CommandQueue::label",
    ("MTL::CommandQueue", "setLabel"): "metal::CommandQueue::set_label",
    ("MTL::CommandBuffer", "commit"): "metal::CommandBuffer::commit",
    ("MTL::CommandBuffer", "waitUntilCompleted"): "metal::SubmittedCommandBuffer::wait",
    ("MTL::CommandBuffer", "presentDrawable"): "metal::CommandBuffer::present_drawable",
    ("MTL::CommandBuffer", "status"): "metal::CommandBuffer::status",
    ("MTL::CommandBuffer", "error"): "metal::CommandBuffer::error",
    ("MTL::CommandBuffer", "renderCommandEncoderWithDescriptor"): "metal::CommandBuffer::render_encoder",
    ("MTL::CommandBuffer", "computeCommandEncoderWithDescriptor"): "metal::CommandBuffer::compute_encoder",
    ("MTL::Buffer", "length"): "metal::Buffer::length",
    ("MTL::Buffer", "contents"): "metal::Buffer::write",
    ("MTL::Buffer", "didModifyRange"): "metal::Buffer::write",
    ("MTL::Texture", "width"): "metal::Texture::width",
    ("MTL::Texture", "height"): "metal::Texture::height",
    ("MTL::Texture", "storageMode"): "metal::Texture::storage_mode",
    ("MTL::Device", "supportsTextureSampleCount"): "metal::Device::supports_texture_sample_count",
    ("MTL::Function", "name"): "metal::Function::name",
    ("MTL::ComputePipelineState", "threadExecutionWidth"): "metal::ComputePipelineState::execution_width",
    ("MTL::ComputePipelineState", "maxTotalThreadsPerThreadgroup"): "metal::ComputePipelineState::max_total_threads_per_threadgroup",
    ("MTL::ComputeCommandEncoder", "dispatchType"): "metal::ComputeCommandEncoder::dispatch_type",
    ("MTL::ComputeCommandEncoder", "setTexture"): "metal::ComputeCommandEncoder::set_texture",
    ("MTL::ComputeCommandEncoder", "setTextures"): "metal::ComputeCommandEncoder::set_textures",
    ("MTL::ComputeCommandEncoder", "setImageblockWidth"): "metal::ComputeCommandEncoder::set_imageblock_size",
    ("MTL::ComputeCommandEncoder", "setThreadgroupMemoryLength"): "metal::ComputeCommandEncoder::set_threadgroup_memory_length",
    ("MTL::RenderPipelineState", "maxTotalThreadsPerThreadgroup"): "metal::RenderPipelineState::max_total_threads_per_threadgroup",
    ("MTLFX::SpatialScalerDescriptor", "newSpatialScaler"): "metal_fx::SpatialScalerDescriptor::new_scaler",
    ("MTLFX::SpatialScalerDescriptor", "supportsDevice"): "metal_fx::SpatialScalerDescriptor::supports_device",
    ("MTLFX::SpatialScaler", "encodeToCommandBuffer"): "metal_fx::SpatialScaler::encode",
    ("MTLFX::SpatialScalerBase", "colorTextureUsage"): "metal_fx::SpatialScaler::color_texture_usage",
    ("MTLFX::SpatialScalerBase", "outputTextureUsage"): "metal_fx::SpatialScaler::output_texture_usage",
    ("MTLFX::SpatialScalerBase", "setInputContentWidth"): "metal_fx::SpatialScaler::set_input_content_size",
    ("MTLFX::SpatialScalerBase", "setInputContentHeight"): "metal_fx::SpatialScaler::set_input_content_size",
    ("MTLFX::SpatialScalerBase", "setColorTexture"): "metal_fx::SpatialScaler::set_textures",
    ("MTLFX::SpatialScalerBase", "setOutputTexture"): "metal_fx::SpatialScaler::set_textures",
    ("MTLFX::TemporalScalerDescriptor", "newTemporalScaler"): "metal_fx::TemporalScalerDescriptor::new_scaler",
    ("MTLFX::TemporalScalerDescriptor", "supportsDevice"): "metal_fx::TemporalScalerDescriptor::supports_device",
    ("MTLFX::TemporalScalerDescriptor", "supportedInputContentMinScale"): "metal_fx::TemporalScalerDescriptor::supported_input_content_min_scale",
    ("MTLFX::TemporalScalerDescriptor", "supportedInputContentMaxScale"): "metal_fx::TemporalScalerDescriptor::supported_input_content_max_scale",
    ("MTLFX::TemporalScaler", "encodeToCommandBuffer"): "metal_fx::TemporalScaler::encode",
    ("MTLFX::TemporalScalerBase", "colorTextureUsage"): "metal_fx::TemporalScaler::color_texture_usage",
    ("MTLFX::TemporalScalerBase", "depthTextureUsage"): "metal_fx::TemporalScaler::depth_texture_usage",
    ("MTLFX::TemporalScalerBase", "motionTextureUsage"): "metal_fx::TemporalScaler::motion_texture_usage",
    ("MTLFX::TemporalScalerBase", "outputTextureUsage"): "metal_fx::TemporalScaler::output_texture_usage",
    ("MTLFX::TemporalScalerBase", "setInputContentWidth"): "metal_fx::TemporalScaler::set_input_content_size",
    ("MTLFX::TemporalScalerBase", "setInputContentHeight"): "metal_fx::TemporalScaler::set_input_content_size",
    ("MTLFX::TemporalScalerBase", "setColorTexture"): "metal_fx::TemporalScaler::set_textures",
    ("MTLFX::TemporalScalerBase", "setDepthTexture"): "metal_fx::TemporalScaler::set_textures",
    ("MTLFX::TemporalScalerBase", "setMotionTexture"): "metal_fx::TemporalScaler::set_textures",
    ("MTLFX::TemporalScalerBase", "setOutputTexture"): "metal_fx::TemporalScaler::set_textures",
    ("CA::MetalLayer", "layer"): "quartz_core::Layer::new",
    ("CA::MetalLayer", "device"): "quartz_core::Layer::device",
    ("CA::MetalLayer", "setDevice"): "quartz_core::Layer::set_device",
    ("CA::MetalLayer", "pixelFormat"): "quartz_core::Layer::pixel_format",
    ("CA::MetalLayer", "setPixelFormat"): "quartz_core::Layer::set_pixel_format",
    ("CA::MetalLayer", "framebufferOnly"): "quartz_core::Layer::framebuffer_only",
    ("CA::MetalLayer", "setFramebufferOnly"): "quartz_core::Layer::set_framebuffer_only",
    ("CA::MetalLayer", "drawableSize"): "quartz_core::Layer::drawable_size",
    ("CA::MetalLayer", "setDrawableSize"): "quartz_core::Layer::set_drawable_size",
    ("CA::MetalLayer", "maximumDrawableCount"): "quartz_core::Layer::maximum_drawable_count",
    ("CA::MetalLayer", "setMaximumDrawableCount"): "quartz_core::Layer::set_maximum_drawable_count",
    ("CA::MetalLayer", "displaySyncEnabled"): "quartz_core::Layer::display_sync_enabled",
    ("CA::MetalLayer", "setDisplaySyncEnabled"): "quartz_core::Layer::set_display_sync_enabled",
    ("CA::MetalLayer", "colorspace"): "quartz_core::Layer::color_space",
    ("CA::MetalLayer", "setColorspace"): "quartz_core::Layer::set_color_space",
    ("CA::MetalLayer", "allowsNextDrawableTimeout"): "quartz_core::Layer::allows_next_drawable_timeout",
    ("CA::MetalLayer", "setAllowsNextDrawableTimeout"): "quartz_core::Layer::set_allows_next_drawable_timeout",
    ("CA::MetalLayer", "wantsExtendedDynamicRangeContent"): "quartz_core::Layer::wants_extended_dynamic_range_content",
    ("CA::MetalLayer", "setWantsExtendedDynamicRangeContent"): "quartz_core::Layer::set_wants_extended_dynamic_range_content",
    ("CA::MetalLayer", "residencySet"): "quartz_core::Layer::residency_set",
    ("CA::MetalLayer", "nextDrawable"): "quartz_core::Layer::next_drawable",
    ("CA::MetalDrawable", "texture"): "quartz_core::Drawable::texture",
    ("MTL::CommandBuffer", "addCompletedHandler"): "metal::CommandBuffer::on_complete",
    ("MTL::CommandBuffer", "addScheduledHandler"): "metal::CommandBuffer::on_scheduled",
    ("MTL::CommandBuffer", "device"): "metal::CommandBuffer::device",
    ("MTL::CommandBuffer", "commandQueue"): "metal::CommandBuffer::command_queue",
    ("MTL::CommandBuffer", "label"): "metal::CommandBuffer::label",
    ("MTL::CommandBuffer", "setLabel"): "metal::CommandBuffer::set_label",
    ("MTL::CommandBuffer", "retainedReferences"): "metal::CommandBuffer::retained_references",
    ("MTL::CommandBuffer", "pushDebugGroup"): "metal::CommandBuffer::push_debug_group",
    ("MTL::CommandBuffer", "popDebugGroup"): "metal::CommandBuffer::pop_debug_group",
    ("MTL::CommandBuffer", "presentDrawableAtTime"): "metal::CommandBuffer::present_drawable_at_time",
    ("MTL::CommandBuffer", "presentDrawableAfterMinimumDuration"): "metal::CommandBuffer::present_drawable_after_minimum_duration",
    ("MTL::CommandBuffer", "GPUStartTime"): "metal::CommandBuffer::gpu_start_time",
    ("MTL::CommandBuffer", "GPUEndTime"): "metal::CommandBuffer::gpu_end_time",
    ("MTL::CommandBuffer", "kernelStartTime"): "metal::CommandBuffer::kernel_start_time",
    ("MTL::CommandBuffer", "kernelEndTime"): "metal::CommandBuffer::kernel_end_time",
    ("MTL::Texture", "getBytes"): "metal::BlitCommandEncoder::read_texture",
    ("MTL::TextureDescriptor", "alloc"): "metal::TextureDescriptor::new",
    ("MTL::TextureDescriptor", "init"): "metal::TextureDescriptor::new",
    ("MTL::TextureDescriptor", "width"): "metal::TextureDescriptor::dimensions",
    ("MTL::TextureDescriptor", "height"): "metal::TextureDescriptor::dimensions",
    ("MTL::TextureDescriptor", "depth"): "metal::TextureDescriptor::dimensions",
    ("MTL::TextureDescriptor", "setWidth"): "metal::TextureDescriptor::set_dimensions",
    ("MTL::TextureDescriptor", "setHeight"): "metal::TextureDescriptor::set_dimensions",
    ("MTL::TextureDescriptor", "setDepth"): "metal::TextureDescriptor::set_dimensions",
    ("MTL::TextureDescriptor", "arrayLength"): "metal::TextureDescriptor::array_length",
    ("MTL::TextureDescriptor", "setArrayLength"): "metal::TextureDescriptor::set_array_length",
    ("MTL::TextureDescriptor", "sampleCount"): "metal::TextureDescriptor::sample_count",
    ("MTL::TextureDescriptor", "setSampleCount"): "metal::TextureDescriptor::set_sample_count",
    ("MTL::TextureDescriptor", "mipmapLevelCount"): "metal::TextureDescriptor::mipmap_level_count",
    ("MTL::TextureDescriptor", "setMipmapLevelCount"): "metal::TextureDescriptor::set_mipmap_level_count",
    ("MTL::TextureDescriptor", "pixelFormat"): "metal::TextureDescriptor::pixel_format",
    ("MTL::TextureDescriptor", "setPixelFormat"): "metal::TextureDescriptor::set_pixel_format",
    ("MTL::TextureDescriptor", "textureType"): "metal::TextureDescriptor::texture_type",
    ("MTL::TextureDescriptor", "setTextureType"): "metal::TextureDescriptor::set_texture_type",
    ("MTL::TextureDescriptor", "resourceOptions"): "metal::TextureDescriptor::resource_options",
    ("MTL::TextureDescriptor", "setResourceOptions"): "metal::TextureDescriptor::set_resource_options",
    ("MTL::TextureDescriptor", "usage"): "metal::TextureDescriptor::usage",
    ("MTL::TextureDescriptor", "setUsage"): "metal::TextureDescriptor::set_usage",
    ("MTL::TextureDescriptor", "storageMode"): "metal::TextureDescriptor::storage_mode",
    ("MTL::TextureDescriptor", "setStorageMode"): "metal::TextureDescriptor::set_storage_mode",
    ("MTL::TextureDescriptor", "cpuCacheMode"): "metal::TextureDescriptor::cpu_cache_mode",
    ("MTL::TextureDescriptor", "setCpuCacheMode"): "metal::TextureDescriptor::set_cpu_cache_mode",
    ("MTL::TextureDescriptor", "hazardTrackingMode"): "metal::TextureDescriptor::hazard_tracking_mode",
    ("MTL::TextureDescriptor", "setHazardTrackingMode"): "metal::TextureDescriptor::set_hazard_tracking_mode",
    ("MTL::TextureDescriptor", "compressionType"): "metal::TextureDescriptor::compression_type",
    ("MTL::TextureDescriptor", "setCompressionType"): "metal::TextureDescriptor::set_compression_type",
    ("MTL::TextureDescriptor", "placementSparsePageSize"): "metal::TextureDescriptor::placement_sparse_page_size",
    ("MTL::TextureDescriptor", "setPlacementSparsePageSize"): "metal::TextureDescriptor::set_placement_sparse_page_size",
    ("MTL::TextureDescriptor", "allowGPUOptimizedContents"): "metal::TextureDescriptor::allows_gpu_optimized_contents",
    ("MTL::TextureDescriptor", "setAllowGPUOptimizedContents"): "metal::TextureDescriptor::set_allows_gpu_optimized_contents",
    ("MTL::Texture", "depth"): "metal::Texture::layout",
    ("MTL::Texture", "arrayLength"): "metal::Texture::layout",
    ("MTL::Texture", "mipmapLevelCount"): "metal::Texture::layout",
    ("MTL::Texture", "sampleCount"): "metal::Texture::layout",
    ("MTL::Texture", "textureType"): "metal::Texture::texture_type",
    ("MTL::Texture", "usage"): "metal::Texture::usage",
    ("MTL::Texture", "isFramebufferOnly"): "metal::Texture::is_framebuffer_only",
    ("MTL::Texture", "isShareable"): "metal::Texture::is_shareable",
    ("MTL::Texture", "isSparse"): "metal::Texture::is_sparse",
    ("MTL::Texture", "allowGPUOptimizedContents"): "metal::Texture::allows_gpu_optimized_contents",
    ("MTL::Texture", "compressionType"): "metal::Texture::compression_type",
    ("MTL::Texture", "sparseTextureTier"): "metal::Texture::sparse_texture_tier",
    ("MTL::Texture", "parentTexture"): "metal::Texture::parent_texture",
    ("MTL::Texture", "parentRelativeLevel"): "metal::Texture::parent_relative_location",
    ("MTL::Texture", "parentRelativeSlice"): "metal::Texture::parent_relative_location",
    ("MTL::Texture", "buffer"): "metal::Texture::buffer",
    ("MTL::Texture", "bufferOffset"): "metal::Texture::buffer_layout",
    ("MTL::Texture", "bufferBytesPerRow"): "metal::Texture::buffer_layout",
    ("MTL::Texture", "firstMipmapInTail"): "metal::Texture::sparse_tail",
    ("MTL::Texture", "tailSizeInBytes"): "metal::Texture::sparse_tail",
    ("MTL::Device", "areBarycentricCoordsSupported"): "metal::Device::capability",
    ("MTL::Device", "areProgrammableSamplePositionsSupported"): "metal::Device::capability",
    ("MTL::Device", "areRasterOrderGroupsSupported"): "metal::Device::capability",
    ("MTL::Device", "hasUnifiedMemory"): "metal::Device::capability",
    ("MTL::Device", "isDepth24Stencil8PixelFormatSupported"): "metal::Device::capability",
    ("MTL::Device", "isHeadless"): "metal::Device::capability",
    ("MTL::Device", "isLowPower"): "metal::Device::capability",
    ("MTL::Device", "isRemovable"): "metal::Device::capability",
    ("MTL::Device", "supports32BitFloatFiltering"): "metal::Device::capability",
    ("MTL::Device", "supports32BitMSAA"): "metal::Device::capability",
    ("MTL::Device", "supportsBCTextureCompression"): "metal::Device::capability",
    ("MTL::Device", "supportsDynamicLibraries"): "metal::Device::capability",
    ("MTL::Device", "supportsFunctionPointers"): "metal::Device::capability",
    ("MTL::Device", "supportsFunctionPointersFromRender"): "metal::Device::capability",
    ("MTL::Device", "supportsPlacementSparse"): "metal::Device::capability",
    ("MTL::Device", "supportsPrimitiveMotionBlur"): "metal::Device::capability",
    ("MTL::Device", "supportsPullModelInterpolation"): "metal::Device::capability",
    ("MTL::Device", "supportsQueryTextureLOD"): "metal::Device::capability",
    ("MTL::Device", "supportsRaytracing"): "metal::Device::capability",
    ("MTL::Device", "supportsRaytracingFromRender"): "metal::Device::capability",
    ("MTL::Device", "supportsRenderDynamicLibraries"): "metal::Device::capability",
    ("MTL::Device", "supportsShaderBarycentricCoordinates"): "metal::Device::capability",
    ("MTL::Device", "currentAllocatedSize"): "metal::Device::numeric_property",
    ("MTL::Device", "locationNumber"): "metal::Device::numeric_property",
    ("MTL::Device", "maxArgumentBufferSamplerCount"): "metal::Device::numeric_property",
    ("MTL::Device", "maxBufferLength"): "metal::Device::numeric_property",
    ("MTL::Device", "maxThreadgroupMemoryLength"): "metal::Device::numeric_property",
    ("MTL::Device", "maxTransferRate"): "metal::Device::numeric_property",
    ("MTL::Device", "maximumConcurrentCompilationTaskCount"): "metal::Device::numeric_property",
    ("MTL::Device", "peerCount"): "metal::Device::numeric_property",
    ("MTL::Device", "peerGroupID"): "metal::Device::numeric_property",
    ("MTL::Device", "peerIndex"): "metal::Device::numeric_property",
    ("MTL::Device", "recommendedMaxWorkingSetSize"): "metal::Device::numeric_property",
    ("MTL::Device", "registryID"): "metal::Device::numeric_property",
    ("MTL::Device", "sparseTileSizeInBytes"): "metal::Device::numeric_property",
    ("MTL::Device", "queryTimestampFrequency"): "metal::Device::numeric_property",
    ("MTL::Device", "maxThreadsPerThreadgroup"): "metal::Device::max_threads_per_threadgroup",
    ("MTL::Device", "minimumLinearTextureAlignmentForPixelFormat"): "metal::Device::texture_alignments",
    ("MTL::Device", "minimumTextureBufferAlignmentForPixelFormat"): "metal::Device::texture_alignments",
    ("MTL::Device", "sampleTimestamps"): "metal::Device::sample_timestamps",
    ("MTL::Device", "location"): "metal::Device::location",
    ("MTL::Device", "argumentBuffersSupport"): "metal::Device::argument_buffers_tier",
    ("MTL::Device", "readWriteTextureSupport"): "metal::Device::read_write_texture_tier",
    ("MTL::Device", "supportsFamily"): "metal::Device::supports_family",
    ("MTL::Device", "supportsFeatureSet"): "metal::Device::supports_feature_set",
    ("MTL::Device", "supportsCounterSampling"): "metal::Device::supports_counter_sampling",
    ("MTL::Device", "supportsRasterizationRateMap"): "metal::Device::supports_rasterization_rate_map",
    ("MTL::Device", "supportsVertexAmplificationCount"): "metal::Device::supports_vertex_amplification_count",
    ("MTL::Device", "shouldMaximizeConcurrentCompilation"): "metal::Device::should_maximize_concurrent_compilation",
    ("MTL::Device", "setShouldMaximizeConcurrentCompilation"): "metal::Device::set_should_maximize_concurrent_compilation",
    ("MTL::Device", "getDefaultSamplePositions"): "metal::Device::default_sample_positions",
    ("MTL::Device", "heapBufferSizeAndAlign"): "metal::Device::heap_buffer_size_and_align",
    ("MTL::Device", "sparseTileSize"): "metal::Device::sparse_tile_size",
    ("MTL::Buffer", "addDebugMarker"): "metal::Buffer::add_debug_marker",
    ("MTL::Buffer", "removeAllDebugMarkers"): "metal::Buffer::remove_all_debug_markers",
    ("MTL::Buffer", "gpuAddress"): "metal::Buffer::gpu_address",
    ("MTL::Buffer", "sparseBufferTier"): "metal::Buffer::sparse_buffer_tier",
    ("MTL::Buffer", "remoteStorageBuffer"): "metal::Buffer::remote_storage_buffer",
    ("MTL::Buffer", "newRemoteBufferViewForDevice"): "metal::Buffer::new_remote_view",
    ("MTL::Buffer", "newTexture"): "metal::Buffer::new_texture",
    ("MTL::CommandQueue", "device"): "metal::CommandQueue::device",
    ("MTL::CommandQueue", "insertDebugCaptureBoundary"): "metal::CommandQueue::insert_debug_capture_boundary",
    ("MTL::CommandQueue", "addResidencySet"): "metal::CommandQueue::add_residency_sets",
    ("MTL::CommandQueue", "addResidencySets"): "metal::CommandQueue::add_residency_sets",
    ("MTL::CommandQueue", "removeResidencySet"): "metal::CommandQueue::remove_residency_sets",
    ("MTL::CommandQueue", "removeResidencySets"): "metal::CommandQueue::remove_residency_sets",
    ("MTL::CommandQueue", "commandBufferWithUnretainedReferences"): "metal::CommandQueue::command_buffer",
    ("MTL::CompileOptions", "alloc"): "metal::CompileOptions::new",
    ("MTL::CompileOptions", "init"): "metal::CompileOptions::new",
    ("MTL::CompileOptions", "fastMathEnabled"): "metal::CompileOptions::fast_math_enabled",
    ("MTL::CompileOptions", "setFastMathEnabled"): "metal::CompileOptions::set_fast_math_enabled",
    ("MTL::CompileOptions", "allowReferencingUndefinedSymbols"): "metal::CompileOptions::allows_referencing_undefined_symbols",
    ("MTL::CompileOptions", "setAllowReferencingUndefinedSymbols"): "metal::CompileOptions::set_allows_referencing_undefined_symbols",
    ("MTL::CompileOptions", "enableLogging"): "metal::CompileOptions::logging_enabled",
    ("MTL::CompileOptions", "setEnableLogging"): "metal::CompileOptions::set_logging_enabled",
    ("MTL::CompileOptions", "preserveInvariance"): "metal::CompileOptions::preserves_invariance",
    ("MTL::CompileOptions", "setPreserveInvariance"): "metal::CompileOptions::set_preserves_invariance",
    ("MTL::CompileOptions", "installName"): "metal::CompileOptions::install_name",
    ("MTL::CompileOptions", "setInstallName"): "metal::CompileOptions::set_install_name",
    ("MTL::CompileOptions", "maxTotalThreadsPerThreadgroup"): "metal::CompileOptions::max_total_threads_per_threadgroup",
    ("MTL::CompileOptions", "setMaxTotalThreadsPerThreadgroup"): "metal::CompileOptions::set_max_total_threads_per_threadgroup",
    ("MTL::CompileOptions", "requiredThreadsPerThreadgroup"): "metal::CompileOptions::required_threads_per_threadgroup",
    ("MTL::CompileOptions", "setRequiredThreadsPerThreadgroup"): "metal::CompileOptions::set_required_threads_per_threadgroup",
    ("MTL::CompileOptions", "mathMode"): "metal::CompileOptions::math_mode",
    ("MTL::CompileOptions", "setMathMode"): "metal::CompileOptions::set_math_mode",
    ("MTL::CompileOptions", "mathFloatingPointFunctions"): "metal::CompileOptions::math_floating_point_functions",
    ("MTL::CompileOptions", "setMathFloatingPointFunctions"): "metal::CompileOptions::set_math_floating_point_functions",
    ("MTL::CompileOptions", "languageVersion"): "metal::CompileOptions::language_version",
    ("MTL::CompileOptions", "setLanguageVersion"): "metal::CompileOptions::set_language_version",
    ("MTL::CompileOptions", "libraryType"): "metal::CompileOptions::library_type",
    ("MTL::CompileOptions", "setLibraryType"): "metal::CompileOptions::set_library_type",
    ("MTL::CompileOptions", "optimizationLevel"): "metal::CompileOptions::optimization_level",
    ("MTL::CompileOptions", "setOptimizationLevel"): "metal::CompileOptions::set_optimization_level",
    ("MTL::CompileOptions", "compileSymbolVisibility"): "metal::CompileOptions::compile_symbol_visibility",
    ("MTL::CompileOptions", "setCompileSymbolVisibility"): "metal::CompileOptions::set_compile_symbol_visibility",
    ("MTL::RenderPipelineDescriptor", "alloc"): "metal::RenderPipelineDescriptor::empty",
    ("MTL::RenderPipelineDescriptor", "init"): "metal::RenderPipelineDescriptor::empty",
    ("MTL::RenderPipelineDescriptor", "label"): "metal::RenderPipelineDescriptor::label",
    ("MTL::RenderPipelineDescriptor", "setLabel"): "metal::RenderPipelineDescriptor::set_label",
    ("MTL::RenderPipelineDescriptor", "vertexFunction"): "metal::RenderPipelineDescriptor::vertex_function",
    ("MTL::RenderPipelineDescriptor", "setVertexFunction"): "metal::RenderPipelineDescriptor::set_vertex_function",
    ("MTL::RenderPipelineDescriptor", "fragmentFunction"): "metal::RenderPipelineDescriptor::fragment_function",
    ("MTL::RenderPipelineDescriptor", "setFragmentFunction"): "metal::RenderPipelineDescriptor::set_fragment_function",
    ("MTL::RenderPipelineDescriptor", "reset"): "metal::RenderPipelineDescriptor::reset",
    ("MTL::RenderPipelineDescriptor", "inputPrimitiveTopology"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "isAlphaToCoverageEnabled"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "isAlphaToOneEnabled"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "isRasterizationEnabled"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "isTessellationFactorScaleEnabled"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "depthAttachmentPixelFormat"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "stencilAttachmentPixelFormat"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "maxFragmentCallStackDepth"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "maxTessellationFactor"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "maxVertexAmplificationCount"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "maxVertexCallStackDepth"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "rasterSampleCount"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "sampleCount"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "shaderValidation"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "supportAddingFragmentBinaryFunctions"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "supportAddingVertexBinaryFunctions"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "supportIndirectCommandBuffers"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "tessellationControlPointIndexType"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "tessellationFactorFormat"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "tessellationFactorStepFunction"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "tessellationOutputWindingOrder"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "tessellationPartitionMode"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "setInputPrimitiveTopology"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setAlphaToCoverageEnabled"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setAlphaToOneEnabled"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setRasterizationEnabled"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setTessellationFactorScaleEnabled"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setDepthAttachmentPixelFormat"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setStencilAttachmentPixelFormat"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setMaxFragmentCallStackDepth"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setMaxTessellationFactor"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setMaxVertexAmplificationCount"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setMaxVertexCallStackDepth"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setRasterSampleCount"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setSampleCount"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setShaderValidation"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setSupportAddingFragmentBinaryFunctions"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setSupportAddingVertexBinaryFunctions"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setSupportIndirectCommandBuffers"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setTessellationControlPointIndexType"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setTessellationFactorFormat"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setTessellationFactorStepFunction"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setTessellationOutputWindingOrder"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPipelineDescriptor", "setTessellationPartitionMode"): "metal::RenderPipelineDescriptor::set_options",
    ("MTL::RenderPassDescriptor", "alloc"): "metal::RenderPassDescriptor::new",
    ("MTL::RenderPassDescriptor", "init"): "metal::RenderPassDescriptor::new",
    ("MTL::RenderPassDescriptor", "renderPassDescriptor"): "metal::RenderPassDescriptor::new",
    ("MTL::RenderPassDescriptor", "defaultRasterSampleCount"): "metal::RenderPassDescriptor::options",
    ("MTL::RenderPassDescriptor", "imageblockSampleLength"): "metal::RenderPassDescriptor::options",
    ("MTL::RenderPassDescriptor", "renderTargetArrayLength"): "metal::RenderPassDescriptor::options",
    ("MTL::RenderPassDescriptor", "renderTargetHeight"): "metal::RenderPassDescriptor::options",
    ("MTL::RenderPassDescriptor", "renderTargetWidth"): "metal::RenderPassDescriptor::options",
    ("MTL::RenderPassDescriptor", "supportColorAttachmentMapping"): "metal::RenderPassDescriptor::options",
    ("MTL::RenderPassDescriptor", "threadgroupMemoryLength"): "metal::RenderPassDescriptor::options",
    ("MTL::RenderPassDescriptor", "tileHeight"): "metal::RenderPassDescriptor::options",
    ("MTL::RenderPassDescriptor", "tileWidth"): "metal::RenderPassDescriptor::options",
    ("MTL::RenderPassDescriptor", "visibilityResultType"): "metal::RenderPassDescriptor::options",
    ("MTL::RenderPassDescriptor", "setDefaultRasterSampleCount"): "metal::RenderPassDescriptor::set_options",
    ("MTL::RenderPassDescriptor", "setImageblockSampleLength"): "metal::RenderPassDescriptor::set_options",
    ("MTL::RenderPassDescriptor", "setRenderTargetArrayLength"): "metal::RenderPassDescriptor::set_options",
    ("MTL::RenderPassDescriptor", "setRenderTargetHeight"): "metal::RenderPassDescriptor::set_options",
    ("MTL::RenderPassDescriptor", "setRenderTargetWidth"): "metal::RenderPassDescriptor::set_options",
    ("MTL::RenderPassDescriptor", "setSupportColorAttachmentMapping"): "metal::RenderPassDescriptor::set_options",
    ("MTL::RenderPassDescriptor", "setThreadgroupMemoryLength"): "metal::RenderPassDescriptor::set_options",
    ("MTL::RenderPassDescriptor", "setTileHeight"): "metal::RenderPassDescriptor::set_options",
    ("MTL::RenderPassDescriptor", "setTileWidth"): "metal::RenderPassDescriptor::set_options",
    ("MTL::RenderPassDescriptor", "setVisibilityResultType"): "metal::RenderPassDescriptor::set_options",
    ("MTL::RenderPassDescriptor", "getSamplePositions"): "metal::RenderPassDescriptor::sample_positions",
    ("MTL::RenderPassDescriptor", "setSamplePositions"): "metal::RenderPassDescriptor::set_sample_positions",
    ("MTL::RenderPassDescriptor", "visibilityResultBuffer"): "metal::RenderPassDescriptor::visibility_result_buffer",
    ("MTL::RenderPassDescriptor", "setVisibilityResultBuffer"): "metal::RenderPassDescriptor::set_visibility_result_buffer",
    ("MTL::RenderCommandEncoder", "setRenderPipelineState"): "metal::RenderCommandEncoder::set_pipeline",
    ("MTL::RenderCommandEncoder", "setViewport"): "metal::RenderCommandEncoder::set_viewport",
    ("MTL::RenderCommandEncoder", "setFragmentBytes"): "metal::RenderCommandEncoder::set_fragment_bytes",
    ("MTL::RenderCommandEncoder", "setFragmentBuffer"): "metal::RenderCommandEncoder::set_fragment_buffer",
    ("MTL::RenderCommandEncoder", "setVertexTexture"): "metal::RenderCommandEncoder::set_vertex_texture",
    ("MTL::RenderCommandEncoder", "setFragmentTexture"): "metal::RenderCommandEncoder::set_fragment_texture",
    ("MTL::RenderCommandEncoder", "setBlendColor"): "metal::RenderCommandEncoder::set_blend_color",
    ("MTL::RenderCommandEncoder", "setCullMode"): "metal::RenderCommandEncoder::set_cull_mode",
    ("MTL::RenderCommandEncoder", "setFrontFacingWinding"): "metal::RenderCommandEncoder::set_front_facing_winding",
    ("MTL::RenderCommandEncoder", "setTriangleFillMode"): "metal::RenderCommandEncoder::set_triangle_fill_mode",
    ("MTL::RenderCommandEncoder", "setDepthBias"): "metal::RenderCommandEncoder::set_depth_bias",
    ("MTL::RenderCommandEncoder", "setDepthClipMode"): "metal::RenderCommandEncoder::set_depth_clip_mode",
    ("MTL::RenderCommandEncoder", "setDepthTestBounds"): "metal::RenderCommandEncoder::set_depth_test_bounds",
    ("MTL::RenderCommandEncoder", "setStencilReferenceValue"): "metal::RenderCommandEncoder::set_stencil_reference_value",
    ("MTL::RenderCommandEncoder", "setStencilReferenceValues"): "metal::RenderCommandEncoder::set_stencil_reference_values",
    ("MTL::RenderCommandEncoder", "setScissorRect"): "metal::RenderCommandEncoder::set_scissor_rect",
    ("MTL::RenderCommandEncoder", "tileWidth"): "metal::RenderCommandEncoder::tile_size",
    ("MTL::RenderCommandEncoder", "tileHeight"): "metal::RenderCommandEncoder::tile_size",
    ("MTL::RenderCommandEncoder", "textureBarrier"): "metal::RenderCommandEncoder::texture_barrier",
    ("MTL::ComputeCommandEncoder", "setComputePipelineState"): "metal::ComputeCommandEncoder::set_pipeline",
    ("MTL::ComputeCommandEncoder", "dispatchThreads"): "metal::ComputeCommandEncoder::dispatch_threads",
    ("MTL::BlitCommandEncoder", "fillBuffer"): "metal::BlitCommandEncoder::fill_buffer",
    ("MTL::BlitCommandEncoder", "generateMipmaps"): "metal::BlitCommandEncoder::generate_mipmaps",
    ("MTL::BlitCommandEncoder", "synchronizeTexture"): "metal::BlitCommandEncoder::synchronize_texture",
    ("MTL::CommandEncoder", "device"): "metal::RenderCommandEncoder::device",
    ("MTL::CommandEncoder", "insertDebugSignpost"): "metal::RenderCommandEncoder::insert_debug_signpost",
    ("MTL::CommandEncoder", "pushDebugGroup"): "metal::RenderCommandEncoder::push_debug_group",
    ("MTL::CommandEncoder", "popDebugGroup"): "metal::RenderCommandEncoder::pop_debug_group",
    ("MTL::CommandEncoder", "endEncoding"): "metal::RenderCommandEncoder::end_encoding",
    ("MTL::Library", "device"): "metal::Library::device",
    ("MTL::Library", "installName"): "metal::Library::install_name",
    ("MTL::Library", "label"): "metal::Library::label",
    ("MTL::Library", "setLabel"): "metal::Library::set_label",
    ("MTL::Library", "type"): "metal::Library::library_type",
    ("MTL::Function", "device"): "metal::Function::device",
    ("MTL::Function", "label"): "metal::Function::label",
    ("MTL::Function", "setLabel"): "metal::Function::set_label",
    ("MTL::Function", "functionType"): "metal::Function::function_type",
    ("MTL::Function", "options"): "metal::Function::options",
    ("MTL::Function", "patchControlPointCount"): "metal::Function::patch_control_point_count",
    ("MTL::Function", "patchType"): "metal::Function::patch_type",
    ("MTL::RenderPipelineState", "device"): "metal::RenderPipelineState::device",
    ("MTL::RenderPipelineState", "label"): "metal::RenderPipelineState::label",
    ("MTL::RenderPipelineState", "supportIndirectCommandBuffers"): "metal::RenderPipelineState::supports_indirect_command_buffers",
    ("MTL::RenderPipelineState", "threadgroupSizeMatchesTileSize"): "metal::RenderPipelineState::threadgroup_size_matches_tile_size",
    ("MTL::RenderPipelineState", "imageblockSampleLength"): "metal::RenderPipelineState::imageblock_sample_length",
    ("MTL::RenderPipelineState", "shaderValidation"): "metal::RenderPipelineState::shader_validation",
    ("MTL::RenderPipelineState", "requiredThreadsPerTileThreadgroup"): "metal::RenderPipelineState::required_threadgroups",
    ("MTL::RenderPipelineState", "requiredThreadsPerMeshThreadgroup"): "metal::RenderPipelineState::required_threadgroups",
    ("MTL::RenderPipelineState", "requiredThreadsPerObjectThreadgroup"): "metal::RenderPipelineState::required_threadgroups",
    ("MTL::ComputePipelineState", "device"): "metal::ComputePipelineState::device",
    ("MTL::ComputePipelineState", "label"): "metal::ComputePipelineState::label",
    ("MTL::ComputePipelineState", "supportIndirectCommandBuffers"): "metal::ComputePipelineState::supports_indirect_command_buffers",
    ("MTL::ComputePipelineState", "staticThreadgroupMemoryLength"): "metal::ComputePipelineState::static_threadgroup_memory_length",
    ("MTL::ComputePipelineState", "requiredThreadsPerThreadgroup"): "metal::ComputePipelineState::required_threads_per_threadgroup",
    ("MTL::ComputePipelineState", "shaderValidation"): "metal::ComputePipelineState::shader_validation",
    ("MTLFX::SpatialScalerDescriptor", "colorTextureFormat"): "metal_fx::SpatialScalerDescriptor::color_texture_format",
    ("MTLFX::SpatialScalerDescriptor", "setColorTextureFormat"): "metal_fx::SpatialScalerDescriptor::set_color_texture_format",
    ("MTLFX::SpatialScalerDescriptor", "outputTextureFormat"): "metal_fx::SpatialScalerDescriptor::output_texture_format",
    ("MTLFX::SpatialScalerDescriptor", "setOutputTextureFormat"): "metal_fx::SpatialScalerDescriptor::set_output_texture_format",
    ("MTLFX::SpatialScalerDescriptor", "inputWidth"): "metal_fx::SpatialScalerDescriptor::input_size",
    ("MTLFX::SpatialScalerDescriptor", "inputHeight"): "metal_fx::SpatialScalerDescriptor::input_size",
    ("MTLFX::SpatialScalerDescriptor", "setInputWidth"): "metal_fx::SpatialScalerDescriptor::set_input_size",
    ("MTLFX::SpatialScalerDescriptor", "setInputHeight"): "metal_fx::SpatialScalerDescriptor::set_input_size",
    ("MTLFX::SpatialScalerDescriptor", "outputWidth"): "metal_fx::SpatialScalerDescriptor::output_size",
    ("MTLFX::SpatialScalerDescriptor", "outputHeight"): "metal_fx::SpatialScalerDescriptor::output_size",
    ("MTLFX::SpatialScalerDescriptor", "setOutputWidth"): "metal_fx::SpatialScalerDescriptor::set_output_size",
    ("MTLFX::SpatialScalerDescriptor", "setOutputHeight"): "metal_fx::SpatialScalerDescriptor::set_output_size",
    ("MTLFX::SpatialScalerDescriptor", "colorProcessingMode"): "metal_fx::SpatialScalerDescriptor::color_processing_mode",
    ("MTLFX::SpatialScalerDescriptor", "setColorProcessingMode"): "metal_fx::SpatialScalerDescriptor::set_color_processing_mode",
    ("MTLFX::SpatialScalerDescriptor", "supportsMetal4FX"): "metal_fx::SpatialScalerDescriptor::supports_metal4_fx",
    ("MTLFX::SpatialScalerBase", "colorTexture"): "metal_fx::SpatialScaler::color_texture",
    ("MTLFX::SpatialScalerBase", "outputTexture"): "metal_fx::SpatialScaler::output_texture",
    ("MTLFX::SpatialScalerBase", "colorProcessingMode"): "metal_fx::SpatialScaler::color_processing_mode",
    ("MTLFX::TemporalScalerDescriptor", "colorTextureFormat"): "metal_fx::TemporalScalerDescriptor::texture_formats",
    ("MTLFX::TemporalScalerDescriptor", "depthTextureFormat"): "metal_fx::TemporalScalerDescriptor::texture_formats",
    ("MTLFX::TemporalScalerDescriptor", "motionTextureFormat"): "metal_fx::TemporalScalerDescriptor::texture_formats",
    ("MTLFX::TemporalScalerDescriptor", "outputTextureFormat"): "metal_fx::TemporalScalerDescriptor::texture_formats",
    ("MTLFX::TemporalScalerDescriptor", "setColorTextureFormat"): "metal_fx::TemporalScalerDescriptor::set_texture_formats",
    ("MTLFX::TemporalScalerDescriptor", "setDepthTextureFormat"): "metal_fx::TemporalScalerDescriptor::set_texture_formats",
    ("MTLFX::TemporalScalerDescriptor", "setMotionTextureFormat"): "metal_fx::TemporalScalerDescriptor::set_texture_formats",
    ("MTLFX::TemporalScalerDescriptor", "setOutputTextureFormat"): "metal_fx::TemporalScalerDescriptor::set_texture_formats",
    ("MTLFX::TemporalScalerDescriptor", "inputWidth"): "metal_fx::TemporalScalerDescriptor::input_size",
    ("MTLFX::TemporalScalerDescriptor", "inputHeight"): "metal_fx::TemporalScalerDescriptor::input_size",
    ("MTLFX::TemporalScalerDescriptor", "setInputWidth"): "metal_fx::TemporalScalerDescriptor::set_input_size",
    ("MTLFX::TemporalScalerDescriptor", "setInputHeight"): "metal_fx::TemporalScalerDescriptor::set_input_size",
    ("MTLFX::TemporalScalerDescriptor", "outputWidth"): "metal_fx::TemporalScalerDescriptor::output_size",
    ("MTLFX::TemporalScalerDescriptor", "outputHeight"): "metal_fx::TemporalScalerDescriptor::output_size",
    ("MTLFX::TemporalScalerDescriptor", "setOutputWidth"): "metal_fx::TemporalScalerDescriptor::set_output_size",
    ("MTLFX::TemporalScalerDescriptor", "setOutputHeight"): "metal_fx::TemporalScalerDescriptor::set_output_size",
    ("MTLFX::TemporalScalerDescriptor", "isAutoExposureEnabled"): "metal_fx::TemporalScalerDescriptor::auto_exposure_enabled",
    ("MTLFX::TemporalScalerDescriptor", "setAutoExposureEnabled"): "metal_fx::TemporalScalerDescriptor::set_auto_exposure_enabled",
    ("MTLFX::TemporalScalerDescriptor", "isInputContentPropertiesEnabled"): "metal_fx::TemporalScalerDescriptor::input_content_properties_enabled",
    ("MTLFX::TemporalScalerDescriptor", "setInputContentPropertiesEnabled"): "metal_fx::TemporalScalerDescriptor::set_input_content_properties_enabled",
    ("MTLFX::TemporalScalerDescriptor", "requiresSynchronousInitialization"): "metal_fx::TemporalScalerDescriptor::requires_synchronous_initialization",
    ("MTLFX::TemporalScalerDescriptor", "setRequiresSynchronousInitialization"): "metal_fx::TemporalScalerDescriptor::set_requires_synchronous_initialization",
    ("MTLFX::TemporalScalerDescriptor", "isReactiveMaskTextureEnabled"): "metal_fx::TemporalScalerDescriptor::reactive_mask_texture_enabled",
    ("MTLFX::TemporalScalerDescriptor", "setReactiveMaskTextureEnabled"): "metal_fx::TemporalScalerDescriptor::set_reactive_mask_texture_enabled",
    ("MTLFX::TemporalScalerDescriptor", "reactiveMaskTextureFormat"): "metal_fx::TemporalScalerDescriptor::reactive_mask_texture_format",
    ("MTLFX::TemporalScalerDescriptor", "setReactiveMaskTextureFormat"): "metal_fx::TemporalScalerDescriptor::set_reactive_mask_texture_format",
    ("MTLFX::TemporalScalerDescriptor", "inputContentMinScale"): "metal_fx::TemporalScalerDescriptor::input_content_scale_range",
    ("MTLFX::TemporalScalerDescriptor", "inputContentMaxScale"): "metal_fx::TemporalScalerDescriptor::input_content_scale_range",
    ("MTLFX::TemporalScalerDescriptor", "setInputContentMinScale"): "metal_fx::TemporalScalerDescriptor::set_input_content_scale_range",
    ("MTLFX::TemporalScalerDescriptor", "setInputContentMaxScale"): "metal_fx::TemporalScalerDescriptor::set_input_content_scale_range",
    ("MTLFX::TemporalScalerDescriptor", "isOutputResolutionMotionVectorsEnabled"): "metal_fx::TemporalScalerDescriptor::output_resolution_motion_vectors_enabled",
    ("MTLFX::TemporalScalerDescriptor", "setOutputResolutionMotionVectorsEnabled"): "metal_fx::TemporalScalerDescriptor::set_output_resolution_motion_vectors_enabled",
    ("MTLFX::TemporalScalerDescriptor", "supportsMetal4FX"): "metal_fx::TemporalScalerDescriptor::supports_metal4_fx",
    ("MTLFX::TemporalScalerBase", "colorTexture"): "metal_fx::TemporalScaler::textures",
    ("MTLFX::TemporalScalerBase", "depthTexture"): "metal_fx::TemporalScaler::textures",
    ("MTLFX::TemporalScalerBase", "motionTexture"): "metal_fx::TemporalScaler::textures",
    ("MTLFX::TemporalScalerBase", "outputTexture"): "metal_fx::TemporalScaler::textures",
    ("MTLFX::TemporalScalerBase", "exposureTexture"): "metal_fx::TemporalScaler::exposure_texture",
    ("MTLFX::TemporalScalerBase", "setExposureTexture"): "metal_fx::TemporalScaler::set_exposure_texture",
    ("MTLFX::TemporalScalerBase", "reactiveMaskTexture"): "metal_fx::TemporalScaler::reactive_mask_texture",
    ("MTLFX::TemporalScalerBase", "setReactiveMaskTexture"): "metal_fx::TemporalScaler::set_reactive_mask_texture",
    ("MTLFX::TemporalScalerBase", "reactiveTextureUsage"): "metal_fx::TemporalScaler::reactive_texture_usage",
    ("MTLFX::TemporalScalerBase", "setDepthReversed"): "metal_fx::TemporalScaler::set_depth_reversed",
}

# Handwritten safe facade methods added by the vertical migration slices.  Only
# declarations whose parent/name pair is unique in the inventory belong here;
# overloaded APIs are recorded by their complete C++ signature below.
ACTUAL_METHODS.update(
    {
        ("MTL4::CommandBuffer", "writeTimestampIntoHeap"): "metal4::RecordingCommandBuffer::write_timestamp_into_heap",
        ("MTL4::MachineLearningCommandEncoder", "dispatchNetwork"): "metal4::RecordingMachineLearningEncoder::dispatch_network",
        ("MTL4::MachineLearningCommandEncoder", "setArgumentTable"): "metal4::RecordingMachineLearningEncoder::set_argument_table",
        ("MTL4::MachineLearningCommandEncoder", "setPipelineState"): "metal4::RecordingMachineLearningEncoder::set_pipeline_state",
        ("MTL::LinkedFunctions", "privateFunctions"): "metal::LinkedFunctions::internal_functions",
        ("MTL::LinkedFunctions", "setPrivateFunctions"): "metal::LinkedFunctions::set_internal_functions",
        ("MTL4::StaticLinkingDescriptor", "privateFunctionDescriptors"): "metal4::StaticLinkingDescriptor::internal_functions",
        ("MTL4::StaticLinkingDescriptor", "setPrivateFunctionDescriptors"): "metal4::StaticLinkingDescriptor::set_internal_functions",
        ("MTL4::CommandBuffer", "resolveCounterHeap"): "metal4::RecordingCommandBuffer::resolve_counter_heap",
        ("MTL4::CommandEncoder", "commandBuffer"): "metal4::RecordingCommandBuffer",
        ("MTL4::CommandQueueDescriptor", "feedbackQueue"): "metal4::SubmittedCommandBuffers::wait",
        ("MTL4::CommandQueueDescriptor", "setFeedbackQueue"): "metal4::SubmittedCommandBuffers::wait",
        ("MTL4::CommitFeedback", "error"): "metal4::SubmittedCommandBuffers::wait",
        ("MTL::ArgumentDescriptor", "argumentDescriptor"): "metal::ArgumentDescriptor::new",
        ("MTL::FunctionDescriptor", "binaryArchives"): "metal::FunctionDescriptor::binary_archives_vec",
        ("MTL::FunctionDescriptor", "setBinaryArchives"): "metal::FunctionDescriptor::set_binary_archives_slice",
        ("MTL::FunctionDescriptor", "functionDescriptor"): "metal::FunctionDescriptor::new",
        ("MTL::PipelineBufferDescriptorArray", "object"): "metal::PipelineBufferDescriptorArray::buffer",
        ("MTL::PipelineBufferDescriptorArray", "setObject"): "metal::PipelineBufferDescriptorArray::set_buffer",
        ("MTL::SamplerDescriptor", "rAddressMode"): "metal::SamplerDescriptor::r_address_mode",
        ("MTL::SamplerDescriptor", "setRAddressMode"): "metal::SamplerDescriptor::set_r_address_mode",
        ("MTL::SamplerState", "gpuResourceID"): "metal::SamplerState::gpu_resource_id",
        ("MTL::DepthStencilState", "gpuResourceID"): "metal::DepthStencilState::gpu_resource_id",
        ("MTL::CounterSet", "counters"): "metal::CounterSet::counters_vec",
        ("MTL::CounterSampleBuffer", "resolveCounterRange"): "metal::CounterSampleBuffer::resolve_counter_range",
        ("MTL::DynamicLibrary", "serializeToURL"): "metal::DynamicLibrary::serialize_to_file",
        ("MTL::FunctionHandle", "gpuResourceID"): "metal::FunctionHandle::gpu_resource_id",
        ("MTL::FunctionLogDebugLocation", "URL"): "metal::FunctionLogDebugLocation::source_url",
        ("MTL::FunctionReflection", "bindings"): "metal::FunctionReflection::bindings_vec",
        ("MTL::LinkedFunctions", "linkedFunctions"): "metal::LinkedFunctions::new",
        ("MTL::TensorAuxiliaryPlaneDescriptorMap", "descriptor"): "metal::TensorAuxiliaryPlaneDescriptorMap::descriptor",
        ("MTL::TensorAuxiliaryPlaneDescriptorMap", "setDescriptor"): "metal::TensorAuxiliaryPlaneDescriptorMap::set_descriptor",
        ("MTL::TensorAuxiliaryPlaneDescriptorMap", "reset"): "metal::TensorAuxiliaryPlaneDescriptorMap::reset",
        ("MTL::Tensor", "auxiliaryPlanes"): "metal::Tensor::auxiliary_plane_objects",
        ("MTL::Tensor", "gpuResourceID"): "metal::Tensor::gpu_resource_id",
        ("MTL4::ComputePipelineDescriptor", "requiredThreadsPerThreadgroup"): "metal4::ComputePipelineDescriptor::required_threads_per_threadgroup_safe",
        ("MTL4::ComputePipelineDescriptor", "setRequiredThreadsPerThreadgroup"): "metal4::ComputePipelineDescriptor::set_required_threads_per_threadgroup_safe",
        ("MTL4::ComputePipelineDescriptor", "reset"): "metal4::ComputePipelineDescriptor::reset_pipeline_descriptor",
        ("MTL4::TileRenderPipelineDescriptor", "requiredThreadsPerThreadgroup"): "metal4::TileRenderPipelineDescriptor::required_threads_per_threadgroup_safe",
        ("MTL4::TileRenderPipelineDescriptor", "setRequiredThreadsPerThreadgroup"): "metal4::TileRenderPipelineDescriptor::set_required_threads_per_threadgroup_safe",
        ("MTL4::TileRenderPipelineDescriptor", "reset"): "metal4::TileRenderPipelineDescriptor::reset_pipeline_descriptor",
        ("MTL4::StitchedFunctionDescriptor", "functionDescriptors"): "metal4::StitchedFunctionDescriptor::function_descriptors_vec",
        ("MTL4::StitchedFunctionDescriptor", "setFunctionDescriptors"): "metal4::StitchedFunctionDescriptor::set_function_descriptors_slice",
        ("MTL4::RenderPassDescriptor", "getSamplePositions"): "metal4::RenderPassDescriptor::sample_positions_vec",
        ("MTL4::RenderPassDescriptor", "setSamplePositions"): "metal4::RenderPassDescriptor::set_sample_positions_slice",
        ("MTL4::PipelineDataSetSerializer", "serializeAsArchiveAndFlushToURL"): "metal4::PipelineDataSetSerializer::serialize_archive_to_path",
        ("MTL4::PipelineDataSetSerializer", "serializeAsPipelinesScript"): "metal4::PipelineDataSetSerializer::serialize_pipelines_script",
        ("MTL4::CommandAllocator", "allocatedSize"): "metal4::CommandAllocator::allocated_size_safe",
        ("MTL4::CommandAllocator", "reset"): "metal4::CommandAllocator::reset_safe",
        ("MTL4::CompilerTask", "waitUntilCompleted"): "metal4::CompilerTask::wait_until_completed_safe",
        ("MTL::CommandBufferEncoderInfo", "debugSignposts"): "metal::CommandBufferEncoderInfo::debug_signposts",
        ("MTL::CommandBuffer", "computeCommandEncoder"): "metal::CommandBuffer::compute_encoder",
        ("MTL::CommandBuffer", "renderCommandEncoder"): "metal::CommandBuffer::render_encoder",
        ("MTL::IOScratchBufferAllocator", "newScratchBuffer"): "metal::IoScratchBufferAllocator::new_scratch_buffer",
        ("MTL::Texture", "pixelFormat"): "metal::Texture::pixel_format",
        ("MTL::RasterizationRateMap", "physicalSize"): "metal::RasterizationRateMap::physical_size",
        ("MTL::Library", "reflectionForFunction"): "metal::Library::reflection_for_function",
        ("MTL::FunctionConstantValues", "reset"): "metal::FunctionConstantValues::reset",
        ("MTL::CompileOptions", "libraries"): "metal::CompileOptions::libraries",
        ("MTL::CompileOptions", "setLibraries"): "metal::CompileOptions::set_libraries",
        ("MTL::CompileOptions", "preprocessorMacros"): "metal::CompileOptions::preprocessor_macros",
        ("MTL::CompileOptions", "setPreprocessorMacros"): "metal::CompileOptions::set_preprocessor_macros",
        ("MTL::ComputePipelineState", "newComputePipelineStateWithBinaryFunctions"): "metal::ComputePipelineState::with_metal4_binary_functions",
        ("MTL::ComputePipelineState", "newIntersectionFunctionTable"): "metal::ComputePipelineState::new_intersection_function_table",
        ("MTL::ComputePipelineState", "newVisibleFunctionTable"): "metal::ComputePipelineState::new_visible_function_table",
        ("MTL::RenderPipelineState", "newIntersectionFunctionTable"): "metal::RenderPipelineState::new_intersection_function_table",
        ("MTL::RenderPipelineState", "newRenderPipelineDescriptor"): "metal::RenderPipelineState::new_render_pipeline_descriptor",
        ("MTL::RenderPipelineState", "newRenderPipelineState"): "metal::RenderPipelineState::with_metal4_binary_functions",
        ("MTL::RenderPipelineState", "newVisibleFunctionTable"): "metal::RenderPipelineState::new_visible_function_table",
        ("MTL4::CommandQueue", "updateBufferMappings"): "metal4::CommandQueue::update_buffer_mappings",
        ("MTL4::CommandQueue", "copyBufferMappingsFromBuffer"): "metal4::CommandQueue::copy_buffer_mappings",
        ("MTL4::CommandQueue", "updateTextureMappings"): "metal4::CommandQueue::update_texture_mappings",
        ("MTL4::CommandQueue", "copyTextureMappingsFromTexture"): "metal4::CommandQueue::copy_texture_mappings",
        ("MTL4::RenderCommandEncoder", "dispatchThreadsPerTile"): "metal4::RecordingRenderEncoder::dispatch_threads_per_tile",
        ("MTL4::RenderCommandEncoder", "drawMeshThreads"): "metal4::RecordingRenderEncoder::draw_mesh_threads",
        ("MTL4::RenderCommandEncoder", "drawPrimitives"): "metal4::RecordingRenderEncoder::draw_primitives_indirect",
        ("MTL4::RenderCommandEncoder", "setColorAttachmentMap"): "metal4::RecordingRenderEncoder::set_color_attachment_map",
        ("MTL4::RenderCommandEncoder", "setScissorRect"): "metal4::RecordingRenderEncoder::set_scissor_rect",
        ("MTL4::RenderCommandEncoder", "setScissorRects"): "metal4::RecordingRenderEncoder::set_scissor_rects",
        ("MTL4::RenderCommandEncoder", "setVertexAmplificationCount"): "metal4::RecordingRenderEncoder::set_vertex_amplification",
        ("MTL4::RenderCommandEncoder", "setViewports"): "metal4::RecordingRenderEncoder::set_viewports",
        ("MTL4::RenderCommandEncoder", "tileHeight"): "metal4::RecordingRenderEncoder::tile_height",
        ("MTL4::RenderCommandEncoder", "tileWidth"): "metal4::RecordingRenderEncoder::tile_width",
        ("MTL4::RenderCommandEncoder", "writeTimestamp"): "metal4::RecordingRenderEncoder::write_timestamp",
        ("MTL4::ComputeCommandEncoder", "copyIndirectCommandBuffer"): "metal4::RecordingComputeEncoder::copy_indirect_commands",
        ("MTL4::ComputeCommandEncoder", "fillBuffer"): "metal4::RecordingComputeEncoder::fill_buffer",
        ("MTL4::ComputeCommandEncoder", "generateMipmaps"): "metal4::RecordingComputeEncoder::generate_mipmaps",
        ("MTL4::ComputeCommandEncoder", "optimizeIndirectCommandBuffer"): "metal4::RecordingComputeEncoder::optimize_indirect_commands",
        ("MTL4::ComputeCommandEncoder", "resetCommandsInBuffer"): "metal4::RecordingComputeEncoder::reset_commands",
        ("MTL4::ComputeCommandEncoder", "writeTimestamp"): "metal4::RecordingComputeEncoder::write_timestamp",
        ("MTL4::CounterHeap", "resolveCounterRange"): "metal4::CompletedCommandBuffers::resolve_counters",
        ("MTL::BlitPassSampleBufferAttachmentDescriptorArray", "object"): "metal::BlitPassSampleBufferAttachmentDescriptorArray::attachment",
        ("MTL::BlitPassSampleBufferAttachmentDescriptorArray", "setObject"): "metal::BlitPassSampleBufferAttachmentDescriptorArray::set_attachment",
        ("MTL::BlitPassDescriptor", "blitPassDescriptor"): "metal::BlitPassDescriptor::new",
        ("MTL::ResourceStatePassSampleBufferAttachmentDescriptorArray", "object"): "metal::ResourceStatePassSampleBufferAttachmentDescriptorArray::attachment",
        ("MTL::ResourceStatePassSampleBufferAttachmentDescriptorArray", "setObject"): "metal::ResourceStatePassSampleBufferAttachmentDescriptorArray::set_attachment",
        ("MTL::ResourceStatePassDescriptor", "resourceStatePassDescriptor"): "metal::ResourceStatePassDescriptor::new",
        ("MTL::CommandEncoder", "barrierAfterQueueStages"): "metal::CommandEncoder::barrier_after_queue_stages",
        ("MTL::PrimitiveAccelerationStructureDescriptor", "descriptor"): "metal::PrimitiveAccelerationStructureDescriptor::new",
        ("MTL::AccelerationStructureTriangleGeometryDescriptor", "descriptor"): "metal::AccelerationStructureTriangleGeometryDescriptor::new",
        ("MTL::AccelerationStructureBoundingBoxGeometryDescriptor", "descriptor"): "metal::AccelerationStructureBoundingBoxGeometryDescriptor::new",
        ("MTL::MotionKeyframeData", "data"): "metal::MotionKeyframeData::new",
        ("MTL::AccelerationStructureMotionTriangleGeometryDescriptor", "descriptor"): "metal::AccelerationStructureMotionTriangleGeometryDescriptor::new",
        ("MTL::AccelerationStructureMotionBoundingBoxGeometryDescriptor", "descriptor"): "metal::AccelerationStructureMotionBoundingBoxGeometryDescriptor::new",
        ("MTL::AccelerationStructureCurveGeometryDescriptor", "descriptor"): "metal::AccelerationStructureCurveGeometryDescriptor::new",
        ("MTL::AccelerationStructureMotionCurveGeometryDescriptor", "descriptor"): "metal::AccelerationStructureMotionCurveGeometryDescriptor::new",
        ("MTL::InstanceAccelerationStructureDescriptor", "descriptor"): "metal::InstanceAccelerationStructureDescriptor::new",
        ("MTL::IndirectInstanceAccelerationStructureDescriptor", "descriptor"): "metal::IndirectInstanceAccelerationStructureDescriptor::new",
        ("MTL::AccelerationStructurePassDescriptor", "accelerationStructurePassDescriptor"): "metal::AccelerationStructurePassDescriptor::new",
        ("MTL::AccelerationStructurePassSampleBufferAttachmentDescriptorArray", "object"): "metal::AccelerationStructurePassSampleBufferAttachmentDescriptorArray::attachment",
        ("MTL::AccelerationStructurePassSampleBufferAttachmentDescriptorArray", "setObject"): "metal::AccelerationStructurePassSampleBufferAttachmentDescriptorArray::set_attachment",
        ("MTL::CaptureDescriptor", "captureObject"): "metal::CaptureDescriptor::capture_target",
        ("MTL::CaptureManager", "alloc"): "metal::CaptureSession",
        ("MTL::CaptureManager", "init"): "metal::CaptureSession",
        ("MTL::VertexBufferLayoutDescriptorArray", "object"): "metal::VertexBufferLayoutDescriptorArray::get",
        ("MTL::VertexBufferLayoutDescriptorArray", "setObject"): "metal::VertexBufferLayoutDescriptorArray::set",
        ("MTL::VertexAttributeDescriptorArray", "object"): "metal::VertexAttributeDescriptorArray::get",
        ("MTL::VertexAttributeDescriptorArray", "setObject"): "metal::VertexAttributeDescriptorArray::set",
        ("MTL::VertexDescriptor", "reset"): "metal::VertexDescriptor::reset_safe",
        ("MTL::VertexDescriptor", "vertexDescriptor"): "metal::VertexDescriptor::default_descriptor",
        ("MTL::BufferLayoutDescriptorArray", "object"): "metal::BufferLayoutDescriptorArray::get",
        ("MTL::BufferLayoutDescriptorArray", "setObject"): "metal::BufferLayoutDescriptorArray::set",
        ("MTL::AttributeDescriptorArray", "object"): "metal::AttributeDescriptorArray::get",
        ("MTL::AttributeDescriptorArray", "setObject"): "metal::AttributeDescriptorArray::set",
        ("MTL::StageInputOutputDescriptor", "reset"): "metal::StageInputOutputDescriptor::reset_safe",
        ("MTL::StageInputOutputDescriptor", "stageInputOutputDescriptor"): "metal::StageInputOutputDescriptor::default_descriptor",
        ("MTL::TensorBufferAttachments", "buffer"): "metal::CheckedTensorBufferAttachments::buffer",
        ("MTL::TensorBufferAttachments", "offset"): "metal::CheckedTensorBufferAttachments::offset",
        ("MTL::TensorBufferAttachments", "setBuffer"): "metal::CheckedTensorBufferAttachments::set_buffer",
        ("MTL::TensorBufferAttachments", "reset"): "metal::CheckedTensorBufferAttachments::reset",
        ("MTL4::CounterHeap", "invalidateCounterRange"): "metal4::TimestampCounterHeap::invalidate_range",
        ("MTL4::CounterHeap", "label"): "metal4::TimestampCounterHeap::label",
        ("MTL4::CounterHeap", "setLabel"): "metal4::TimestampCounterHeap::set_label",
        ("MTL4::CounterHeap", "type"): "metal4::TimestampCounterHeap::heap_type",
        ("MTL::Resource", "isAliasable"): "metal::Resource::is_aliasable",
        ("MTL::Resource", "makeAliasable"): "metal::Resource::make_aliasable",
        ("MTL::Resource", "setOwner"): "metal::Resource::set_owner",
        ("MTL::Resource", "setPurgeableState"): "metal::Resource::set_purgeable_state",
        ("MTL::ResourceViewPool", "baseResourceID"): "metal::ResourceViewPool::base_resource_id",
        ("MTL::ResourceViewPool", "copyResourceViewsFromPool"): "metal::ResourceViewPool::copy_resource_views_from_pool",
        # Command-buffer lifecycle and submission-bound operations.
        ("MTL::CommandBuffer", "encodeSignalEvent"): "metal::CommandBuffer::encode_signal_event",
        ("MTL::CommandBuffer", "encodeWait"): "metal::CommandBuffer::encode_wait",
        ("MTL::CommandBuffer", "enqueue"): "metal::CommandBuffer::enqueue",
        ("MTL::CommandBuffer", "errorOptions"): "metal::CommandBuffer::error_options",
        ("MTL::CommandBuffer", "logs"): "metal::CompletedCommandBuffer::logs",
        ("MTL::CommandBuffer", "useResidencySet"): "metal::CommandBuffer::use_residency_sets",
        ("MTL::CommandBuffer", "useResidencySets"): "metal::CommandBuffer::use_residency_sets",
        ("MTL::CommandBuffer", "waitUntilScheduled"): "metal::SubmittedCommandBuffer::wait_until_scheduled",
        # Render/compute pass descriptors and checked attachment indexing.
        ("MTL::ComputePassDescriptor", "alloc"): "metal::ComputePassDescriptor::new",
        ("MTL::ComputePassDescriptor", "computePassDescriptor"): "metal::ComputePassDescriptor::new",
        ("MTL::ComputePassDescriptor", "dispatchType"): "metal::ComputePassDescriptor::dispatch_type",
        ("MTL::ComputePassDescriptor", "init"): "metal::ComputePassDescriptor::new",
        ("MTL::ComputePassDescriptor", "sampleBufferAttachments"): "metal::ComputePassDescriptor::sample_buffer_attachment",
        ("MTL::ComputePassDescriptor", "setDispatchType"): "metal::ComputePassDescriptor::set_dispatch_type",
        ("MTL::ComputePassSampleBufferAttachmentDescriptorArray", "object"): "metal::ComputePassDescriptor::sample_buffer_attachment",
        ("MTL::ComputePassSampleBufferAttachmentDescriptorArray", "setObject"): "metal::ComputePassDescriptor::set_sample_buffer_attachment",
        ("MTL::RenderPassDescriptor", "colorAttachments"): "metal::RenderPassDescriptor::color_attachment",
        ("MTL::RenderPassDescriptor", "depthAttachment"): "metal::RenderPassDescriptor::depth_attachment",
        ("MTL::RenderPassDescriptor", "rasterizationRateMap"): "metal::RenderPassDescriptor::rasterization_rate_map",
        ("MTL::RenderPassDescriptor", "sampleBufferAttachments"): "metal::RenderPassDescriptor::sample_buffer_attachment",
        ("MTL::RenderPassDescriptor", "setDepthAttachment"): "metal::RenderPassDescriptor::set_depth_attachment",
        ("MTL::RenderPassDescriptor", "setRasterizationRateMap"): "metal::RenderPassDescriptor::set_rasterization_rate_map",
        ("MTL::RenderPassDescriptor", "setStencilAttachment"): "metal::RenderPassDescriptor::set_stencil_attachment",
        ("MTL::RenderPassDescriptor", "stencilAttachment"): "metal::RenderPassDescriptor::stencil_attachment",
        ("MTL::RenderPassColorAttachmentDescriptor", "clearColor"): "metal::RenderPassDescriptor::color_attachment_clear_color",
        ("MTL::RenderPassColorAttachmentDescriptor", "setClearColor"): "metal::RenderPassDescriptor::set_color_attachment_clear_color",
        ("MTL::RenderPassColorAttachmentDescriptorArray", "object"): "metal::RenderPassDescriptor::color_attachment",
        ("MTL::RenderPassColorAttachmentDescriptorArray", "setObject"): "metal::RenderPassDescriptor::set_color_attachment_descriptor",
        ("MTL::RenderPassSampleBufferAttachmentDescriptorArray", "object"): "metal::RenderPassDescriptor::sample_buffer_attachment",
        ("MTL::RenderPassSampleBufferAttachmentDescriptorArray", "setObject"): "metal::RenderPassDescriptor::set_sample_buffer_attachment",
        # Capture owns the Objective-C target and turns begin/end into a scoped guard.
        ("MTL::CaptureManager", "defaultCaptureScope"): "metal::CaptureSession::default_scope",
        ("MTL::CaptureManager", "isCapturing"): "metal::CaptureSession::is_capturing",
        ("MTL::CaptureManager", "setDefaultCaptureScope"): "metal::CaptureSession::set_default_scope",
        ("MTL::CaptureManager", "stopCapture"): "metal::CaptureSession::finish",
        ("MTL::CaptureManager", "supportsDestination"): "metal::CaptureSession::supports_destination",
        ("MTL::CaptureDescriptor", "destination"): "metal::CaptureDescriptor::destination",
        ("MTL::CaptureDescriptor", "outputURL"): "metal::CaptureDescriptor::output_path",
        ("MTL::CaptureDescriptor", "setCaptureObject"): "metal::CaptureDescriptor::set_capture_device",
        ("MTL::CaptureDescriptor", "setDestination"): "metal::CaptureDescriptor::set_destination",
        ("MTL::CaptureDescriptor", "setOutputURL"): "metal::CaptureDescriptor::set_capture_output",
        ("MTL::CaptureScope", "beginScope"): "metal::CaptureScope::with_scope",
        ("MTL::CaptureScope", "endScope"): "metal::CaptureScope::with_scope",
        # Rust-owned shader metadata and selector-gated pipeline helpers.
        ("MTL::Library", "functionNames"): "metal::Library::function_names",
        ("MTL::Function", "functionConstantsDictionary"): "metal::Function::function_constant_names",
        ("MTL::Function", "stageInputAttributes"): "metal::Function::stage_input_attribute_names",
        ("MTL::Function", "vertexAttributes"): "metal::Function::vertex_attribute_names",
        ("MTL::CompileOptions", "floatingPointConversionRoundingMode"): "metal::CompileOptions::floating_point_conversion_rounding_mode",
        ("MTL::CompileOptions", "setFloatingPointConversionRoundingMode"): "metal::CompileOptions::set_floating_point_conversion_rounding_mode",
        ("MTL::RenderPipelineState", "gpuResourceID"): "metal::RenderPipelineState::gpu_resource_id",
        ("MTL::RenderPipelineState", "imageblockMemoryLength"): "metal::RenderPipelineState::imageblock_memory_length",
        ("MTL::RenderPipelineState", "maxTotalThreadgroupsPerMeshGrid"): "metal::RenderPipelineState::max_total_threadgroups_per_mesh_grid",
        ("MTL::RenderPipelineState", "maxTotalThreadsPerMeshThreadgroup"): "metal::RenderPipelineState::max_total_threads_per_mesh_threadgroup",
        ("MTL::RenderPipelineState", "maxTotalThreadsPerObjectThreadgroup"): "metal::RenderPipelineState::max_total_threads_per_object_threadgroup",
        ("MTL::RenderPipelineState", "meshThreadExecutionWidth"): "metal::RenderPipelineState::mesh_thread_execution_width",
        ("MTL::RenderPipelineState", "objectThreadExecutionWidth"): "metal::RenderPipelineState::object_thread_execution_width",
        ("MTL::RenderPipelineState", "reflection"): "metal::RenderPipelineState::reflection",
        ("MTL::ComputePipelineState", "gpuResourceID"): "metal::ComputePipelineState::gpu_resource_id",
        ("MTL::ComputePipelineState", "imageblockMemoryLength"): "metal::ComputePipelineState::imageblock_memory_length",
        ("MTL::ComputePipelineState", "reflection"): "metal::ComputePipelineState::reflection",
        # Texture/resource identity and safe CPU writes.
        ("MTL::TextureDescriptor", "swizzle"): "metal::TextureDescriptor::swizzle",
        ("MTL::TextureDescriptor", "setSwizzle"): "metal::TextureDescriptor::set_swizzle",
        ("MTL::Texture", "gpuResourceID"): "metal::Texture::gpu_resource_id",
        ("MTL::Texture", "iosurface"): "metal::Texture::iosurface",
        ("MTL::Texture", "iosurfacePlane"): "metal::Texture::iosurface_plane",
        ("MTL::Texture", "newRemoteTextureViewForDevice"): "metal::Texture::new_remote_view",
        ("MTL::Texture", "newSharedTextureHandle"): "metal::Texture::new_shared_texture_handle",
        ("MTL::Texture", "remoteStorageTexture"): "metal::Texture::remote_storage_texture",
        ("MTL::Texture", "rootResource"): "metal::Texture::root_resource",
        ("MTL::Texture", "swizzle"): "metal::Texture::swizzle",
        # Rasterization-rate, heap and residency abstractions.
        ("MTL::Heap", "maxAvailableSize"): "metal::Heap::max_available_size",
        ("MTL::Heap", "setPurgeableState"): "metal::Heap::set_purgeable_state",
        ("MTL::RasterizationRateLayerDescriptor", "maxSampleCount"): "metal::RasterizationRateLayerDescriptor::max_sample_count",
        ("MTL::RasterizationRateLayerDescriptor", "sampleCount"): "metal::RasterizationRateLayerDescriptor::sample_count",
        ("MTL::RasterizationRateLayerDescriptor", "setSampleCount"): "metal::RasterizationRateLayerDescriptor::set_sample_count",
        ("MTL::RasterizationRateLayerDescriptor", "horizontalSampleStorage"): "metal::RasterizationRateLayerDescriptor::horizontal_samples",
        ("MTL::RasterizationRateLayerDescriptor", "verticalSampleStorage"): "metal::RasterizationRateLayerDescriptor::vertical_samples",
        ("MTL::RasterizationRateSampleArray", "object"): "metal::RasterizationRateLayerDescriptor::horizontal_samples",
        ("MTL::RasterizationRateSampleArray", "setObject"): "metal::RasterizationRateLayerDescriptor::set_horizontal_sample",
        ("MTL::RasterizationRateLayerArray", "object"): "metal::RasterizationRateMapDescriptor::layer",
        ("MTL::RasterizationRateLayerArray", "setObject"): "metal::RasterizationRateMapDescriptor::set_layer",
        ("MTL::RasterizationRateMapDescriptor", "layer"): "metal::RasterizationRateMapDescriptor::layer",
        ("MTL::RasterizationRateMapDescriptor", "layers"): "metal::RasterizationRateMapDescriptor::layer_vec",
        ("MTL::RasterizationRateMapDescriptor", "screenSize"): "metal::RasterizationRateMapDescriptor::screen_size",
        ("MTL::RasterizationRateMapDescriptor", "setScreenSize"): "metal::RasterizationRateMapDescriptor::set_screen_size",
        ("MTL::RasterizationRateMapDescriptor", "setLayer"): "metal::RasterizationRateMapDescriptor::set_layer",
        ("MTL::RasterizationRateMap", "copyParameterDataToBuffer"): "metal::RasterizationRateMap::copy_parameter_data_to_buffer",
        ("MTL::RasterizationRateMap", "mapPhysicalToScreenCoordinates"): "metal::RasterizationRateMap::map_physical_to_screen_coordinates",
        ("MTL::RasterizationRateMap", "mapScreenToPhysicalCoordinates"): "metal::RasterizationRateMap::map_screen_to_physical_coordinates",
        ("MTL::RasterizationRateMap", "parameterBufferSizeAndAlign"): "metal::RasterizationRateMap::parameter_buffer_size_and_align",
        ("MTL::RasterizationRateMap", "physicalGranularity"): "metal::RasterizationRateMap::physical_granularity",
        ("MTL::RasterizationRateMap", "screenSize"): "metal::RasterizationRateMap::screen_size",
        ("MTL::ResidencySet", "addAllocation"): "metal::ResidencySet::add_allocation",
        ("MTL::ResidencySet", "addAllocations"): "metal::ResidencySet::add_allocations",
        ("MTL::ResidencySet", "allAllocations"): "metal::ResidencySet::allocation_vec",
        ("MTL::ResidencySet", "commit"): "metal::ResidencySet::commit",
        ("MTL::ResidencySet", "containsAllocation"): "metal::ResidencySet::contains_allocation",
        ("MTL::ResidencySet", "endResidency"): "metal::ResidencySet::end_residency",
        ("MTL::ResidencySet", "removeAllAllocations"): "metal::ResidencySet::remove_all_allocations",
        ("MTL::ResidencySet", "removeAllocation"): "metal::ResidencySet::remove_allocation",
        ("MTL::ResidencySet", "removeAllocations"): "metal::ResidencySet::remove_allocations",
        ("MTL::ResidencySet", "requestResidency"): "metal::ResidencySet::request_residency",
    }
)

ACTUAL_METHOD_SIGNATURES: dict[tuple[str, str, str], str] = {}

VALUE_HELPER_SUBSTITUTE_METHODS = {
    ("MTL::PackedFloat3", "PackedFloat3"): "metal::PackedFloat3",
    ("MTL::PackedFloat3", "operator[]"): "metal::PackedFloat3",
    ("MTL::PackedFloat4x3", "PackedFloat4x3"): "metal::PackedFloat4x3",
    ("MTL::PackedFloat4x3", "operator[]"): "metal::PackedFloat4x3",
    ("MTL::PackedFloatQuaternion", "PackedFloatQuaternion"): "metal::PackedFloatQuaternion",
    ("MTL::PackedFloatQuaternion", "operator[]"): "metal::PackedFloatQuaternion",
    ("MTL::AxisAlignedBoundingBox", "AxisAlignedBoundingBox"): "metal::AxisAlignedBoundingBox",
    ("MTL::TextureSwizzleChannels", "TextureSwizzleChannels"): "metal::TextureSwizzleChannels",
    ("MTL::TextureSwizzleChannels", "Default"): "metal::TextureSwizzleChannels",
    ("MTL::TextureSwizzleChannels", "Make"): "metal::TextureSwizzleChannels",
    ("MTL::SamplePosition", "SamplePosition"): "metal::SamplePosition",
    ("MTL::SamplePosition", "Make"): "metal::SamplePosition",
    ("MTL4::BufferRange", "BufferRange"): "metal4::BufferRange",
    ("MTL4::BufferRange", "Make"): "metal4::BufferRange",
}
ACTUAL_METHODS.update(VALUE_HELPER_SUBSTITUTE_METHODS)

ACTUAL_METHODS.update(
    {
        ("MTL::IndirectCommandBuffer", "gpuResourceID"): "metal::IndirectCommandBuffer::gpu_resource_id",
        ("MTL::IndirectCommandBuffer", "indirectComputeCommand"): "metal::IndirectCommandBuffer::with_indirect_compute_command",
        ("MTL::IndirectCommandBuffer", "indirectRenderCommand"): "metal::IndirectCommandBuffer::with_indirect_render_command",
        ("MTL::IndirectCommandBuffer", "reset"): "metal::IndirectCommandBuffer::reset_commands",
        ("MTL4::MeshRenderPipelineDescriptor", "requiredThreadsPerMeshThreadgroup"): "metal4::MeshRenderPipelineDescriptor::required_threads_per_mesh_threadgroup_safe",
        ("MTL4::MeshRenderPipelineDescriptor", "requiredThreadsPerObjectThreadgroup"): "metal4::MeshRenderPipelineDescriptor::required_threads_per_object_threadgroup_safe",
        ("MTL4::MeshRenderPipelineDescriptor", "reset"): "metal4::MeshRenderPipelineDescriptor::reset_safe",
        ("MTL4::MeshRenderPipelineDescriptor", "setRequiredThreadsPerMeshThreadgroup"): "metal4::MeshRenderPipelineDescriptor::set_required_threads_per_mesh_threadgroup_safe",
        ("MTL4::MeshRenderPipelineDescriptor", "setRequiredThreadsPerObjectThreadgroup"): "metal4::MeshRenderPipelineDescriptor::set_required_threads_per_object_threadgroup_safe",
        ("MTL4::MachineLearningPipelineDescriptor", "inputDimensionsAtBufferIndex"): "metal4::MachineLearningPipelineDescriptor::input_dimensions",
        ("MTL4::MachineLearningPipelineDescriptor", "reset"): "metal4::MachineLearningPipelineDescriptor::reset_safe",
        ("MTL4::MachineLearningPipelineReflection", "bindings"): "metal4::MachineLearningPipelineReflection::bindings_vec",
    }
)

ACTUAL_METHOD_SIGNATURES.update(
    {
        ("MTL4::ComputeCommandEncoder", "copyFromTensor", "void copyFromTensor(const MTL::Tensor* sourceTensor, const MTL::TensorExtents* sourceOrigin, const MTL::TensorExtents* sourceDimensions, const MTL::Tensor* destinationTensor, const MTL::TensorExtents* destinationOrigin, const MTL::TensorExtents* destinationDimensions);"): "metal4::RecordingComputeEncoder::copy_tensor",
        ("MTL4::ComputeCommandEncoder", "copyFromTensor", "void copyFromTensor(const MTL::Tensor* sourceTensor, const MTL::TensorExtents* sourceOrigin, const MTL::TensorExtents* sourceDimensions, MTL::TensorPlaneType sourcePlane, const MTL::Tensor* destinationTensor, const MTL::TensorExtents* destinationOrigin, const MTL::TensorExtents* destinationDimensions, MTL::TensorPlaneType destinationPlane);"): "metal4::RecordingComputeEncoder::copy_tensor",
        ("MTL::DepthStencilDescriptor", "deprecated", "[[deprecated( )]] bool depthWriteEnabled() const;"): "metal::DepthStencilDescriptor::depth_write_enabled",
        ("MTL::Function", "newArgumentEncoder", "ArgumentEncoder* newArgumentEncoder(NS::UInteger bufferIndex);"): "metal::Function::new_argument_encoder",
        ("MTL::Function", "newArgumentEncoder", "ArgumentEncoder* newArgumentEncoder(NS::UInteger bufferIndex, const MTL::AutoreleasedArgument* reflection);"): "metal::Function::new_argument_encoder_with_reflection",
        ("MTL::ArgumentEncoder", "constantData", "void* constantData(NS::UInteger index);"): "metal::ArgumentEncoder::with_constant_data",
        ("MTL::IndirectRenderCommand", "drawIndexedPatches", "void drawIndexedPatches(NS::UInteger numberOfPatchControlPoints, NS::UInteger patchStart, NS::UInteger patchCount, const MTL::Buffer* patchIndexBuffer, NS::UInteger patchIndexBufferOffset, const MTL::Buffer* controlPointIndexBuffer, NS::UInteger controlPointIndexBufferOffset, NS::UInteger instanceCount, NS::UInteger baseInstance, const MTL::Buffer* buffer, NS::UInteger offset, NS::UInteger instanceStride);"): "metal::IndirectRenderCommandRecording::draw_indexed_patches",
        ("MTL::IndirectRenderCommand", "drawPatches", "void drawPatches(NS::UInteger numberOfPatchControlPoints, NS::UInteger patchStart, NS::UInteger patchCount, const MTL::Buffer* patchIndexBuffer, NS::UInteger patchIndexBufferOffset, NS::UInteger instanceCount, NS::UInteger baseInstance, const MTL::Buffer* buffer, NS::UInteger offset, NS::UInteger instanceStride);"): "metal::IndirectRenderCommandRecording::draw_patches",
        ("MTL::Tensor", "getBytes", "void getBytes(void* bytes, const MTL::TensorExtents* strides, const MTL::TensorExtents* sliceOrigin, const MTL::TensorExtents* sliceDimensions);"): "metal::Tensor::read_slice",
        ("MTL::Tensor", "getBytes", "void getBytes(void* bytes, const MTL::TensorExtents* strides, const MTL::TensorExtents* sliceOrigin, const MTL::TensorExtents* sliceDimensions, MTL::TensorPlaneType plane);"): "metal::Tensor::read_plane_slice",
        ("MTL::Tensor", "replaceSliceOrigin", "void replaceSliceOrigin(const MTL::TensorExtents* sliceOrigin, const MTL::TensorExtents* sliceDimensions, const void* bytes, const MTL::TensorExtents* strides);"): "metal::Tensor::write_slice",
        ("MTL::Tensor", "replaceSliceOrigin", "void replaceSliceOrigin(const MTL::TensorExtents* sliceOrigin, const MTL::TensorExtents* sliceDimensions, MTL::TensorPlaneType plane, const void* bytes, const MTL::TensorExtents* strides);"): "metal::Tensor::write_plane_slice",
        ("MTL4::ComputeCommandEncoder", "buildAccelerationStructure", "void buildAccelerationStructure(const MTL::AccelerationStructure* accelerationStructure, const MTL4::AccelerationStructureDescriptor* descriptor, const MTL4::BufferRange scratchBuffer);"): "metal4::RecordingComputeEncoder::build_acceleration_structure",
        ("MTL4::ComputeCommandEncoder", "copyAccelerationStructure", "void copyAccelerationStructure(const MTL::AccelerationStructure* sourceAccelerationStructure, const MTL::AccelerationStructure* destinationAccelerationStructure);"): "metal4::RecordingComputeEncoder::copy_acceleration_structure",
        ("MTL4::ComputeCommandEncoder", "copyAndCompactAccelerationStructure", "void copyAndCompactAccelerationStructure(const MTL::AccelerationStructure* sourceAccelerationStructure, const MTL::AccelerationStructure* destinationAccelerationStructure);"): "metal4::RecordingComputeEncoder::copy_and_compact_acceleration_structure",
        ("MTL4::ComputeCommandEncoder", "refitAccelerationStructure", "void refitAccelerationStructure(const MTL::AccelerationStructure* sourceAccelerationStructure, const MTL4::AccelerationStructureDescriptor* descriptor, const MTL::AccelerationStructure* destinationAccelerationStructure, const MTL4::BufferRange scratchBuffer);"): "metal4::RecordingComputeEncoder::refit_acceleration_structure",
        ("MTL4::ComputeCommandEncoder", "refitAccelerationStructure", "void refitAccelerationStructure(const MTL::AccelerationStructure* sourceAccelerationStructure, const MTL4::AccelerationStructureDescriptor* descriptor, const MTL::AccelerationStructure* destinationAccelerationStructure, const MTL4::BufferRange scratchBuffer, MTL::AccelerationStructureRefitOptions options);"): "metal4::RecordingComputeEncoder::refit_acceleration_structure",
        ("MTL4::ComputeCommandEncoder", "writeCompactedAccelerationStructureSize", "void writeCompactedAccelerationStructureSize(const MTL::AccelerationStructure* accelerationStructure, const MTL4::BufferRange buffer);"): "metal4::RecordingComputeEncoder::write_compacted_acceleration_structure_size",
        ("MTL::TextureViewPool", "setTextureView", "ResourceID setTextureView(const MTL::Texture* texture, NS::UInteger index);"): "metal::TextureViewPool::set_texture_view",
        ("MTL::TextureViewPool", "setTextureView", "ResourceID setTextureView(const MTL::Texture* texture, const MTL::TextureViewDescriptor* descriptor, NS::UInteger index);"): "metal::TextureViewPool::set_texture_view_with_descriptor",
        ("MTL::TextureViewPool", "setTextureViewFromBuffer", "ResourceID setTextureViewFromBuffer(const MTL::Buffer* buffer, const MTL::TextureDescriptor* descriptor, NS::UInteger offset, NS::UInteger bytesPerRow, NS::UInteger index);"): "metal::TextureViewPool::set_texture_view_from_buffer",
        ("MTL::VertexAttribute", "deprecated", "[[deprecated( )]] bool active() const;"): "metal::VertexAttribute::is_active",
        ("MTL::VertexAttribute", "deprecated", "[[deprecated( )]] bool patchControlPointData() const;"): "metal::VertexAttribute::is_patch_control_point_data",
        ("MTL::VertexAttribute", "deprecated", "[[deprecated( )]] bool patchData() const;"): "metal::VertexAttribute::is_patch_data",
        ("MTL::Attribute", "deprecated", "[[deprecated( )]] bool active() const;"): "metal::Attribute::is_active",
        ("MTL::Attribute", "deprecated", "[[deprecated( )]] bool patchControlPointData() const;"): "metal::Attribute::is_patch_control_point_data",
        ("MTL::Attribute", "deprecated", "[[deprecated( )]] bool patchData() const;"): "metal::Attribute::is_patch_data",
        ("MTL4::ComputeCommandEncoder", "copyFromBuffer", "void copyFromBuffer(const MTL::Buffer* sourceBuffer, NS::UInteger sourceOffset, NS::UInteger sourceBytesPerRow, NS::UInteger sourceBytesPerImage, MTL::Size sourceSize, const MTL::Texture* destinationTexture, NS::UInteger destinationSlice, NS::UInteger destinationLevel, MTL::Origin destinationOrigin);"): "metal4::RecordingComputeEncoder::copy_buffer_to_texture",
        ("MTL4::ComputeCommandEncoder", "copyFromBuffer", "void copyFromBuffer(const MTL::Buffer* sourceBuffer, NS::UInteger sourceOffset, NS::UInteger sourceBytesPerRow, NS::UInteger sourceBytesPerImage, MTL::Size sourceSize, const MTL::Texture* destinationTexture, NS::UInteger destinationSlice, NS::UInteger destinationLevel, MTL::Origin destinationOrigin, MTL::BlitOption options);"): "metal4::RecordingComputeEncoder::copy_buffer_to_texture",
        ("MTL4::ComputeCommandEncoder", "copyFromTexture", "void copyFromTexture(const MTL::Texture* sourceTexture, NS::UInteger sourceSlice, NS::UInteger sourceLevel, MTL::Origin sourceOrigin, MTL::Size sourceSize, const MTL::Texture* destinationTexture, NS::UInteger destinationSlice, NS::UInteger destinationLevel, MTL::Origin destinationOrigin);"): "metal4::RecordingComputeEncoder::copy_texture_region",
        ("MTL4::ComputeCommandEncoder", "copyFromTexture", "void copyFromTexture(const MTL::Texture* sourceTexture, NS::UInteger sourceSlice, NS::UInteger sourceLevel, MTL::Origin sourceOrigin, MTL::Size sourceSize, const MTL::Buffer* destinationBuffer, NS::UInteger destinationOffset, NS::UInteger destinationBytesPerRow, NS::UInteger destinationBytesPerImage);"): "metal4::RecordingComputeEncoder::copy_texture_to_buffer",
        ("MTL4::ComputeCommandEncoder", "copyFromTexture", "void copyFromTexture(const MTL::Texture* sourceTexture, NS::UInteger sourceSlice, NS::UInteger sourceLevel, MTL::Origin sourceOrigin, MTL::Size sourceSize, const MTL::Buffer* destinationBuffer, NS::UInteger destinationOffset, NS::UInteger destinationBytesPerRow, NS::UInteger destinationBytesPerImage, MTL::BlitOption options);"): "metal4::RecordingComputeEncoder::copy_texture_to_buffer",
        ("MTL::LogState", "addLogHandler", "void addLogHandler(void (^block)(NS::String*, NS::String*, MTL::LogLevel, NS::String*));"): "metal::LogState::add_log_handler",
        ("MTL::LogState", "addLogHandler", "void addLogHandler(const MTL::LogHandlerFunction& handler);"): "metal::LogState::add_log_handler",
        ("MTL4::CommitOptions", "addFeedbackHandler", "void addFeedbackHandler(const MTL4::CommitFeedbackHandler block);"): "metal4::SubmittedCommandBuffers::wait",
        ("MTL4::CommitOptions", "addFeedbackHandler", "void addFeedbackHandler(const MTL4::CommitFeedbackHandlerFunction& function);"): "metal4::SubmittedCommandBuffers::wait",
        ("MTL::Device", "newLibrary", "Library* newLibrary(const dispatch_data_t data, NS::Error** error);"): "metal::Device::new_library_from_bytes",
        ("MTL::Device", "newDefaultLibrary", "Library* newDefaultLibrary(const NS::Bundle* bundle, NS::Error** error);"): "metal::Device::new_default_library_from_bundle",
        ("MTL::Device", "newTexture", "Texture* newTexture(const MTL::TextureDescriptor* descriptor, const IOSurfaceRef iosurface, NS::UInteger plane);"): "metal::Device::new_texture_from_iosurface",
        ("MTL::Library", "newFunction", "void newFunction(const NS::String* name, const MTL::FunctionConstantValues* constantValues, void (^completionHandler)(MTL::Function*, NS::Error*));"): "metal::Library::specialized_function_async",
        ("MTL::Library", "newFunction", "void newFunction(const MTL::FunctionDescriptor* descriptor, void (^completionHandler)(MTL::Function*, NS::Error*));"): "metal::Library::function_with_descriptor_async",
        ("MTL::Library", "newFunction", "void newFunction(const NS::String* pFunctionName, const MTL::FunctionConstantValues* pConstantValues, const MTL::FunctionCompletionHandlerFunction& completionHandler);"): "metal::Library::specialized_function_async",
        ("MTL::Library", "newFunction", "void newFunction(const MTL::FunctionDescriptor* pDescriptor, const MTL::FunctionCompletionHandlerFunction& completionHandler);"): "metal::Library::function_with_descriptor_async",
        ("MTL::Library", "newIntersectionFunction", "void newIntersectionFunction(const MTL::IntersectionFunctionDescriptor* descriptor, void (^completionHandler)(MTL::Function*, NS::Error*));"): "metal::Library::intersection_function_with_descriptor_async",
        ("MTL::Library", "newIntersectionFunction", "void newIntersectionFunction(const MTL::IntersectionFunctionDescriptor* pDescriptor, const MTL::FunctionCompletionHandlerFunction& completionHandler);"): "metal::Library::intersection_function_with_descriptor_async",
        ("MTL::FunctionConstantValues", "setConstantValue", "void setConstantValue(const void* value, MTL::DataType type, NS::UInteger index);"): "metal::FunctionConstantValues::set_constant_at_index",
        ("MTL::FunctionConstantValues", "setConstantValue", "void setConstantValue(const void* value, MTL::DataType type, const NS::String* name);"): "metal::FunctionConstantValues::set_constant_named",
        ("MTL::FunctionConstantValues", "setConstantValues", "void setConstantValues(const void* values, MTL::DataType type, NS::Range range);"): "metal::FunctionConstantValues::set_constants",
        ("MTL::ComputePipelineState", "functionHandle", "FunctionHandle* functionHandle(const MTL4::BinaryFunction* function);"): "metal::ComputePipelineState::function_handle_for_binary_function",
        ("MTL::ComputePipelineState", "functionHandle", "FunctionHandle* functionHandle(const MTL::Function* function);"): "metal::ComputePipelineState::function_handle_for_function",
        ("MTL::RenderPipelineState", "functionHandle", "FunctionHandle* functionHandle(const MTL4::BinaryFunction* function, MTL::RenderStages stage);"): "metal::RenderPipelineState::function_handle_for_binary_function",
        ("MTL::RenderPipelineState", "functionHandle", "FunctionHandle* functionHandle(const MTL::Function* function, MTL::RenderStages stage);"): "metal::RenderPipelineState::function_handle_for_function",
        ("MTL4::RenderCommandEncoder", "drawIndexedPrimitives", "void drawIndexedPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger indexCount, MTL::IndexType indexType, MTL::GPUAddress indexBuffer, NS::UInteger indexBufferLength);"): "metal4::RecordingRenderEncoder::draw_indexed_primitives",
        ("MTL4::RenderCommandEncoder", "drawIndexedPrimitives", "void drawIndexedPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger indexCount, MTL::IndexType indexType, MTL::GPUAddress indexBuffer, NS::UInteger indexBufferLength, NS::UInteger instanceCount);"): "metal4::RecordingRenderEncoder::draw_indexed_primitives_instanced",
        ("MTL4::RenderCommandEncoder", "drawIndexedPrimitives", "void drawIndexedPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger indexCount, MTL::IndexType indexType, MTL::GPUAddress indexBuffer, NS::UInteger indexBufferLength, NS::UInteger instanceCount, NS::Integer baseVertex, NS::UInteger baseInstance);"): "metal4::RecordingRenderEncoder::draw_indexed_primitives_base",
        ("MTL4::RenderCommandEncoder", "drawIndexedPrimitives", "void drawIndexedPrimitives(MTL::PrimitiveType primitiveType, MTL::IndexType indexType, MTL::GPUAddress indexBuffer, NS::UInteger indexBufferLength, MTL::GPUAddress indirectBuffer);"): "metal4::RecordingRenderEncoder::draw_indexed_primitives_indirect",
        ("MTL4::RenderCommandEncoder", "drawMeshThreadgroups", "void drawMeshThreadgroups(MTL::Size threadgroupsPerGrid, MTL::Size threadsPerObjectThreadgroup, MTL::Size threadsPerMeshThreadgroup);"): "metal4::RecordingRenderEncoder::draw_mesh_threadgroups",
        ("MTL4::RenderCommandEncoder", "drawMeshThreadgroups", "void drawMeshThreadgroups(MTL::GPUAddress indirectBuffer, MTL::Size threadsPerObjectThreadgroup, MTL::Size threadsPerMeshThreadgroup);"): "metal4::RecordingRenderEncoder::draw_mesh_threadgroups_indirect",
        ("MTL4::RenderCommandEncoder", "executeCommandsInBuffer", "void executeCommandsInBuffer(const MTL::IndirectCommandBuffer* indirectCommandBuffer, NS::Range executionRange);"): "metal4::RecordingRenderEncoder::execute_commands",
        ("MTL4::RenderCommandEncoder", "executeCommandsInBuffer", "void executeCommandsInBuffer(const MTL::IndirectCommandBuffer* indirectCommandBuffer, MTL::GPUAddress indirectRangeBuffer);"): "metal4::RecordingRenderEncoder::execute_commands_indirect",
        ("MTL4::ComputeCommandEncoder", "copyFromBuffer", "void copyFromBuffer(const MTL::Buffer* sourceBuffer, NS::UInteger sourceOffset, const MTL::Buffer* destinationBuffer, NS::UInteger destinationOffset, NS::UInteger size);"): "metal4::RecordingComputeEncoder::copy_buffer",
        ("MTL4::ComputeCommandEncoder", "copyFromTexture", "void copyFromTexture(const MTL::Texture* sourceTexture, const MTL::Texture* destinationTexture);"): "metal4::RecordingComputeEncoder::copy_texture",
        ("MTL4::ComputeCommandEncoder", "copyFromTexture", "void copyFromTexture(const MTL::Texture* sourceTexture, NS::UInteger sourceSlice, NS::UInteger sourceLevel, const MTL::Texture* destinationTexture, NS::UInteger destinationSlice, NS::UInteger destinationLevel, NS::UInteger sliceCount, NS::UInteger levelCount);"): "metal4::RecordingComputeEncoder::copy_texture_levels",
        ("MTL4::ComputeCommandEncoder", "dispatchThreadgroups", "void dispatchThreadgroups(MTL::GPUAddress indirectBuffer, MTL::Size threadsPerThreadgroup);"): "metal4::RecordingComputeEncoder::dispatch_threadgroups_indirect",
        ("MTL4::ComputeCommandEncoder", "dispatchThreads", "void dispatchThreads(MTL::GPUAddress indirectBuffer);"): "metal4::RecordingComputeEncoder::dispatch_threads_indirect",
        ("MTL4::ComputeCommandEncoder", "executeCommandsInBuffer", "void executeCommandsInBuffer(const MTL::IndirectCommandBuffer* indirectCommandBuffer, NS::Range executionRange);"): "metal4::RecordingComputeEncoder::execute_commands",
        ("MTL4::ComputeCommandEncoder", "executeCommandsInBuffer", "void executeCommandsInBuffer(const MTL::IndirectCommandBuffer* indirectCommandbuffer, MTL::GPUAddress indirectRangeBuffer);"): "metal4::RecordingComputeEncoder::execute_commands_indirect",
        ("MTL4::ComputeCommandEncoder", "optimizeContentsForCPUAccess", "void optimizeContentsForCPUAccess(const MTL::Texture* texture);"): "metal4::RecordingComputeEncoder::optimize_texture_for_cpu",
        ("MTL4::ComputeCommandEncoder", "optimizeContentsForCPUAccess", "void optimizeContentsForCPUAccess(const MTL::Texture* texture, NS::UInteger slice, NS::UInteger level);"): "metal4::RecordingComputeEncoder::optimize_texture_level_for_cpu",
        ("MTL4::ComputeCommandEncoder", "optimizeContentsForGPUAccess", "void optimizeContentsForGPUAccess(const MTL::Texture* texture);"): "metal4::RecordingComputeEncoder::optimize_texture_for_gpu",
        ("MTL4::ComputeCommandEncoder", "optimizeContentsForGPUAccess", "void optimizeContentsForGPUAccess(const MTL::Texture* texture, NS::UInteger slice, NS::UInteger level);"): "metal4::RecordingComputeEncoder::optimize_texture_level_for_gpu",
        ("MTL::CaptureManager", "newCaptureScope", "CaptureScope* newCaptureScope(const MTL4::CommandQueue* commandQueue);"): "metal::CaptureSession::new_scope_for_mtl4_command_queue",
        ("MTL::Device", "functionHandle", "FunctionHandle* functionHandle(const MTL4::BinaryFunction* function);"): "metal::Device::function_handle_from_binary",
        ("MTL::Device", "newArchive", "MTL4::Archive* newArchive(const NS::URL* url, NS::Error** error);"): "metal::Device::new_mtl4_archive_from_path",
        ("MTL::Device", "newCommandAllocator", "MTL4::CommandAllocator* newCommandAllocator();"): "metal::Device::new_mtl4_command_allocator",
        ("MTL::Device", "newCommandAllocator", "MTL4::CommandAllocator* newCommandAllocator(const MTL4::CommandAllocatorDescriptor* descriptor, NS::Error** error);"): "metal::Device::new_mtl4_command_allocator_from_descriptor",
        ("MTL::Device", "newCompiler", "MTL4::Compiler* newCompiler(const MTL4::CompilerDescriptor* descriptor, NS::Error** error);"): "metal::Device::new_mtl4_compiler",
        ("MTL::Device", "newMTL4CommandQueue", "MTL4::CommandQueue* newMTL4CommandQueue(const MTL4::CommandQueueDescriptor* descriptor, NS::Error** error);"): "metal::Device::new_mtl4_command_queue_from_descriptor",
        ("MTL::Device", "newPipelineDataSetSerializer", "MTL4::PipelineDataSetSerializer* newPipelineDataSetSerializer(const MTL4::PipelineDataSetSerializerDescriptor* descriptor);"): "metal::Device::new_pipeline_data_set_serializer",
        ("MTL::Device", "newResidencySet", "ResidencySet* newResidencySet(const MTL::ResidencySetDescriptor* desc, NS::Error** error);"): "metal::Device::new_residency_set",
        ("MTL::Device", "newTensor", "Tensor* newTensor(const MTL::TensorDescriptor* descriptor, NS::Error** error);"): "metal::Device::new_tensor",
        ("MTL::Device", "newTensor", "Tensor* newTensor(const MTL::TensorDescriptor* descriptor, const MTL::TensorBufferAttachments* attachments, NS::Error** error);"): "metal::Device::new_tensor_with_attachments",
        ("MTL::Device", "newTextureViewPool", "TextureViewPool* newTextureViewPool(const MTL::ResourceViewPoolDescriptor* descriptor, NS::Error** error);"): "metal::Device::new_texture_view_pool",
        ("MTL::Device", "sizeOfCounterHeapEntry", "NS::UInteger sizeOfCounterHeapEntry(MTL4::CounterHeapType type);"): "metal::Device::size_of_counter_heap_entry",
        ("MTL::Device", "tensorSizeAndAlign", "SizeAndAlign tensorSizeAndAlign(const MTL::TensorDescriptor* descriptor);"): "metal::Device::tensor_size_and_align",
        ("MTL::PackedFloat3", "PackedFloat3", "PackedFloat3();"): "metal::PackedFloat3::default",
        ("MTL::PackedFloat3", "PackedFloat3", "PackedFloat3(float x, float y, float z);"): "metal::PackedFloat3::from_components",
        ("MTL::PackedFloat3", "operator[]", "float& operator[](int idx);"): "metal::PackedFloat3::index_mut",
        ("MTL::PackedFloat3", "operator[]", "float operator[](int idx) const;"): "metal::PackedFloat3::index",
        ("MTL::PackedFloat4x3", "PackedFloat4x3", "PackedFloat4x3();"): "metal::PackedFloat4x3::default",
        ("MTL::PackedFloat4x3", "PackedFloat4x3", "PackedFloat4x3(const PackedFloat3& col0, const PackedFloat3& col1, const PackedFloat3& col2, const PackedFloat3& col3);"): "metal::PackedFloat4x3::new",
        ("MTL::PackedFloat4x3", "operator[]", "PackedFloat3& operator[](int idx);"): "metal::PackedFloat4x3::index_mut",
        ("MTL::PackedFloat4x3", "operator[]", "const PackedFloat3& operator[](int idx) const;"): "metal::PackedFloat4x3::index",
        ("MTL::PackedFloatQuaternion", "PackedFloatQuaternion", "PackedFloatQuaternion();"): "metal::PackedFloatQuaternion::default",
        ("MTL::PackedFloatQuaternion", "PackedFloatQuaternion", "PackedFloatQuaternion(float x, float y, float z, float w);"): "metal::PackedFloatQuaternion::from_components",
        ("MTL::PackedFloatQuaternion", "operator[]", "float& operator[](int idx);"): "metal::PackedFloatQuaternion::index_mut",
        ("MTL::PackedFloatQuaternion", "operator[]", "const float& operator[](int idx) const;"): "metal::PackedFloatQuaternion::index",
        ("MTL::BlitCommandEncoder", "copyFromBuffer", "void copyFromBuffer(const MTL::Buffer* sourceBuffer, NS::UInteger sourceOffset, NS::UInteger sourceBytesPerRow, NS::UInteger sourceBytesPerImage, MTL::Size sourceSize, const MTL::Texture* destinationTexture, NS::UInteger destinationSlice, NS::UInteger destinationLevel, MTL::Origin destinationOrigin, MTL::BlitOption options);"): "metal::BlitCommandEncoder::copy_buffer_to_texture_with_options",
        ("MTL::BlitCommandEncoder", "copyFromTensor", "void copyFromTensor(const MTL::Tensor* sourceTensor, const MTL::TensorExtents* sourceOrigin, const MTL::TensorExtents* sourceDimensions, const MTL::Tensor* destinationTensor, const MTL::TensorExtents* destinationOrigin, const MTL::TensorExtents* destinationDimensions);"): "metal::BlitCommandEncoder::copy_tensor",
        ("MTL::BlitCommandEncoder", "copyFromTensor", "void copyFromTensor(const MTL::Tensor* sourceTensor, const MTL::TensorExtents* sourceOrigin, const MTL::TensorExtents* sourceDimensions, MTL::TensorPlaneType sourcePlane, const MTL::Tensor* destinationTensor, const MTL::TensorExtents* destinationOrigin, const MTL::TensorExtents* destinationDimensions, MTL::TensorPlaneType destinationPlane);"): "metal::BlitCommandEncoder::copy_tensor_plane",
        ("MTL::BlitCommandEncoder", "copyFromTexture", "void copyFromTexture(const MTL::Texture* sourceTexture, NS::UInteger sourceSlice, NS::UInteger sourceLevel, MTL::Origin sourceOrigin, MTL::Size sourceSize, const MTL::Buffer* destinationBuffer, NS::UInteger destinationOffset, NS::UInteger destinationBytesPerRow, NS::UInteger destinationBytesPerImage, MTL::BlitOption options);"): "metal::BlitCommandEncoder::copy_texture_to_buffer_with_options",
        ("MTL::BlitCommandEncoder", "getTextureAccessCounters", "void getTextureAccessCounters(const MTL::Texture* texture, MTL::Region region, NS::UInteger mipLevel, NS::UInteger slice, bool resetCounters, const MTL::Buffer* countersBuffer, NS::UInteger countersBufferOffset);"): "metal::BlitCommandEncoder::read_texture_access_counters",
        ("MTL::BlitCommandEncoder", "resolveCounters", "void resolveCounters(const MTL::CounterSampleBuffer* sampleBuffer, NS::Range range, const MTL::Buffer* destinationBuffer, NS::UInteger destinationOffset);"): "metal::BlitCommandEncoder::read_counters",
        ("MTL::BlitCommandEncoder", "synchronizeResource", "void synchronizeResource(const MTL::Resource* resource);"): "metal::BlitCommandEncoder::synchronize_buffer",
        (
            "MTL4::MachineLearningPipelineDescriptor",
            "setInputDimensions",
            "void setInputDimensions(const MTL::TensorExtents* dimensions, NS::Integer bufferIndex);",
        ): "metal4::MachineLearningPipelineDescriptor::set_input_dimensions",
        (
            "MTL4::MachineLearningPipelineDescriptor",
            "setInputDimensions",
            "void setInputDimensions(const NS::Array* dimensions, NS::Range range);",
        ): "metal4::MachineLearningPipelineDescriptor::set_input_dimensions_slice",
    }
)

PIPELINE_DESCRIPTOR_METHODS = {
    "MTL::ComputePipelineReflection": {
        "arguments": "arguments_vec",
        "bindings": "bindings_vec",
    },
    "MTL::ComputePipelineDescriptor": {
        "binaryArchives": "binary_archives_vec",
        "insertLibraries": "insert_libraries_vec",
        "preloadedLibraries": "preloaded_libraries_vec",
        "requiredThreadsPerThreadgroup": "required_threads_per_threadgroup_safe",
        "reset": "reset_safe",
        "setBinaryArchives": "set_binary_archives_slice",
        "setInsertLibraries": "set_insert_libraries_slice",
        "setPreloadedLibraries": "set_preloaded_libraries_slice",
        "setRequiredThreadsPerThreadgroup": "set_required_threads_per_threadgroup_safe",
    },
    "MTL::LogicalToPhysicalColorAttachmentMap": {
        "getPhysicalIndex": "physical_index",
        "reset": "reset_safe",
        "setPhysicalIndex": "set_physical_index",
    },
    "MTL::RenderPipelineReflection": {
        "fragmentArguments": "fragment_arguments_vec",
        "fragmentBindings": "fragment_bindings_vec",
        "meshBindings": "mesh_bindings_vec",
        "objectBindings": "object_bindings_vec",
        "tileArguments": "tile_arguments_vec",
        "tileBindings": "tile_bindings_vec",
        "vertexArguments": "vertex_arguments_vec",
        "vertexBindings": "vertex_bindings_vec",
    },
    "MTL::RenderPipelineDescriptor": {
        "binaryArchives": "binary_archives_vec",
        "colorAttachments": "color_attachments_safe",
        "fragmentBuffers": "fragment_buffers_safe",
        "fragmentLinkedFunctions": "fragment_linked_functions_safe",
        "fragmentPreloadedLibraries": "fragment_preloaded_libraries_vec",
        "setBinaryArchives": "set_binary_archives_slice",
        "setFragmentLinkedFunctions": "set_fragment_linked_functions_safe",
        "setFragmentPreloadedLibraries": "set_fragment_preloaded_libraries_slice",
        "setVertexDescriptor": "set_vertex_descriptor_safe",
        "setVertexLinkedFunctions": "set_vertex_linked_functions_safe",
        "setVertexPreloadedLibraries": "set_vertex_preloaded_libraries_slice",
        "vertexBuffers": "vertex_buffers_safe",
        "vertexDescriptor": "vertex_descriptor_safe",
        "vertexLinkedFunctions": "vertex_linked_functions_safe",
        "vertexPreloadedLibraries": "vertex_preloaded_libraries_vec",
    },
    "MTL::RenderPipelineFunctionsDescriptor": {
        "fragmentAdditionalBinaryFunctions": "fragment_additional_binary_functions_vec",
        "setFragmentAdditionalBinaryFunctions": "set_fragment_additional_binary_functions_slice",
        "setTileAdditionalBinaryFunctions": "set_tile_additional_binary_functions_slice",
        "setVertexAdditionalBinaryFunctions": "set_vertex_additional_binary_functions_slice",
        "tileAdditionalBinaryFunctions": "tile_additional_binary_functions_vec",
        "vertexAdditionalBinaryFunctions": "vertex_additional_binary_functions_vec",
    },
    "MTL::RenderPipelineColorAttachmentDescriptorArray": {"object": "get", "setObject": "set"},
    "MTL::TileRenderPipelineColorAttachmentDescriptorArray": {"object": "get", "setObject": "set"},
    "MTL::TileRenderPipelineDescriptor": {
        "binaryArchives": "binary_archives_vec",
        "preloadedLibraries": "preloaded_libraries_vec",
        "requiredThreadsPerThreadgroup": "required_threads_per_threadgroup_safe",
        "reset": "reset_safe",
        "setBinaryArchives": "set_binary_archives_slice",
        "setPreloadedLibraries": "set_preloaded_libraries_slice",
        "setRequiredThreadsPerThreadgroup": "set_required_threads_per_threadgroup_safe",
    },
    "MTL::MeshRenderPipelineDescriptor": {
        "binaryArchives": "binary_archives_vec",
        "requiredThreadsPerMeshThreadgroup": "required_threads_per_mesh_threadgroup_safe",
        "requiredThreadsPerObjectThreadgroup": "required_threads_per_object_threadgroup_safe",
        "reset": "reset_safe",
        "setBinaryArchives": "set_binary_archives_slice",
        "setRequiredThreadsPerMeshThreadgroup": "set_required_threads_per_mesh_threadgroup_safe",
        "setRequiredThreadsPerObjectThreadgroup": "set_required_threads_per_object_threadgroup_safe",
    },
    "MTL::LinkedFunctions": {
        "binaryFunctions": "binary_functions_vec",
        "functions": "functions_vec",
        "groups": "groups_map",
        "setBinaryFunctions": "set_binary_functions_slice",
        "setFunctions": "set_functions_slice",
        "setGroups": "set_groups_map",
    },
}

for _parent, _methods in PIPELINE_DESCRIPTOR_METHODS.items():
    _rust_parent = _parent.rsplit("::", 1)[-1]
    for _cpp_name, _rust_name in _methods.items():
        ACTUAL_METHODS[(_parent, _cpp_name)] = f"metal::{_rust_parent}::{_rust_name}"

ACTUAL_METHOD_SIGNATURES.update(
    {
        ("MTL::RenderPipelineColorAttachmentDescriptor", "deprecated", "[[deprecated( )]] bool blendingEnabled() const;"): "metal::RenderPipelineColorAttachmentDescriptor::is_blending_enabled",
        ("MTL::MeshRenderPipelineDescriptor", "deprecated", "[[deprecated( )]] bool alphaToCoverageEnabled() const;"): "metal::MeshRenderPipelineDescriptor::is_alpha_to_coverage_enabled",
        ("MTL::MeshRenderPipelineDescriptor", "deprecated", "[[deprecated( )]] bool alphaToOneEnabled() const;"): "metal::MeshRenderPipelineDescriptor::is_alpha_to_one_enabled",
        ("MTL::MeshRenderPipelineDescriptor", "deprecated", "[[deprecated( )]] bool rasterizationEnabled() const;"): "metal::MeshRenderPipelineDescriptor::is_rasterization_enabled",
        ("MTL4::MeshRenderPipelineDescriptor", "deprecated", "[[deprecated( )]] bool rasterizationEnabled() const;"): "metal4::MeshRenderPipelineDescriptor::is_rasterization_enabled",
        ("MTL4::RenderPipelineDescriptor", "deprecated", "[[deprecated( )]] bool rasterizationEnabled() const;"): "metal4::RenderPipelineDescriptor::is_rasterization_enabled",
    }
)

# Device pipeline and library overloads converge on owned reflection tuples and
# panic-isolated Rust callbacks. Exact signatures keep unrelated overloads out.
ACTUAL_METHOD_SIGNATURES.update(
    {
        ("MTL::Device", "newComputePipelineState", "ComputePipelineState* newComputePipelineState(const MTL::Function* computeFunction, MTL::PipelineOption options, const MTL::AutoreleasedComputePipelineReflection* reflection, NS::Error** error);"): "metal::Device::new_compute_pipeline_with_reflection",
        ("MTL::Device", "newComputePipelineState", "void newComputePipelineState(const MTL::Function* computeFunction, const MTL::NewComputePipelineStateCompletionHandler completionHandler);"): "metal::Device::new_compute_pipeline_async",
        ("MTL::Device", "newComputePipelineState", "void newComputePipelineState(const MTL::Function* computeFunction, MTL::PipelineOption options, const MTL::NewComputePipelineStateWithReflectionCompletionHandler completionHandler);"): "metal::Device::new_compute_pipeline_with_reflection_async",
        ("MTL::Device", "newComputePipelineState", "ComputePipelineState* newComputePipelineState(const MTL::ComputePipelineDescriptor* descriptor, MTL::PipelineOption options, const MTL::AutoreleasedComputePipelineReflection* reflection, NS::Error** error);"): "metal::Device::new_compute_pipeline_from_descriptor",
        ("MTL::Device", "newComputePipelineState", "void newComputePipelineState(const MTL::ComputePipelineDescriptor* descriptor, MTL::PipelineOption options, const MTL::NewComputePipelineStateWithReflectionCompletionHandler completionHandler);"): "metal::Device::new_compute_pipeline_from_descriptor_async",
        ("MTL::Device", "newComputePipelineState", "void newComputePipelineState(const MTL::Function* pFunction, const MTL::NewComputePipelineStateCompletionHandlerFunction& completionHandler);"): "metal::Device::new_compute_pipeline_async",
        ("MTL::Device", "newComputePipelineState", "void newComputePipelineState(const MTL::Function* pFunction, MTL::PipelineOption options, const MTL::NewComputePipelineStateWithReflectionCompletionHandlerFunction& completionHandler);"): "metal::Device::new_compute_pipeline_with_reflection_async",
        ("MTL::Device", "newComputePipelineState", "void newComputePipelineState(const MTL::ComputePipelineDescriptor* pDescriptor, MTL::PipelineOption options, const MTL::NewComputePipelineStateWithReflectionCompletionHandlerFunction& completionHandler);"): "metal::Device::new_compute_pipeline_from_descriptor_async",
        ("MTL::Device", "newRenderPipelineState", "RenderPipelineState* newRenderPipelineState(const MTL::RenderPipelineDescriptor* descriptor, MTL::PipelineOption options, const MTL::AutoreleasedRenderPipelineReflection* reflection, NS::Error** error);"): "metal::Device::new_render_pipeline_with_reflection",
        ("MTL::Device", "newRenderPipelineState", "void newRenderPipelineState(const MTL::RenderPipelineDescriptor* descriptor, const MTL::NewRenderPipelineStateCompletionHandler completionHandler);"): "metal::Device::new_render_pipeline_async",
        ("MTL::Device", "newRenderPipelineState", "void newRenderPipelineState(const MTL::RenderPipelineDescriptor* descriptor, MTL::PipelineOption options, const MTL::NewRenderPipelineStateWithReflectionCompletionHandler completionHandler);"): "metal::Device::new_render_pipeline_with_reflection_async",
        ("MTL::Device", "newRenderPipelineState", "RenderPipelineState* newRenderPipelineState(const MTL::TileRenderPipelineDescriptor* descriptor, MTL::PipelineOption options, const MTL::AutoreleasedRenderPipelineReflection* reflection, NS::Error** error);"): "metal::Device::new_tile_render_pipeline_with_reflection",
        ("MTL::Device", "newRenderPipelineState", "void newRenderPipelineState(const MTL::TileRenderPipelineDescriptor* descriptor, MTL::PipelineOption options, const MTL::NewRenderPipelineStateWithReflectionCompletionHandler completionHandler);"): "metal::Device::new_tile_render_pipeline_with_reflection_async",
        ("MTL::Device", "newRenderPipelineState", "RenderPipelineState* newRenderPipelineState(const MTL::MeshRenderPipelineDescriptor* descriptor, MTL::PipelineOption options, const MTL::AutoreleasedRenderPipelineReflection* reflection, NS::Error** error);"): "metal::Device::new_mesh_render_pipeline_with_reflection",
        ("MTL::Device", "newRenderPipelineState", "void newRenderPipelineState(const MTL::MeshRenderPipelineDescriptor* descriptor, MTL::PipelineOption options, const MTL::NewRenderPipelineStateWithReflectionCompletionHandler completionHandler);"): "metal::Device::new_mesh_render_pipeline_with_reflection_async",
        ("MTL::Device", "newRenderPipelineState", "void newRenderPipelineState(const MTL::RenderPipelineDescriptor* pDescriptor, const MTL::NewRenderPipelineStateCompletionHandlerFunction& completionHandler);"): "metal::Device::new_render_pipeline_async",
        ("MTL::Device", "newRenderPipelineState", "void newRenderPipelineState(const MTL::RenderPipelineDescriptor* pDescriptor, MTL::PipelineOption options, const MTL::NewRenderPipelineStateWithReflectionCompletionHandlerFunction& completionHandler);"): "metal::Device::new_render_pipeline_with_reflection_async",
        ("MTL::Device", "newRenderPipelineState", "void newRenderPipelineState(const MTL::TileRenderPipelineDescriptor* pDescriptor, MTL::PipelineOption options, const MTL::NewRenderPipelineStateWithReflectionCompletionHandlerFunction& completionHandler);"): "metal::Device::new_tile_render_pipeline_with_reflection_async",
        ("MTL::Device", "newLibrary", "Library* newLibrary(const NS::String* filepath, NS::Error** error);"): "metal::Device::new_library_from_path",
        ("MTL::Device", "newLibrary", "Library* newLibrary(const NS::URL* url, NS::Error** error);"): "metal::Device::new_library_from_path",
        ("MTL::Device", "newLibrary", "void newLibrary(const NS::String* source, const MTL::CompileOptions* options, const MTL::NewLibraryCompletionHandler completionHandler);"): "metal::Device::new_library_from_source_async",
        ("MTL::Device", "newLibrary", "Library* newLibrary(const MTL::StitchedLibraryDescriptor* descriptor, NS::Error** error);"): "metal::Device::new_stitched_library",
        ("MTL::Device", "newLibrary", "void newLibrary(const MTL::StitchedLibraryDescriptor* descriptor, const MTL::NewLibraryCompletionHandler completionHandler);"): "metal::Device::new_stitched_library_async",
        ("MTL::Device", "newLibrary", "void newLibrary(const NS::String* pSource, const MTL::CompileOptions* pOptions, const MTL::NewLibraryCompletionHandlerFunction& completionHandler);"): "metal::Device::new_library_from_source_async",
        ("MTL::Device", "newLibrary", "void newLibrary(const MTL::StitchedLibraryDescriptor* pDescriptor, const MTL::NewLibraryCompletionHandlerFunction& completionHandler);"): "metal::Device::new_stitched_library_async",
        ("MTL::Device", "newDynamicLibrary", "DynamicLibrary* newDynamicLibrary(const NS::URL* url, NS::Error** error);"): "metal::Device::new_dynamic_library_from_path",
        ("MTL::Device", "newLogState", "LogState* newLogState(const MTL::LogStateDescriptor* descriptor, NS::Error** error);"): "metal::Device::new_log_state",
        ("MTL::Device", "newCounterHeap", "MTL4::CounterHeap* newCounterHeap(const MTL4::CounterHeapDescriptor* descriptor, NS::Error** error);"): "metal::Device::new_timestamp_counter_heap",
        ("MTL::Device", "newBuffer", "Buffer* newBuffer(const void* pointer, NS::UInteger length, MTL::ResourceOptions options, void (^deallocator)(void*, NS::UInteger));"): "metal::Device::new_buffer_with_bytes",
    }
)

# Metal 4 archive lookup and argument-table bindings are selector gated.  The
# argument-table facade deliberately accepts typed resources instead of raw
# GPU addresses or ResourceID values.
ACTUAL_METHOD_SIGNATURES.update(
    {
        (
            "MTL::Device",
            "newArgumentTable",
            "MTL4::ArgumentTable* newArgumentTable(const MTL4::ArgumentTableDescriptor* descriptor, NS::Error** error);",
        ): "metal::Device::new_mtl4_argument_table",
        (
            "MTL4::Archive",
            "newBinaryFunction",
            "BinaryFunction* newBinaryFunction(const MTL4::BinaryFunctionDescriptor* descriptor, NS::Error** error);",
        ): "metal4::Archive::new_binary_function",
        (
            "MTL4::Archive",
            "newComputePipelineState",
            "MTL::ComputePipelineState* newComputePipelineState(const MTL4::ComputePipelineDescriptor* descriptor, NS::Error** error);",
        ): "metal4::Archive::new_compute_pipeline_state",
        (
            "MTL4::Archive",
            "newComputePipelineState",
            "MTL::ComputePipelineState* newComputePipelineState(const MTL4::ComputePipelineDescriptor* descriptor, const MTL4::PipelineStageDynamicLinkingDescriptor* dynamicLinkingDescriptor, NS::Error** error);",
        ): "metal4::Archive::new_compute_pipeline_state",
        (
            "MTL4::Archive",
            "newRenderPipelineState",
            "MTL::RenderPipelineState* newRenderPipelineState(const MTL4::PipelineDescriptor* descriptor, NS::Error** error);",
        ): "metal4::Archive::new_render_pipeline_state",
        (
            "MTL4::Archive",
            "newRenderPipelineState",
            "MTL::RenderPipelineState* newRenderPipelineState(const MTL4::PipelineDescriptor* descriptor, const MTL4::RenderPipelineDynamicLinkingDescriptor* dynamicLinkingDescriptor, NS::Error** error);",
        ): "metal4::Archive::new_render_pipeline_state",
        (
            "MTL4::ArgumentTable",
            "setAddress",
            "void setAddress(MTL::GPUAddress gpuAddress, NS::UInteger bindingIndex);",
        ): "metal4::ArgumentTable::set_buffer",
        (
            "MTL4::ArgumentTable",
            "setAddress",
            "void setAddress(MTL::GPUAddress gpuAddress, NS::UInteger stride, NS::UInteger bindingIndex);",
        ): "metal4::ArgumentTable::set_buffer_with_stride",
        (
            "MTL4::ArgumentTable",
            "setResource",
            "void setResource(MTL::ResourceID resourceID, NS::UInteger bindingIndex);",
        ): "metal4::ArgumentTable::set_resource",
        (
            "MTL4::ArgumentTable",
            "setSamplerState",
            "void setSamplerState(MTL::ResourceID resourceID, NS::UInteger bindingIndex);",
        ): "metal4::ArgumentTable::set_sampler_state",
        (
            "MTL4::ArgumentTable",
            "setTexture",
            "void setTexture(MTL::ResourceID resourceID, NS::UInteger bindingIndex);",
        ): "metal4::ArgumentTable::set_texture",
    }
)

ACTUAL_METHODS.update(
    {
        ("MTL::StructMember", "arrayType"): "metal::StructMember::array_type",
        ("MTL::StructMember", "pointerType"): "metal::StructMember::pointer_type",
        ("MTL::StructMember", "structType"): "metal::StructMember::struct_type",
        ("MTL::StructMember", "tensorReferenceType"): "metal::StructMember::tensor_reference_type",
        ("MTL::StructMember", "textureReferenceType"): "metal::StructMember::texture_reference_type",
        ("MTL::StructType", "memberByName"): "metal::StructType::member_by_name",
        ("MTL::StructType", "members"): "metal::StructType::members",
        ("MTL::ArrayType", "elementArrayType"): "metal::ArrayType::element_array_type",
        ("MTL::ArrayType", "elementPointerType"): "metal::ArrayType::element_pointer_type",
        ("MTL::ArrayType", "elementStructType"): "metal::ArrayType::element_struct_type",
        ("MTL::ArrayType", "elementTensorReferenceType"): "metal::ArrayType::element_tensor_reference_type",
        ("MTL::ArrayType", "elementTextureReferenceType"): "metal::ArrayType::element_texture_reference_type",
        ("MTL::PointerType", "elementArrayType"): "metal::PointerType::element_array_type",
        ("MTL::PointerType", "elementStructType"): "metal::PointerType::element_struct_type",
        ("MTL::TensorReferenceType", "auxiliaryPlanes"): "metal::TensorReferenceType::auxiliary_planes",
        ("MTL::TensorBinding", "auxiliaryPlanes"): "metal::TensorBinding::auxiliary_planes",
        ("MTL::TextureViewDescriptor", "levelRange"): "metal::TextureViewDescriptor::level_range",
        ("MTL::TextureViewDescriptor", "setLevelRange"): "metal::TextureViewDescriptor::set_level_range",
        ("MTL::TextureViewDescriptor", "sliceRange"): "metal::TextureViewDescriptor::slice_range",
        ("MTL::TextureViewDescriptor", "setSliceRange"): "metal::TextureViewDescriptor::set_slice_range",
        ("MTL::TextureViewDescriptor", "swizzle"): "metal::TextureViewDescriptor::swizzle",
        ("MTL::TextureViewDescriptor", "setSwizzle"): "metal::TextureViewDescriptor::set_swizzle",
    }
)

ACTUAL_METHOD_SIGNATURES.update(
    {
        ("MTL::Argument", "deprecated", "[[deprecated( )]] bool active() const;"): "metal::Argument::is_active",
        ("MTL::Binding", "deprecated", "[[deprecated( )]] bool argument() const;"): "metal::Binding::is_argument",
        ("MTL::Binding", "deprecated", "[[deprecated( )]] bool used() const;"): "metal::Binding::is_used",
        ("MTL::TextureBinding", "deprecated", "[[deprecated( )]] bool depthTexture() const;"): "metal::TextureBinding::is_depth_texture",
    }
)

ACTUAL_METHODS.update(
    {
        ("MTL4::CompilerTaskOptions", "lookupArchives"): "metal4::CompilerTaskOptions::lookup_archives_vec",
        ("MTL4::CompilerTaskOptions", "setLookupArchives"): "metal4::CompilerTaskOptions::set_lookup_archives_slice",
        ("MTL4::StaticLinkingDescriptor", "functionDescriptors"): "metal4::StaticLinkingDescriptor::function_descriptors_vec",
        ("MTL4::StaticLinkingDescriptor", "setFunctionDescriptors"): "metal4::StaticLinkingDescriptor::set_function_descriptors_slice",
        ("MTL4::StaticLinkingDescriptor", "groups"): "metal4::StaticLinkingDescriptor::groups_map",
        ("MTL4::StaticLinkingDescriptor", "setGroups"): "metal4::StaticLinkingDescriptor::set_groups_map",
        ("MTL4::PipelineStageDynamicLinkingDescriptor", "binaryLinkedFunctions"): "metal4::PipelineStageDynamicLinkingDescriptor::binary_linked_functions_vec",
        ("MTL4::PipelineStageDynamicLinkingDescriptor", "setBinaryLinkedFunctions"): "metal4::PipelineStageDynamicLinkingDescriptor::set_binary_linked_functions_slice",
        ("MTL4::PipelineStageDynamicLinkingDescriptor", "preloadedLibraries"): "metal4::PipelineStageDynamicLinkingDescriptor::preloaded_libraries_vec",
        ("MTL4::PipelineStageDynamicLinkingDescriptor", "setPreloadedLibraries"): "metal4::PipelineStageDynamicLinkingDescriptor::set_preloaded_libraries_slice",
        ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "fragmentAdditionalBinaryFunctions"): "metal4::RenderPipelineBinaryFunctionsDescriptor::fragment_additional_binary_functions_vec",
        ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "setFragmentAdditionalBinaryFunctions"): "metal4::RenderPipelineBinaryFunctionsDescriptor::set_fragment_additional_binary_functions_slice",
        ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "meshAdditionalBinaryFunctions"): "metal4::RenderPipelineBinaryFunctionsDescriptor::mesh_additional_binary_functions_vec",
        ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "setMeshAdditionalBinaryFunctions"): "metal4::RenderPipelineBinaryFunctionsDescriptor::set_mesh_additional_binary_functions_slice",
        ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "objectAdditionalBinaryFunctions"): "metal4::RenderPipelineBinaryFunctionsDescriptor::object_additional_binary_functions_vec",
        ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "setObjectAdditionalBinaryFunctions"): "metal4::RenderPipelineBinaryFunctionsDescriptor::set_object_additional_binary_functions_slice",
        ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "tileAdditionalBinaryFunctions"): "metal4::RenderPipelineBinaryFunctionsDescriptor::tile_additional_binary_functions_vec",
        ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "setTileAdditionalBinaryFunctions"): "metal4::RenderPipelineBinaryFunctionsDescriptor::set_tile_additional_binary_functions_slice",
        ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "vertexAdditionalBinaryFunctions"): "metal4::RenderPipelineBinaryFunctionsDescriptor::vertex_additional_binary_functions_vec",
        ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "setVertexAdditionalBinaryFunctions"): "metal4::RenderPipelineBinaryFunctionsDescriptor::set_vertex_additional_binary_functions_slice",
        ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "reset"): "metal4::RenderPipelineBinaryFunctionsDescriptor::reset_safe",
        ("MTL4::RenderPipelineColorAttachmentDescriptor", "reset"): "metal4::RenderPipelineColorAttachmentDescriptor::reset_safe",
        ("MTL4::RenderPipelineColorAttachmentDescriptorArray", "object"): "metal4::RenderPipelineColorAttachmentDescriptorArray::attachment",
        ("MTL4::RenderPipelineColorAttachmentDescriptorArray", "setObject"): "metal4::RenderPipelineColorAttachmentDescriptorArray::set_attachment",
        ("MTL4::RenderPipelineColorAttachmentDescriptorArray", "reset"): "metal4::RenderPipelineColorAttachmentDescriptorArray::reset_safe",
        ("MTL4::RenderPipelineDescriptor", "reset"): "metal4::RenderPipelineDescriptor::reset_safe",
    }
)

ACTUAL_METHODS.update(
    {
        ("MTL::Drawable", "drawableID"): "metal::Drawable::drawable_id",
        ("MTL::Drawable", "present"): "metal::Drawable::present",
        ("MTL::Drawable", "presentAfterMinimumDuration"): "metal::Drawable::present_after_minimum_duration",
        ("MTL::Drawable", "presentAtTime"): "metal::Drawable::present_at_time",
        ("MTL::Drawable", "presentedTime"): "metal::Drawable::validated_presented_time",
        ("MTL::SharedEvent", "newSharedEventHandle"): "metal::SharedEvent::new_shared_event_handle",
        ("MTL::SharedEvent", "waitUntilSignaledValue"): "metal::SharedEvent::wait_until_signaled_value",
        ("MTL::SharedEventListener", "alloc"): "metal::SharedEventListener::new",
        ("MTL::SharedEventListener", "dispatchQueue"): "metal::SharedEventListener::shared",
        ("MTL::SharedEventListener", "sharedListener"): "metal::SharedEventListener::shared",
    }
)

ACTUAL_METHOD_SIGNATURES.update(
    {
        ("MTL::Drawable", "addPresentedHandler", "void addPresentedHandler(const MTL::DrawablePresentedHandler block);"): "metal::Drawable::on_presented",
        ("MTL::Drawable", "addPresentedHandler", "void addPresentedHandler(const MTL::DrawablePresentedHandlerFunction& function);"): "metal::Drawable::on_presented",
        ("MTL::SharedEvent", "notifyListener", "void notifyListener(const MTL::SharedEventListener* listener, uint64_t value, const MTL::SharedEventNotificationBlock block);"): "metal::SharedEvent::notify_at",
        ("MTL::SharedEvent", "notifyListener", "void notifyListener(const MTL::SharedEventListener* listener, uint64_t value, const MTL::SharedEventNotificationFunction& function);"): "metal::SharedEvent::notify_at",
        ("MTL::SharedEventListener", "init", "SharedEventListener* init();"): "metal::SharedEventListener::new",
        ("MTL::SharedEventListener", "init", "SharedEventListener* init(const dispatch_queue_t dispatchQueue);"): "metal::SharedEventListener::new",
    }
)

ACTUAL_METHODS.update(
    {
        ("MTL4::CommandQueue", "label"): "metal4::CommandQueue::label",
        ("MTL4::CommandQueue", "addResidencySet"): "metal4::CommandQueue::add_residency_set",
        ("MTL4::CommandQueue", "addResidencySets"): "metal4::CommandQueue::add_residency_sets",
        ("MTL4::CommandQueue", "removeResidencySet"): "metal4::CommandQueue::remove_residency_set",
        ("MTL4::CommandQueue", "removeResidencySets"): "metal4::CommandQueue::remove_residency_sets",
        ("MTL4::CommandQueue", "signalEvent"): "metal4::CommandQueue::signal_event",
        ("MTL4::CommandQueue", "signalDrawable"): "metal4::CommandQueue::signal_drawable",
        ("MTL4::CommandBuffer", "computeCommandEncoder"): "metal4::RecordingCommandBuffer::compute_encoder",
        ("MTL4::CommandBuffer", "device"): "metal4::AvailableCommandBuffer::device",
        ("MTL4::CommandBuffer", "endCommandBuffer"): "metal4::RecordingCommandBuffer::end",
        ("MTL4::CommandBuffer", "label"): "metal4::AvailableCommandBuffer::label",
        ("MTL4::CommandBuffer", "machineLearningCommandEncoder"): "metal4::RecordingCommandBuffer::machine_learning_encoder",
        ("MTL4::CommandBuffer", "popDebugGroup"): "metal4::RecordingCommandBuffer::pop_debug_group",
        ("MTL4::CommandBuffer", "pushDebugGroup"): "metal4::RecordingCommandBuffer::push_debug_group",
        ("MTL4::CommandBuffer", "setLabel"): "metal4::AvailableCommandBuffer::set_label",
        ("MTL4::CommandBuffer", "useResidencySet"): "metal4::RecordingCommandBuffer::use_residency_set",
        ("MTL4::CommandBuffer", "useResidencySets"): "metal4::RecordingCommandBuffer::use_residency_sets",
        ("MTL4::CommandEncoder", "barrierAfterEncoderStages"): "metal4::RecordingComputeEncoder::barrier_after_encoder_stages",
        ("MTL4::CommandEncoder", "barrierAfterQueueStages"): "metal4::RecordingComputeEncoder::barrier_after_queue_stages",
        ("MTL4::CommandEncoder", "barrierAfterStages"): "metal4::RecordingComputeEncoder::barrier_after_stages",
        ("MTL4::CommandEncoder", "endEncoding"): "metal4::RecordingComputeEncoder::end",
        ("MTL4::CommandEncoder", "insertDebugSignpost"): "metal4::RecordingComputeEncoder::insert_debug_signpost",
        ("MTL4::CommandEncoder", "label"): "metal4::RecordingComputeEncoder::label",
        ("MTL4::CommandEncoder", "popDebugGroup"): "metal4::RecordingComputeEncoder::pop_debug_group",
        ("MTL4::CommandEncoder", "pushDebugGroup"): "metal4::RecordingComputeEncoder::push_debug_group",
        ("MTL4::CommandEncoder", "setLabel"): "metal4::RecordingComputeEncoder::set_label",
        ("MTL4::CommandEncoder", "updateFence"): "metal4::RecordingComputeEncoder::update_fence",
        ("MTL4::CommandEncoder", "waitForFence"): "metal4::RecordingComputeEncoder::wait_for_fence",
        ("MTL4::RenderCommandEncoder", "setArgumentTable"): "metal4::RecordingRenderEncoder::set_argument_table",
        ("MTL4::RenderCommandEncoder", "setBlendColor"): "metal4::RecordingRenderEncoder::set_blend_color",
        ("MTL4::RenderCommandEncoder", "setColorStoreAction"): "metal4::RecordingRenderEncoder::set_color_store_action",
        ("MTL4::RenderCommandEncoder", "setCullMode"): "metal4::RecordingRenderEncoder::set_cull_mode",
        ("MTL4::RenderCommandEncoder", "setDepthBias"): "metal4::RecordingRenderEncoder::set_depth_bias",
        ("MTL4::RenderCommandEncoder", "setDepthClipMode"): "metal4::RecordingRenderEncoder::set_depth_clip_mode",
        ("MTL4::RenderCommandEncoder", "setDepthStencilState"): "metal4::RecordingRenderEncoder::set_depth_stencil_state",
        ("MTL4::RenderCommandEncoder", "setDepthStoreAction"): "metal4::RecordingRenderEncoder::set_depth_store_action",
        ("MTL4::RenderCommandEncoder", "setDepthTestBounds"): "metal4::RecordingRenderEncoder::set_depth_test_bounds",
        ("MTL4::RenderCommandEncoder", "setFrontFacingWinding"): "metal4::RecordingRenderEncoder::set_front_facing_winding",
        ("MTL4::RenderCommandEncoder", "setObjectThreadgroupMemoryLength"): "metal4::RecordingRenderEncoder::set_object_threadgroup_memory_length",
        ("MTL4::RenderCommandEncoder", "setRenderPipelineState"): "metal4::RecordingRenderEncoder::set_render_pipeline_state",
        ("MTL4::RenderCommandEncoder", "setStencilReferenceValue"): "metal4::RecordingRenderEncoder::set_stencil_reference_value",
        ("MTL4::RenderCommandEncoder", "setStencilReferenceValues"): "metal4::RecordingRenderEncoder::set_stencil_reference_values",
        ("MTL4::RenderCommandEncoder", "setStencilStoreAction"): "metal4::RecordingRenderEncoder::set_stencil_store_action",
        ("MTL4::RenderCommandEncoder", "setThreadgroupMemoryLength"): "metal4::RecordingRenderEncoder::set_threadgroup_memory_length",
        ("MTL4::RenderCommandEncoder", "setTriangleFillMode"): "metal4::RecordingRenderEncoder::set_triangle_fill_mode",
        ("MTL4::RenderCommandEncoder", "setViewport"): "metal4::RecordingRenderEncoder::set_viewport",
        ("MTL4::RenderCommandEncoder", "setVisibilityResultMode"): "metal4::RecordingRenderEncoder::set_visibility_result_mode",
        ("MTL4::ComputeCommandEncoder", "setArgumentTable"): "metal4::RecordingComputeEncoder::set_argument_table",
        ("MTL4::ComputeCommandEncoder", "setComputePipelineState"): "metal4::RecordingComputeEncoder::set_compute_pipeline_state",
        ("MTL4::ComputeCommandEncoder", "setImageblockWidth"): "metal4::RecordingComputeEncoder::set_imageblock_size",
        ("MTL4::ComputeCommandEncoder", "setThreadgroupMemoryLength"): "metal4::RecordingComputeEncoder::set_threadgroup_memory_length",
        ("MTL4::ComputeCommandEncoder", "stages"): "metal4::RecordingComputeEncoder::stages",
    }
)

ACTUAL_METHOD_SIGNATURES.update(
    {
        ("MTL4::CommandQueue", "commit", "void commit(const MTL4::CommandBuffer* const commandBuffers[], NS::UInteger count);"): "metal4::CommandQueue::submit",
        ("MTL4::CommandQueue", "commit", "void commit(const MTL4::CommandBuffer* const commandBuffers[], NS::UInteger count, const MTL4::CommitOptions* options);"): "metal4::CommandQueue::submit",
        ("MTL4::CommandQueue", "wait", "void wait(const MTL::Event* event, uint64_t value);"): "metal4::CommandQueue::wait_for_event",
        ("MTL4::CommandQueue", "wait", "void wait(const MTL::Drawable* drawable);"): "metal4::CommandQueue::wait_for_drawable",
        ("MTL4::CommandBuffer", "beginCommandBuffer", "void beginCommandBuffer(const MTL4::CommandAllocator* allocator);"): "metal4::AvailableCommandBuffer::begin",
        ("MTL4::CommandBuffer", "beginCommandBuffer", "void beginCommandBuffer(const MTL4::CommandAllocator* allocator, const MTL4::CommandBufferOptions* options);"): "metal4::AvailableCommandBuffer::begin",
        ("MTL4::CommandBuffer", "renderCommandEncoder", "RenderCommandEncoder* renderCommandEncoder(const MTL4::RenderPassDescriptor* descriptor);"): "metal4::RecordingCommandBuffer::render_encoder",
        ("MTL4::CommandBuffer", "renderCommandEncoder", "RenderCommandEncoder* renderCommandEncoder(const MTL4::RenderPassDescriptor* descriptor, MTL4::RenderEncoderOptions options);"): "metal4::RecordingCommandBuffer::render_encoder",
        ("MTL4::RenderCommandEncoder", "drawPrimitives", "void drawPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger vertexStart, NS::UInteger vertexCount);"): "metal4::RecordingRenderEncoder::draw_primitives",
        ("MTL4::RenderCommandEncoder", "drawPrimitives", "void drawPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger vertexStart, NS::UInteger vertexCount, NS::UInteger instanceCount);"): "metal4::RecordingRenderEncoder::draw_primitives_instanced",
        ("MTL4::RenderCommandEncoder", "drawPrimitives", "void drawPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger vertexStart, NS::UInteger vertexCount, NS::UInteger instanceCount, NS::UInteger baseInstance);"): "metal4::RecordingRenderEncoder::draw_primitives_instanced_base_instance",
        ("MTL4::ComputeCommandEncoder", "dispatchThreadgroups", "void dispatchThreadgroups(MTL::Size threadgroupsPerGrid, MTL::Size threadsPerThreadgroup);"): "metal4::RecordingComputeEncoder::dispatch_threadgroups",
        ("MTL4::ComputeCommandEncoder", "dispatchThreads", "void dispatchThreads(MTL::Size threadsPerGrid, MTL::Size threadsPerThreadgroup);"): "metal4::RecordingComputeEncoder::dispatch_threads",
        ("MTL::Device", "newCommandBuffer", "MTL4::CommandBuffer* newCommandBuffer();"): "metal::Device::new_mtl4_command_buffer",
        ("MTL::Device", "newMTL4CommandQueue", "MTL4::CommandQueue* newMTL4CommandQueue();"): "metal::Device::new_mtl4_command_queue",
    }
)

ACTUAL_METHOD_SIGNATURES.update(
    {
        ("MTL4::Compiler", "newBinaryFunction", "BinaryFunction* newBinaryFunction(const MTL4::BinaryFunctionDescriptor* descriptor, const MTL4::CompilerTaskOptions* compilerTaskOptions, NS::Error** error);"): "metal4::Compiler::new_binary_function",
        ("MTL4::Compiler", "newBinaryFunction", "CompilerTask* newBinaryFunction(const MTL4::BinaryFunctionDescriptor* descriptor, const MTL4::CompilerTaskOptions* compilerTaskOptions, const MTL4::NewBinaryFunctionCompletionHandler completionHandler);"): "metal4::Compiler::new_binary_function_async",
        ("MTL4::Compiler", "newComputePipelineState", "MTL::ComputePipelineState* newComputePipelineState(const MTL4::ComputePipelineDescriptor* descriptor, const MTL4::CompilerTaskOptions* compilerTaskOptions, NS::Error** error);"): "metal4::Compiler::new_compute_pipeline",
        ("MTL4::Compiler", "newComputePipelineState", "MTL::ComputePipelineState* newComputePipelineState(const MTL4::ComputePipelineDescriptor* descriptor, const MTL4::PipelineStageDynamicLinkingDescriptor* dynamicLinkingDescriptor, const MTL4::CompilerTaskOptions* compilerTaskOptions, NS::Error** error);"): "metal4::Compiler::new_compute_pipeline",
        ("MTL4::Compiler", "newComputePipelineState", "CompilerTask* newComputePipelineState(const MTL4::ComputePipelineDescriptor* descriptor, const MTL4::CompilerTaskOptions* compilerTaskOptions, const MTL::NewComputePipelineStateCompletionHandler completionHandler);"): "metal4::Compiler::new_compute_pipeline_async",
        ("MTL4::Compiler", "newComputePipelineState", "CompilerTask* newComputePipelineState(const MTL4::ComputePipelineDescriptor* descriptor, const MTL4::PipelineStageDynamicLinkingDescriptor* dynamicLinkingDescriptor, const MTL4::CompilerTaskOptions* compilerTaskOptions, const MTL::NewComputePipelineStateCompletionHandler completionHandler);"): "metal4::Compiler::new_compute_pipeline_linked_async",
        ("MTL4::Compiler", "newComputePipelineState", "CompilerTask* newComputePipelineState(const MTL4::ComputePipelineDescriptor* pDescriptor, const MTL4::CompilerTaskOptions* options, const MTL4::NewComputePipelineStateCompletionHandlerFunction& function);"): "metal4::Compiler::new_compute_pipeline_async",
        ("MTL4::Compiler", "newDynamicLibrary", "MTL::DynamicLibrary* newDynamicLibrary(const MTL::Library* library, NS::Error** error);"): "metal4::Compiler::new_dynamic_library",
        ("MTL4::Compiler", "newDynamicLibrary", "MTL::DynamicLibrary* newDynamicLibrary(const NS::URL* url, NS::Error** error);"): "metal4::Compiler::new_dynamic_library_from_path",
        ("MTL4::Compiler", "newDynamicLibrary", "CompilerTask* newDynamicLibrary(const MTL::Library* library, const MTL::NewDynamicLibraryCompletionHandler completionHandler);"): "metal4::Compiler::new_dynamic_library_async",
        ("MTL4::Compiler", "newDynamicLibrary", "CompilerTask* newDynamicLibrary(const NS::URL* url, const MTL::NewDynamicLibraryCompletionHandler completionHandler);"): "metal4::Compiler::new_dynamic_library_from_path_async",
        ("MTL4::Compiler", "newDynamicLibrary", "CompilerTask* newDynamicLibrary(const MTL::Library* pLibrary, const MTL::NewDynamicLibraryCompletionHandlerFunction& function);"): "metal4::Compiler::new_dynamic_library_async",
        ("MTL4::Compiler", "newDynamicLibrary", "CompilerTask* newDynamicLibrary(const NS::URL* pURL, const MTL::NewDynamicLibraryCompletionHandlerFunction& function);"): "metal4::Compiler::new_dynamic_library_from_path_async",
        ("MTL4::Compiler", "newLibrary", "MTL::Library* newLibrary(const MTL4::LibraryDescriptor* descriptor, NS::Error** error);"): "metal4::Compiler::new_library",
        ("MTL4::Compiler", "newLibrary", "CompilerTask* newLibrary(const MTL4::LibraryDescriptor* descriptor, const MTL::NewLibraryCompletionHandler completionHandler);"): "metal4::Compiler::new_library_async",
        ("MTL4::Compiler", "newLibrary", "CompilerTask* newLibrary(const MTL4::LibraryDescriptor* pDescriptor, const MTL::NewLibraryCompletionHandlerFunction& function);"): "metal4::Compiler::new_library_async",
        ("MTL4::Compiler", "newMachineLearningPipelineState", "MachineLearningPipelineState* newMachineLearningPipelineState(const MTL4::MachineLearningPipelineDescriptor* descriptor, NS::Error** error);"): "metal4::Compiler::new_machine_learning_pipeline",
        ("MTL4::Compiler", "newMachineLearningPipelineState", "CompilerTask* newMachineLearningPipelineState(const MTL4::MachineLearningPipelineDescriptor* descriptor, const MTL4::NewMachineLearningPipelineStateCompletionHandler completionHandler);"): "metal4::Compiler::new_machine_learning_pipeline_async",
        ("MTL4::Compiler", "newMachineLearningPipelineState", "CompilerTask* newMachineLearningPipelineState(const MTL4::MachineLearningPipelineDescriptor* pDescriptor, const MTL4::NewMachineLearningPipelineStateCompletionHandlerFunction& function);"): "metal4::Compiler::new_machine_learning_pipeline_async",
        ("MTL4::Compiler", "newRenderPipelineState", "MTL::RenderPipelineState* newRenderPipelineState(const MTL4::PipelineDescriptor* descriptor, const MTL4::CompilerTaskOptions* compilerTaskOptions, NS::Error** error);"): "metal4::Compiler::new_render_pipeline",
        ("MTL4::Compiler", "newRenderPipelineState", "MTL::RenderPipelineState* newRenderPipelineState(const MTL4::PipelineDescriptor* descriptor, const MTL4::RenderPipelineDynamicLinkingDescriptor* dynamicLinkingDescriptor, const MTL4::CompilerTaskOptions* compilerTaskOptions, NS::Error** error);"): "metal4::Compiler::new_render_pipeline",
        ("MTL4::Compiler", "newRenderPipelineState", "CompilerTask* newRenderPipelineState(const MTL4::PipelineDescriptor* descriptor, const MTL4::CompilerTaskOptions* compilerTaskOptions, const MTL::NewRenderPipelineStateCompletionHandler completionHandler);"): "metal4::Compiler::new_render_pipeline_async",
        ("MTL4::Compiler", "newRenderPipelineState", "CompilerTask* newRenderPipelineState(const MTL4::PipelineDescriptor* descriptor, const MTL4::RenderPipelineDynamicLinkingDescriptor* dynamicLinkingDescriptor, const MTL4::CompilerTaskOptions* compilerTaskOptions, const MTL::NewRenderPipelineStateCompletionHandler completionHandler);"): "metal4::Compiler::new_render_pipeline_linked_async",
        ("MTL4::Compiler", "newRenderPipelineState", "CompilerTask* newRenderPipelineState(const MTL4::PipelineDescriptor* pDescriptor, const MTL4::CompilerTaskOptions* options, const MTL4::NewRenderPipelineStateCompletionHandlerFunction& function);"): "metal4::Compiler::new_render_pipeline_async",
        ("MTL4::Compiler", "newRenderPipelineStateBySpecialization", "MTL::RenderPipelineState* newRenderPipelineStateBySpecialization(const MTL4::PipelineDescriptor* descriptor, const MTL::RenderPipelineState* pipeline, NS::Error** error);"): "metal4::Compiler::specialize_render_pipeline",
        ("MTL4::Compiler", "newRenderPipelineStateBySpecialization", "CompilerTask* newRenderPipelineStateBySpecialization(const MTL4::PipelineDescriptor* descriptor, const MTL::RenderPipelineState* pipeline, const MTL::NewRenderPipelineStateCompletionHandler completionHandler);"): "metal4::Compiler::specialize_render_pipeline_async",
        ("MTL4::Compiler", "newRenderPipelineStateBySpecialization", "CompilerTask* newRenderPipelineStateBySpecialization(const MTL4::PipelineDescriptor* pDescriptor, const MTL::RenderPipelineState* pPipeline, const MTL4::NewRenderPipelineStateCompletionHandlerFunction& function);"): "metal4::Compiler::specialize_render_pipeline_async",
    }
)

METAL4_ACCELERATION_BUFFER_PROPERTIES = (
    ("MTL4::AccelerationStructureGeometryDescriptor", "primitiveDataBuffer", "primitive_data_buffer"),
    ("MTL4::AccelerationStructureTriangleGeometryDescriptor", "indexBuffer", "index_buffer"),
    ("MTL4::AccelerationStructureTriangleGeometryDescriptor", "transformationMatrixBuffer", "transformation_matrix_buffer"),
    ("MTL4::AccelerationStructureTriangleGeometryDescriptor", "vertexBuffer", "vertex_buffer"),
    ("MTL4::AccelerationStructureBoundingBoxGeometryDescriptor", "boundingBoxBuffer", "bounding_box_buffer"),
    ("MTL4::AccelerationStructureMotionTriangleGeometryDescriptor", "indexBuffer", "index_buffer"),
    ("MTL4::AccelerationStructureMotionTriangleGeometryDescriptor", "transformationMatrixBuffer", "transformation_matrix_buffer"),
    ("MTL4::AccelerationStructureMotionTriangleGeometryDescriptor", "vertexBuffers", "vertex_buffers"),
    ("MTL4::AccelerationStructureMotionBoundingBoxGeometryDescriptor", "boundingBoxBuffers", "bounding_box_buffers"),
    ("MTL4::AccelerationStructureCurveGeometryDescriptor", "controlPointBuffer", "control_point_buffer"),
    ("MTL4::AccelerationStructureCurveGeometryDescriptor", "indexBuffer", "index_buffer"),
    ("MTL4::AccelerationStructureCurveGeometryDescriptor", "radiusBuffer", "radius_buffer"),
    ("MTL4::AccelerationStructureMotionCurveGeometryDescriptor", "controlPointBuffers", "control_point_buffers"),
    ("MTL4::AccelerationStructureMotionCurveGeometryDescriptor", "indexBuffer", "index_buffer"),
    ("MTL4::AccelerationStructureMotionCurveGeometryDescriptor", "radiusBuffers", "radius_buffers"),
    ("MTL4::InstanceAccelerationStructureDescriptor", "instanceDescriptorBuffer", "instance_descriptor_buffer"),
    ("MTL4::InstanceAccelerationStructureDescriptor", "motionTransformBuffer", "motion_transform_buffer"),
    ("MTL4::IndirectInstanceAccelerationStructureDescriptor", "instanceCountBuffer", "instance_count_buffer"),
    ("MTL4::IndirectInstanceAccelerationStructureDescriptor", "instanceDescriptorBuffer", "instance_descriptor_buffer"),
    ("MTL4::IndirectInstanceAccelerationStructureDescriptor", "motionTransformBuffer", "motion_transform_buffer"),
    ("MTL4::IndirectInstanceAccelerationStructureDescriptor", "motionTransformCountBuffer", "motion_transform_count_buffer"),
)

for _parent, _cpp_name, _rust_name in METAL4_ACCELERATION_BUFFER_PROPERTIES:
    _rust_parent = _parent.rsplit("::", 1)[-1]
    ACTUAL_METHODS[(_parent, _cpp_name)] = f"metal4::{_rust_parent}::{_rust_name}"
    ACTUAL_METHODS[(_parent, f"set{_cpp_name[0].upper()}{_cpp_name[1:]}")] = (
        f"metal4::{_rust_parent}::set_{_rust_name}"
    )

ACTUAL_METHODS.update(
    {
        ("MTL4::PrimitiveAccelerationStructureDescriptor", "geometryDescriptors"): "metal4::PrimitiveAccelerationStructureDescriptor::geometry_descriptor_vec",
        ("MTL4::PrimitiveAccelerationStructureDescriptor", "setGeometryDescriptors"): "metal4::PrimitiveAccelerationStructureDescriptor::set_geometry_descriptor_slice",
    }
)

ACTUAL_METHODS.update(
    {
        ("MTL::RenderCommandEncoder", cpp_name): f"metal::RenderCommandEncoder::{rust_name}"
        for cpp_name, rust_name in {
            "dispatchThreadsPerTile": "dispatch_threads_per_tile",
            "drawMeshThreads": "draw_mesh_threads",
            "sampleCountersInBuffer": "sample_counters",
            "setColorAttachmentMap": "set_color_attachment_map",
            "setColorStoreAction": "set_color_store_action",
            "setColorStoreActionOptions": "set_color_store_action_options",
            "setDepthStencilState": "set_depth_stencil_state",
            "setDepthStoreAction": "set_depth_store_action",
            "setDepthStoreActionOptions": "set_depth_store_action_options",
            "setFragmentAccelerationStructure": "set_fragment_acceleration_structure",
            "setFragmentBufferOffset": "set_fragment_buffer_offset",
            "setFragmentBuffers": "set_fragment_buffers",
            "setFragmentIntersectionFunctionTable": "set_fragment_intersection_function_table",
            "setFragmentIntersectionFunctionTables": "set_fragment_intersection_function_tables",
            "setFragmentTextures": "set_fragment_textures",
            "setFragmentVisibleFunctionTable": "set_fragment_visible_function_table",
            "setFragmentVisibleFunctionTables": "set_fragment_visible_function_tables",
            "setMeshBuffer": "set_mesh_buffer",
            "setMeshBufferOffset": "set_mesh_buffer_offset",
            "setMeshBuffers": "set_mesh_buffers",
            "setMeshBytes": "set_mesh_bytes",
            "setMeshTexture": "set_mesh_texture",
            "setMeshTextures": "set_mesh_textures",
            "setObjectBuffer": "set_object_buffer",
            "setObjectBufferOffset": "set_object_buffer_offset",
            "setObjectBuffers": "set_object_buffers",
            "setObjectBytes": "set_object_bytes",
            "setObjectTexture": "set_object_texture",
            "setObjectTextures": "set_object_textures",
            "setObjectThreadgroupMemoryLength": "set_object_threadgroup_memory_length",
            "setScissorRects": "set_scissor_rects",
            "setStencilStoreAction": "set_stencil_store_action",
            "setStencilStoreActionOptions": "set_stencil_store_action_options",
            "setTessellationFactorBuffer": "set_tessellation_factor_buffer",
            "setTessellationFactorScale": "set_tessellation_factor_scale",
            "setThreadgroupMemoryLength": "set_threadgroup_memory_length",
            "setTileAccelerationStructure": "set_tile_acceleration_structure",
            "setTileBuffer": "set_tile_buffer",
            "setTileBufferOffset": "set_tile_buffer_offset",
            "setTileBuffers": "set_tile_buffers",
            "setTileBytes": "set_tile_bytes",
            "setTileIntersectionFunctionTable": "set_tile_intersection_function_table",
            "setTileIntersectionFunctionTables": "set_tile_intersection_function_tables",
            "setTileTexture": "set_tile_texture",
            "setTileTextures": "set_tile_textures",
            "setTileVisibleFunctionTable": "set_tile_visible_function_table",
            "setTileVisibleFunctionTables": "set_tile_visible_function_tables",
            "setVertexAccelerationStructure": "set_vertex_acceleration_structure",
            "setVertexAmplificationCount": "set_vertex_amplification",
            "setVertexIntersectionFunctionTable": "set_vertex_intersection_function_table",
            "setVertexIntersectionFunctionTables": "set_vertex_intersection_function_tables",
            "setVertexTextures": "set_vertex_textures",
            "setVertexVisibleFunctionTable": "set_vertex_visible_function_table",
            "setVertexVisibleFunctionTables": "set_vertex_visible_function_tables",
            "setViewports": "set_viewports",
            "setVisibilityResultMode": "set_visibility_result_mode",
            "updateFence": "update_fence",
            "useResource": "use_resource",
            "useResources": "use_resources",
            "waitForFence": "wait_for_fence",
        }.items()
    }
)

ACTUAL_METHOD_SIGNATURES.update({
    ("MTL::RenderCommandEncoder", "drawPrimitives", "void drawPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger vertexStart, NS::UInteger vertexCount);"): "metal::RenderCommandEncoder::draw_primitives",
    ("MTL::RenderCommandEncoder", "setVertexBuffer", "void setVertexBuffer(const MTL::Buffer* buffer, NS::UInteger offset, NS::UInteger index);"): "metal::RenderCommandEncoder::set_vertex_buffer",
    ("MTL::RenderCommandEncoder", "setVertexBytes", "void setVertexBytes(const void* bytes, NS::UInteger length, NS::UInteger index);"): "metal::RenderCommandEncoder::set_vertex_bytes",
    ("MTL::ComputeCommandEncoder", "setBuffer", "void setBuffer(const MTL::Buffer* buffer, NS::UInteger offset, NS::UInteger index);"): "metal::ComputeCommandEncoder::set_buffer",
    ("MTL::ComputeCommandEncoder", "setBuffer", "void setBuffer(const MTL::Buffer* buffer, NS::UInteger offset, NS::UInteger stride, NS::UInteger index);"): "metal::ComputeCommandEncoder::set_buffer_with_stride",
    ("MTL::ComputeCommandEncoder", "setBytes", "void setBytes(const void* bytes, NS::UInteger length, NS::UInteger index);"): "metal::ComputeCommandEncoder::set_bytes",
    ("MTL::ComputeCommandEncoder", "setBytes", "void setBytes(const void* bytes, NS::UInteger length, NS::UInteger stride, NS::UInteger index);"): "metal::ComputeCommandEncoder::set_bytes_with_stride",
    ("MTL::ComputeCommandEncoder", "dispatchThreadgroups", "void dispatchThreadgroups(MTL::Size threadgroupsPerGrid, MTL::Size threadsPerThreadgroup);"): "metal::ComputeCommandEncoder::dispatch_threadgroups",
    ("MTL::ComputeCommandEncoder", "dispatchThreadgroups", "void dispatchThreadgroups(const MTL::Buffer* indirectBuffer, NS::UInteger indirectBufferOffset, MTL::Size threadsPerThreadgroup);"): "metal::ComputeCommandEncoder::dispatch_threadgroups_indirect",
    ("MTL::ComputeCommandEncoder", "setBufferOffset", "void setBufferOffset(NS::UInteger offset, NS::UInteger index);"): "metal::ComputeCommandEncoder::set_buffer_offset",
    ("MTL::ComputeCommandEncoder", "setBufferOffset", "void setBufferOffset(NS::UInteger offset, NS::UInteger stride, NS::UInteger index);"): "metal::ComputeCommandEncoder::set_buffer_offset_with_stride",
    ("MTL::ComputeCommandEncoder", "setBuffers", "void setBuffers(const MTL::Buffer* const buffers[], const NS::UInteger offsets[], NS::Range range);"): "metal::ComputeCommandEncoder::set_buffers",
    ("MTL::ComputeCommandEncoder", "setBuffers", "void setBuffers(const MTL::Buffer* const buffers[], const NS::UInteger* offsets, const NS::UInteger* strides, NS::Range range);"): "metal::ComputeCommandEncoder::set_buffers_with_strides",
    ("MTL::ComputeCommandEncoder", "setStageInRegion", "void setStageInRegion(MTL::Region region);"): "metal::ComputeCommandEncoder::set_stage_in_region",
    ("MTL::ComputeCommandEncoder", "setStageInRegion", "void setStageInRegion(const MTL::Buffer* indirectBuffer, NS::UInteger indirectBufferOffset);"): "metal::ComputeCommandEncoder::set_stage_in_region_indirect",
    ("MTL::Device", "deprecated", "[[deprecated( )]] bool barycentricCoordsSupported() const;"): "metal::Device::capability",
    ("MTL::Device", "deprecated", "[[deprecated( )]] bool programmableSamplePositionsSupported() const;"): "metal::Device::capability",
    ("MTL::Device", "deprecated", "[[deprecated( )]] bool rasterOrderGroupsSupported() const;"): "metal::Device::capability",
    ("MTL::Device", "deprecated", "[[deprecated( )]] bool depth24Stencil8PixelFormatSupported() const;"): "metal::Device::capability",
    ("MTL::Device", "deprecated", "[[deprecated( )]] bool headless() const;"): "metal::Device::capability",
    ("MTL::Device", "deprecated", "[[deprecated( )]] bool lowPower() const;"): "metal::Device::capability",
    ("MTL::Device", "deprecated", "[[deprecated( )]] bool removable() const;"): "metal::Device::capability",
    ("MTL::Texture", "deprecated", "[[deprecated( )]] bool framebufferOnly() const;"): "metal::Texture::is_framebuffer_only",
    ("MTL::Texture", "deprecated", "[[deprecated( )]] bool shareable() const;"): "metal::Texture::is_shareable",
    ("MTL::RenderPipelineDescriptor", "deprecated", "[[deprecated( )]] bool alphaToCoverageEnabled() const;"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "deprecated", "[[deprecated( )]] bool alphaToOneEnabled() const;"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "deprecated", "[[deprecated( )]] bool rasterizationEnabled() const;"): "metal::RenderPipelineDescriptor::options",
    ("MTL::RenderPipelineDescriptor", "deprecated", "[[deprecated( )]] bool tessellationFactorScaleEnabled() const;"): "metal::RenderPipelineDescriptor::options",
    ("MTL::Origin", "Origin", "Origin() = default;"): "metal::Origin::default",
    ("MTL::Origin", "Origin", "Origin(NS::UInteger x, NS::UInteger y, NS::UInteger z);"): "metal::Origin::new",
    ("MTL::Origin", "Make", "static Origin Make(NS::UInteger x, NS::UInteger y, NS::UInteger z);"): "metal::Origin::new",
    ("MTL::Size", "Size", "Size() = default;"): "metal::Size::default",
    ("MTL::Size", "Size", "Size(NS::UInteger width, NS::UInteger height, NS::UInteger depth);"): "metal::Size::new",
    ("MTL::Size", "Make", "static Size Make(NS::UInteger width, NS::UInteger height, NS::UInteger depth);"): "metal::Size::new",
    ("MTL::Region", "Region", "Region() = default;"): "metal::Region::default",
    ("MTL::Region", "Region", "Region(NS::UInteger x, NS::UInteger width);"): "metal::Region::new_1d",
    ("MTL::Region", "Region", "Region(NS::UInteger x, NS::UInteger y, NS::UInteger width, NS::UInteger height);"): "metal::Region::new_2d",
    ("MTL::Region", "Region", "Region(NS::UInteger x, NS::UInteger y, NS::UInteger z, NS::UInteger width, NS::UInteger height, NS::UInteger depth);"): "metal::Region::new_3d",
    ("MTL::Region", "Make1D", "static Region Make1D(NS::UInteger x, NS::UInteger width);"): "metal::Region::new_1d",
    ("MTL::Region", "Make2D", "static Region Make2D(NS::UInteger x, NS::UInteger y, NS::UInteger width, NS::UInteger height);"): "metal::Region::new_2d",
    ("MTL::Region", "Make3D", "static Region Make3D(NS::UInteger x, NS::UInteger y, NS::UInteger z, NS::UInteger width, NS::UInteger height, NS::UInteger depth);"): "metal::Region::new_3d",
    ("MTL::ClearColor", "ClearColor", "ClearColor() = default;"): "metal::ClearColor::default",
    ("MTL::ClearColor", "ClearColor", "ClearColor(double red, double green, double blue, double alpha);"): "metal::ClearColor::new",
    ("MTL::ClearColor", "Make", "static ClearColor Make(double red, double green, double blue, double alpha);"): "metal::ClearColor::new",
    (
        "MTL::CommandBuffer",
        "blitCommandEncoder",
        "BlitCommandEncoder* blitCommandEncoder();",
    ): "metal::CommandBuffer::blit_encoder",
    (
        "MTL::CommandQueue",
        "commandBuffer",
        "CommandBuffer* commandBuffer();",
    ): "metal::CommandQueue::command_buffer",
    (
        "MTL::Device",
        "newCommandQueue",
        "CommandQueue* newCommandQueue();",
    ): "metal::Device::new_command_queue",
    (
        "MTL::Device",
        "newCommandQueue",
        "CommandQueue* newCommandQueue(NS::UInteger maxCommandBufferCount);",
    ): "metal::Device::new_command_queue",
    (
        "MTL::Device",
        "newBuffer",
        "Buffer* newBuffer(NS::UInteger length, MTL::ResourceOptions options);",
    ): "metal::Device::new_buffer",
    (
        "MTL::Device",
        "newTexture",
        "Texture* newTexture(const MTL::TextureDescriptor* descriptor);",
    ): "metal::Device::new_texture",
    (
        "MTL::Device",
        "newLibrary",
        "Library* newLibrary(const NS::String* source, const MTL::CompileOptions* options, NS::Error** error);",
    ): "metal::Device::new_library_from_source",
    (
        "MTL::Device",
        "newRenderPipelineState",
        "RenderPipelineState* newRenderPipelineState(const MTL::RenderPipelineDescriptor* descriptor, NS::Error** error);",
    ): "metal::Device::new_render_pipeline",
    (
        "MTL::Device",
        "newComputePipelineState",
        "ComputePipelineState* newComputePipelineState(const MTL::Function* computeFunction, NS::Error** error);",
    ): "metal::Device::new_compute_pipeline",
    (
        "MTL::Library",
        "newFunction",
        "Function* newFunction(const NS::String* functionName);",
    ): "metal::Library::function",
    (
        "MTL::Texture",
        "newTextureView",
        "Texture* newTextureView(MTL::PixelFormat pixelFormat);",
    ): "metal::Texture::view_with_pixel_format",
    (
        "MTL::Device",
        "heapAccelerationStructureSizeAndAlign",
        "SizeAndAlign heapAccelerationStructureSizeAndAlign(NS::UInteger size);",
    ): "metal::Device::heap_acceleration_structure_size_and_align",
    (
        "MTL::RenderCommandEncoder",
        "drawPrimitives",
        "void drawPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger vertexStart, NS::UInteger vertexCount, NS::UInteger instanceCount);",
    ): "metal::RenderCommandEncoder::draw_primitives_instanced",
    (
        "MTL::RenderCommandEncoder",
        "drawPrimitives",
        "void drawPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger vertexStart, NS::UInteger vertexCount, NS::UInteger instanceCount, NS::UInteger baseInstance);",
    ): "metal::RenderCommandEncoder::draw_primitives_instanced",
    (
        "MTL::BlitCommandEncoder",
        "copyFromBuffer",
        "void copyFromBuffer(const MTL::Buffer* sourceBuffer, NS::UInteger sourceOffset, const MTL::Buffer* destinationBuffer, NS::UInteger destinationOffset, NS::UInteger size);",
    ): "metal::BlitCommandEncoder::copy_buffer",
    (
        "MTL::BlitCommandEncoder",
        "copyFromTexture",
        "void copyFromTexture(const MTL::Texture* sourceTexture, const MTL::Texture* destinationTexture);",
    ): "metal::BlitCommandEncoder::copy_texture",
    (
        "MTL::BlitCommandEncoder",
        "optimizeContentsForCPUAccess",
        "void optimizeContentsForCPUAccess(const MTL::Texture* texture);",
    ): "metal::BlitCommandEncoder::optimize_texture_for_cpu",
    (
        "MTL::BlitCommandEncoder",
        "optimizeContentsForGPUAccess",
        "void optimizeContentsForGPUAccess(const MTL::Texture* texture);",
    ): "metal::BlitCommandEncoder::optimize_texture_for_gpu",
    (
        "MTLFX::TemporalScalerBase",
        "deprecated",
        "[[deprecated( )]] MTL::TextureUsage reactiveTextureUsage() const;",
    ): "metal_fx::TemporalScaler::reactive_texture_usage",
    (
        "MTLFX::TemporalDenoisedScalerBase",
        "deprecated",
        "[[deprecated( )]] MTL::TextureUsage reactiveTextureUsage() const;",
    ): "metal_fx::TemporalDenoisedScalerBase::reactive_mask_texture_usage",
})

ACTUAL_METHOD_SIGNATURES.update(
    {
        # Command queue/buffer overloads are deliberately signature-pinned so
        # encoder factories that do not yet preserve typestate stay uncovered.
        (
            "MTL::CommandQueue",
            "commandBuffer",
            "CommandBuffer* commandBuffer(const MTL::CommandBufferDescriptor* descriptor);",
        ): "metal::CommandQueue::command_buffer_with_descriptor",
        (
            "MTL::CommandBuffer",
            "computeCommandEncoder",
            "ComputeCommandEncoder* computeCommandEncoder();",
        ): "metal::CommandBuffer::compute_encoder_default",
        (
            "MTL::CommandBuffer",
            "computeCommandEncoder",
            "ComputeCommandEncoder* computeCommandEncoder(MTL::DispatchType dispatchType);",
        ): "metal::CommandBuffer::compute_encoder_with_dispatch_type",
        (
            "MTL::CommandBuffer",
            "blitCommandEncoder",
            "BlitCommandEncoder* blitCommandEncoder(const MTL::BlitPassDescriptor* blitPassDescriptor);",
        ): "metal::CommandBuffer::blit_encoder_with_descriptor",
        # Capture target overloads.  The MTL4 queue overload remains uncovered
        # until its canonical command-queue wrapper is available.
        (
            "MTL::CaptureManager",
            "newCaptureScope",
            "CaptureScope* newCaptureScope(const MTL::Device* device);",
        ): "metal::CaptureSession::new_scope_for_device",
        (
            "MTL::CaptureManager",
            "newCaptureScope",
            "CaptureScope* newCaptureScope(const MTL::CommandQueue* commandQueue);",
        ): "metal::CaptureSession::new_scope_for_command_queue",
        (
            "MTL::CaptureManager",
            "startCapture",
            "bool startCapture(const MTL::CaptureDescriptor* descriptor, NS::Error** error);",
        ): "metal::CaptureSession::start_descriptor",
        (
            "MTL::CaptureManager",
            "startCapture",
            "void startCapture(const MTL::Device* device);",
        ): "metal::CaptureSession::start_for_device",
        (
            "MTL::CaptureManager",
            "startCapture",
            "void startCapture(const MTL::CommandQueue* commandQueue);",
        ): "metal::CaptureSession::start_for_command_queue",
        (
            "MTL::CaptureManager",
            "startCapture",
            "void startCapture(const MTL::CaptureScope* captureScope);",
        ): "metal::CaptureSession::start_for_scope",
        # Shader specialization and derived pipeline creation.
        (
            "MTL::Library",
            "newFunction",
            "Function* newFunction(const NS::String* name, const MTL::FunctionConstantValues* constantValues, NS::Error** error);",
        ): "metal::Library::specialized_function",
        (
            "MTL::Library",
            "newFunction",
            "Function* newFunction(const MTL::FunctionDescriptor* descriptor, NS::Error** error);",
        ): "metal::Library::function_with_descriptor",
        (
            "MTL::Library",
            "newIntersectionFunction",
            "Function* newIntersectionFunction(const MTL::IntersectionFunctionDescriptor* descriptor, NS::Error** error);",
        ): "metal::Library::intersection_function_with_descriptor",
        (
            "MTL::RenderPipelineState",
            "functionHandle",
            "FunctionHandle* functionHandle(const NS::String* name, MTL::RenderStages stage);",
        ): "metal::RenderPipelineState::function_handle_by_name",
        (
            "MTL::RenderPipelineState",
            "newRenderPipelineState",
            "RenderPipelineState* newRenderPipelineState(const MTL::RenderPipelineFunctionsDescriptor* additionalBinaryFunctions, NS::Error** error);",
        ): "metal::RenderPipelineState::with_additional_binary_functions",
        (
            "MTL::ComputePipelineState",
            "functionHandle",
            "FunctionHandle* functionHandle(const NS::String* name);",
        ): "metal::ComputePipelineState::function_handle_by_name",
        (
            "MTL::ComputePipelineState",
            "newComputePipelineState",
            "ComputePipelineState* newComputePipelineState(const NS::Array* functions, NS::Error** error);",
        ): "metal::ComputePipelineState::with_additional_functions",
        # Safe texture factories, views, and owned CPU source slices.
        (
            "MTL::TextureDescriptor",
            "texture2DDescriptor",
            "static TextureDescriptor* texture2DDescriptor(MTL::PixelFormat pixelFormat, NS::UInteger width, NS::UInteger height, bool mipmapped);",
        ): "metal::TextureDescriptor::texture_2d",
        (
            "MTL::TextureDescriptor",
            "textureCubeDescriptor",
            "static TextureDescriptor* textureCubeDescriptor(MTL::PixelFormat pixelFormat, NS::UInteger size, bool mipmapped);",
        ): "metal::TextureDescriptor::texture_cube",
        (
            "MTL::TextureDescriptor",
            "textureBufferDescriptor",
            "static TextureDescriptor* textureBufferDescriptor(MTL::PixelFormat pixelFormat, NS::UInteger width, MTL::ResourceOptions resourceOptions, MTL::TextureUsage usage);",
        ): "metal::TextureDescriptor::texture_buffer",
        (
            "MTL::Texture",
            "newTextureView",
            "Texture* newTextureView(MTL::PixelFormat pixelFormat, MTL::TextureType textureType, NS::Range levelRange, NS::Range sliceRange);",
        ): "metal::Texture::view",
        (
            "MTL::Texture",
            "newTextureView",
            "Texture* newTextureView(const MTL::TextureViewDescriptor* descriptor);",
        ): "metal::Texture::view_with_descriptor",
        (
            "MTL::Texture",
            "newTextureView",
            "Texture* newTextureView(MTL::PixelFormat pixelFormat, MTL::TextureType textureType, NS::Range levelRange, NS::Range sliceRange, MTL::TextureSwizzleChannels swizzle);",
        ): "metal::Texture::view_with_swizzle",
        (
            "MTL::Texture",
            "replaceRegion",
            "void replaceRegion(MTL::Region region, NS::UInteger level, const void* pixelBytes, NS::UInteger bytesPerRow);",
        ): "metal::Texture::replace_region_2d",
        (
            "MTL::Texture",
            "replaceRegion",
            "void replaceRegion(MTL::Region region, NS::UInteger level, NS::UInteger slice, const void* pixelBytes, NS::UInteger bytesPerRow, NS::UInteger bytesPerImage);",
        ): "metal::Texture::replace_region",
        # Heap overloads retain size/descriptor and explicit-offset distinctions.
        (
            "MTL::Heap",
            "newBuffer",
            "Buffer* newBuffer(NS::UInteger length, MTL::ResourceOptions options);",
        ): "metal::Heap::new_buffer",
        (
            "MTL::Heap",
            "newBuffer",
            "Buffer* newBuffer(NS::UInteger length, MTL::ResourceOptions options, NS::UInteger offset);",
        ): "metal::Heap::new_buffer_at_offset",
        (
            "MTL::Heap",
            "newTexture",
            "Texture* newTexture(const MTL::TextureDescriptor* descriptor);",
        ): "metal::Heap::new_texture",
        (
            "MTL::Heap",
            "newTexture",
            "Texture* newTexture(const MTL::TextureDescriptor* descriptor, NS::UInteger offset);",
        ): "metal::Heap::new_texture_at_offset",
        (
            "MTL::Heap",
            "newAccelerationStructure",
            "AccelerationStructure* newAccelerationStructure(NS::UInteger size);",
        ): "metal::Heap::new_acceleration_structure",
        (
            "MTL::Heap",
            "newAccelerationStructure",
            "AccelerationStructure* newAccelerationStructure(const MTL::AccelerationStructureDescriptor* descriptor);",
        ): "metal::Heap::new_acceleration_structure_with_descriptor",
        (
            "MTL::Heap",
            "newAccelerationStructure",
            "AccelerationStructure* newAccelerationStructure(NS::UInteger size, NS::UInteger offset);",
        ): "metal::Heap::new_acceleration_structure_at_offset",
        (
            "MTL::Heap",
            "newAccelerationStructure",
            "AccelerationStructure* newAccelerationStructure(const MTL::AccelerationStructureDescriptor* descriptor, NS::UInteger offset);",
        ): "metal::Heap::new_acceleration_structure_with_descriptor_at_offset",
        # Rasterization-rate constructors preserve which sample arrays are supplied.
        (
            "MTL::RasterizationRateLayerDescriptor",
            "init",
            "RasterizationRateLayerDescriptor* init(MTL::Size sampleCount);",
        ): "metal::RasterizationRateLayerDescriptor::with_sample_count",
        (
            "MTL::RasterizationRateLayerDescriptor",
            "init",
            "RasterizationRateLayerDescriptor* init(MTL::Size sampleCount, const float* horizontal, const float* vertical);",
        ): "metal::RasterizationRateLayerDescriptor::with_samples",
        (
            "MTL::RasterizationRateMapDescriptor",
            "rasterizationRateMapDescriptor",
            "static RasterizationRateMapDescriptor* rasterizationRateMapDescriptor(MTL::Size screenSize);",
        ): "metal::RasterizationRateMapDescriptor::with_screen_size",
        (
            "MTL::RasterizationRateMapDescriptor",
            "rasterizationRateMapDescriptor",
            "static RasterizationRateMapDescriptor* rasterizationRateMapDescriptor(MTL::Size screenSize, const MTL::RasterizationRateLayerDescriptor* layer);",
        ): "metal::RasterizationRateMapDescriptor::with_layer",
        (
            "MTL::RasterizationRateMapDescriptor",
            "rasterizationRateMapDescriptor",
            "static RasterizationRateMapDescriptor* rasterizationRateMapDescriptor(MTL::Size screenSize, NS::UInteger layerCount, const MTL::RasterizationRateLayerDescriptor* const* layers);",
        ): "metal::RasterizationRateMapDescriptor::with_layers",
    }
)

ACTUAL_METHOD_SIGNATURES.update(
    {
        ("MTL::RenderCommandEncoder", "drawIndexedPatches", "void drawIndexedPatches(NS::UInteger numberOfPatchControlPoints, NS::UInteger patchStart, NS::UInteger patchCount, const MTL::Buffer* patchIndexBuffer, NS::UInteger patchIndexBufferOffset, const MTL::Buffer* controlPointIndexBuffer, NS::UInteger controlPointIndexBufferOffset, NS::UInteger instanceCount, NS::UInteger baseInstance);"): "metal::RenderCommandEncoder::draw_indexed_patches",
        ("MTL::RenderCommandEncoder", "drawIndexedPatches", "void drawIndexedPatches(NS::UInteger numberOfPatchControlPoints, const MTL::Buffer* patchIndexBuffer, NS::UInteger patchIndexBufferOffset, const MTL::Buffer* controlPointIndexBuffer, NS::UInteger controlPointIndexBufferOffset, const MTL::Buffer* indirectBuffer, NS::UInteger indirectBufferOffset);"): "metal::RenderCommandEncoder::draw_indexed_patches_indirect",
        ("MTL::RenderCommandEncoder", "drawIndexedPrimitives", "void drawIndexedPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger indexCount, MTL::IndexType indexType, const MTL::Buffer* indexBuffer, NS::UInteger indexBufferOffset, NS::UInteger instanceCount);"): "metal::RenderCommandEncoder::draw_indexed_primitives",
        ("MTL::RenderCommandEncoder", "drawIndexedPrimitives", "void drawIndexedPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger indexCount, MTL::IndexType indexType, const MTL::Buffer* indexBuffer, NS::UInteger indexBufferOffset);"): "metal::RenderCommandEncoder::draw_indexed_primitives",
        ("MTL::RenderCommandEncoder", "drawIndexedPrimitives", "void drawIndexedPrimitives(MTL::PrimitiveType primitiveType, NS::UInteger indexCount, MTL::IndexType indexType, const MTL::Buffer* indexBuffer, NS::UInteger indexBufferOffset, NS::UInteger instanceCount, NS::Integer baseVertex, NS::UInteger baseInstance);"): "metal::RenderCommandEncoder::draw_indexed_primitives",
        ("MTL::RenderCommandEncoder", "drawIndexedPrimitives", "void drawIndexedPrimitives(MTL::PrimitiveType primitiveType, MTL::IndexType indexType, const MTL::Buffer* indexBuffer, NS::UInteger indexBufferOffset, const MTL::Buffer* indirectBuffer, NS::UInteger indirectBufferOffset);"): "metal::RenderCommandEncoder::draw_indexed_primitives_indirect",
        ("MTL::RenderCommandEncoder", "drawMeshThreadgroups", "void drawMeshThreadgroups(MTL::Size threadgroupsPerGrid, MTL::Size threadsPerObjectThreadgroup, MTL::Size threadsPerMeshThreadgroup);"): "metal::RenderCommandEncoder::draw_mesh_threadgroups",
        ("MTL::RenderCommandEncoder", "drawMeshThreadgroups", "void drawMeshThreadgroups(const MTL::Buffer* indirectBuffer, NS::UInteger indirectBufferOffset, MTL::Size threadsPerObjectThreadgroup, MTL::Size threadsPerMeshThreadgroup);"): "metal::RenderCommandEncoder::draw_mesh_threadgroups_indirect",
        ("MTL::RenderCommandEncoder", "drawPatches", "void drawPatches(NS::UInteger numberOfPatchControlPoints, NS::UInteger patchStart, NS::UInteger patchCount, const MTL::Buffer* patchIndexBuffer, NS::UInteger patchIndexBufferOffset, NS::UInteger instanceCount, NS::UInteger baseInstance);"): "metal::RenderCommandEncoder::draw_patches",
        ("MTL::RenderCommandEncoder", "drawPatches", "void drawPatches(NS::UInteger numberOfPatchControlPoints, const MTL::Buffer* patchIndexBuffer, NS::UInteger patchIndexBufferOffset, const MTL::Buffer* indirectBuffer, NS::UInteger indirectBufferOffset);"): "metal::RenderCommandEncoder::draw_patches_indirect",
        ("MTL::RenderCommandEncoder", "drawPrimitives", "void drawPrimitives(MTL::PrimitiveType primitiveType, const MTL::Buffer* indirectBuffer, NS::UInteger indirectBufferOffset);"): "metal::RenderCommandEncoder::draw_primitives_indirect",
        ("MTL::RenderCommandEncoder", "executeCommandsInBuffer", "void executeCommandsInBuffer(const MTL::IndirectCommandBuffer* indirectCommandBuffer, NS::Range executionRange);"): "metal::RenderCommandEncoder::execute_commands",
        ("MTL::RenderCommandEncoder", "executeCommandsInBuffer", "void executeCommandsInBuffer(const MTL::IndirectCommandBuffer* indirectCommandbuffer, const MTL::Buffer* indirectRangeBuffer, NS::UInteger indirectBufferOffset);"): "metal::RenderCommandEncoder::execute_commands_indirect",
        ("MTL::RenderCommandEncoder", "memoryBarrier", "void memoryBarrier(MTL::BarrierScope scope, MTL::RenderStages after, MTL::RenderStages before);"): "metal::RenderCommandEncoder::memory_barrier",
        ("MTL::RenderCommandEncoder", "memoryBarrier", "void memoryBarrier(const MTL::Resource* const resources[], NS::UInteger count, MTL::RenderStages after, MTL::RenderStages before);"): "metal::RenderCommandEncoder::memory_barriers",
        ("MTL::RenderCommandEncoder", "setFragmentSamplerState", "void setFragmentSamplerState(const MTL::SamplerState* sampler, NS::UInteger index);"): "metal::RenderCommandEncoder::set_fragment_sampler",
        ("MTL::RenderCommandEncoder", "setFragmentSamplerState", "void setFragmentSamplerState(const MTL::SamplerState* sampler, float lodMinClamp, float lodMaxClamp, NS::UInteger index);"): "metal::RenderCommandEncoder::set_fragment_sampler",
        ("MTL::RenderCommandEncoder", "setFragmentSamplerStates", "void setFragmentSamplerStates(const MTL::SamplerState* const samplers[], NS::Range range);"): "metal::RenderCommandEncoder::set_fragment_samplers",
        ("MTL::RenderCommandEncoder", "setFragmentSamplerStates", "void setFragmentSamplerStates(const MTL::SamplerState* const samplers[], const float lodMinClamps[], const float lodMaxClamps[], NS::Range range);"): "metal::RenderCommandEncoder::set_fragment_samplers_with_lod_clamps",
        ("MTL::RenderCommandEncoder", "setMeshSamplerState", "void setMeshSamplerState(const MTL::SamplerState* sampler, NS::UInteger index);"): "metal::RenderCommandEncoder::set_mesh_sampler",
        ("MTL::RenderCommandEncoder", "setMeshSamplerState", "void setMeshSamplerState(const MTL::SamplerState* sampler, float lodMinClamp, float lodMaxClamp, NS::UInteger index);"): "metal::RenderCommandEncoder::set_mesh_sampler",
        ("MTL::RenderCommandEncoder", "setMeshSamplerStates", "void setMeshSamplerStates(const MTL::SamplerState* const samplers[], NS::Range range);"): "metal::RenderCommandEncoder::set_mesh_samplers",
        ("MTL::RenderCommandEncoder", "setMeshSamplerStates", "void setMeshSamplerStates(const MTL::SamplerState* const samplers[], const float* lodMinClamps, const float* lodMaxClamps, NS::Range range);"): "metal::RenderCommandEncoder::set_mesh_samplers_with_lod_clamps",
        ("MTL::RenderCommandEncoder", "setObjectSamplerState", "void setObjectSamplerState(const MTL::SamplerState* sampler, NS::UInteger index);"): "metal::RenderCommandEncoder::set_object_sampler",
        ("MTL::RenderCommandEncoder", "setObjectSamplerState", "void setObjectSamplerState(const MTL::SamplerState* sampler, float lodMinClamp, float lodMaxClamp, NS::UInteger index);"): "metal::RenderCommandEncoder::set_object_sampler",
        ("MTL::RenderCommandEncoder", "setObjectSamplerStates", "void setObjectSamplerStates(const MTL::SamplerState* const samplers[], NS::Range range);"): "metal::RenderCommandEncoder::set_object_samplers",
        ("MTL::RenderCommandEncoder", "setObjectSamplerStates", "void setObjectSamplerStates(const MTL::SamplerState* const samplers[], const float* lodMinClamps, const float* lodMaxClamps, NS::Range range);"): "metal::RenderCommandEncoder::set_object_samplers_with_lod_clamps",
        ("MTL::RenderCommandEncoder", "setTileSamplerState", "void setTileSamplerState(const MTL::SamplerState* sampler, NS::UInteger index);"): "metal::RenderCommandEncoder::set_tile_sampler",
        ("MTL::RenderCommandEncoder", "setTileSamplerState", "void setTileSamplerState(const MTL::SamplerState* sampler, float lodMinClamp, float lodMaxClamp, NS::UInteger index);"): "metal::RenderCommandEncoder::set_tile_sampler",
        ("MTL::RenderCommandEncoder", "setTileSamplerStates", "void setTileSamplerStates(const MTL::SamplerState* const samplers[], NS::Range range);"): "metal::RenderCommandEncoder::set_tile_samplers",
        ("MTL::RenderCommandEncoder", "setTileSamplerStates", "void setTileSamplerStates(const MTL::SamplerState* const samplers[], const float lodMinClamps[], const float lodMaxClamps[], NS::Range range);"): "metal::RenderCommandEncoder::set_tile_samplers_with_lod_clamps",
        ("MTL::RenderCommandEncoder", "setVertexBuffer", "void setVertexBuffer(const MTL::Buffer* buffer, NS::UInteger offset, NS::UInteger stride, NS::UInteger index);"): "metal::RenderCommandEncoder::set_vertex_buffer_with_stride",
        ("MTL::RenderCommandEncoder", "setVertexBufferOffset", "void setVertexBufferOffset(NS::UInteger offset, NS::UInteger index);"): "metal::RenderCommandEncoder::set_vertex_buffer_offset",
        ("MTL::RenderCommandEncoder", "setVertexBufferOffset", "void setVertexBufferOffset(NS::UInteger offset, NS::UInteger stride, NS::UInteger index);"): "metal::RenderCommandEncoder::set_vertex_buffer_offset_with_stride",
        ("MTL::RenderCommandEncoder", "setVertexBuffers", "void setVertexBuffers(const MTL::Buffer* const buffers[], const NS::UInteger offsets[], NS::Range range);"): "metal::RenderCommandEncoder::set_vertex_buffers",
        ("MTL::RenderCommandEncoder", "setVertexBuffers", "void setVertexBuffers(const MTL::Buffer* const buffers[], const NS::UInteger* offsets, const NS::UInteger* strides, NS::Range range);"): "metal::RenderCommandEncoder::set_vertex_buffers_with_strides",
        ("MTL::RenderCommandEncoder", "setVertexBytes", "void setVertexBytes(const void* bytes, NS::UInteger length, NS::UInteger stride, NS::UInteger index);"): "metal::RenderCommandEncoder::set_vertex_bytes_with_stride",
        ("MTL::RenderCommandEncoder", "setVertexSamplerState", "void setVertexSamplerState(const MTL::SamplerState* sampler, NS::UInteger index);"): "metal::RenderCommandEncoder::set_vertex_sampler",
        ("MTL::RenderCommandEncoder", "setVertexSamplerState", "void setVertexSamplerState(const MTL::SamplerState* sampler, float lodMinClamp, float lodMaxClamp, NS::UInteger index);"): "metal::RenderCommandEncoder::set_vertex_sampler",
        ("MTL::RenderCommandEncoder", "setVertexSamplerStates", "void setVertexSamplerStates(const MTL::SamplerState* const samplers[], NS::Range range);"): "metal::RenderCommandEncoder::set_vertex_samplers",
        ("MTL::RenderCommandEncoder", "setVertexSamplerStates", "void setVertexSamplerStates(const MTL::SamplerState* const samplers[], const float lodMinClamps[], const float lodMaxClamps[], NS::Range range);"): "metal::RenderCommandEncoder::set_vertex_samplers_with_lod_clamps",
        ("MTL::RenderCommandEncoder", "useHeap", "void useHeap(const MTL::Heap* heap);"): "metal::RenderCommandEncoder::use_heap",
        ("MTL::RenderCommandEncoder", "useHeap", "void useHeap(const MTL::Heap* heap, MTL::RenderStages stages);"): "metal::RenderCommandEncoder::use_heap",
        ("MTL::RenderCommandEncoder", "useHeaps", "void useHeaps(const MTL::Heap* const heaps[], NS::UInteger count);"): "metal::RenderCommandEncoder::use_heaps",
        ("MTL::RenderCommandEncoder", "useHeaps", "void useHeaps(const MTL::Heap* const heaps[], NS::UInteger count, MTL::RenderStages stages);"): "metal::RenderCommandEncoder::use_heaps",
        ("MTL::RenderCommandEncoder", "deprecated", "[[deprecated( )]] void useResource(const MTL::Resource* resource, MTL::ResourceUsage usage);"): "metal::RenderCommandEncoder::use_resource",
        ("MTL::RenderCommandEncoder", "deprecated", "[[deprecated( )]] void useResources(const MTL::Resource* const resources[], NS::UInteger count, MTL::ResourceUsage usage);"): "metal::RenderCommandEncoder::use_resources",
    }
)

ACTUAL_METHODS.update(
    {
        # Compute encoder resource bindings and synchronization.
        ("MTL::ComputeCommandEncoder", "setSamplerStates"): "metal::ComputeCommandEncoder::set_sampler_states",
        ("MTL::ComputeCommandEncoder", "setVisibleFunctionTable"): "metal::ComputeCommandEncoder::set_visible_function_table",
        ("MTL::ComputeCommandEncoder", "setVisibleFunctionTables"): "metal::ComputeCommandEncoder::set_visible_function_tables",
        ("MTL::ComputeCommandEncoder", "setIntersectionFunctionTable"): "metal::ComputeCommandEncoder::set_intersection_function_table",
        ("MTL::ComputeCommandEncoder", "setIntersectionFunctionTables"): "metal::ComputeCommandEncoder::set_intersection_function_tables",
        ("MTL::ComputeCommandEncoder", "setAccelerationStructure"): "metal::ComputeCommandEncoder::set_acceleration_structure",
        ("MTL::ComputeCommandEncoder", "waitForFence"): "metal::ComputeCommandEncoder::wait_for_fence",
        ("MTL::ComputeCommandEncoder", "updateFence"): "metal::ComputeCommandEncoder::update_fence",
        ("MTL::ComputeCommandEncoder", "useHeap"): "metal::ComputeCommandEncoder::use_heap",
        ("MTL::ComputeCommandEncoder", "useHeaps"): "metal::ComputeCommandEncoder::use_heaps",
        ("MTL::ComputeCommandEncoder", "useResource"): "metal::ComputeCommandEncoder::use_resource",
        ("MTL::ComputeCommandEncoder", "useResources"): "metal::ComputeCommandEncoder::use_resources",
        ("MTL::ComputeCommandEncoder", "sampleCountersInBuffer"): "metal::ComputeCommandEncoder::sample_counters",
        # Blit methods whose inventory name is not overloaded.
        ("MTL::BlitCommandEncoder", "copyIndirectCommandBuffer"): "metal::BlitCommandEncoder::copy_indirect_commands",
        ("MTL::BlitCommandEncoder", "optimizeIndirectCommandBuffer"): "metal::BlitCommandEncoder::optimize_indirect_commands",
        ("MTL::BlitCommandEncoder", "resetCommandsInBuffer"): "metal::BlitCommandEncoder::reset_indirect_commands",
        ("MTL::BlitCommandEncoder", "resetTextureAccessCounters"): "metal::BlitCommandEncoder::reset_texture_access_counters",
        ("MTL::BlitCommandEncoder", "sampleCountersInBuffer"): "metal::BlitCommandEncoder::sample_counters",
        ("MTL::BlitCommandEncoder", "synchronizeBuffer"): "metal::BlitCommandEncoder::synchronize_buffer",
        ("MTL::BlitCommandEncoder", "updateFence"): "metal::BlitCommandEncoder::update_fence",
        ("MTL::BlitCommandEncoder", "waitForFence"): "metal::BlitCommandEncoder::wait_for_fence",
        # Argument encoder safe slice bindings.
        ("MTL::ArgumentEncoder", "newArgumentEncoder"): "metal::ArgumentEncoder::new_argument_encoder",
        ("MTL::ArgumentEncoder", "setBuffer"): "metal::ArgumentEncoder::set_buffer",
        ("MTL::ArgumentEncoder", "setBuffers"): "metal::ArgumentEncoder::set_buffers",
        ("MTL::ArgumentEncoder", "setTexture"): "metal::ArgumentEncoder::set_texture",
        ("MTL::ArgumentEncoder", "setTextures"): "metal::ArgumentEncoder::set_textures",
        ("MTL::ArgumentEncoder", "setAccelerationStructure"): "metal::ArgumentEncoder::set_acceleration_structure",
        ("MTL::ArgumentEncoder", "setComputePipelineState"): "metal::ArgumentEncoder::set_compute_pipeline_state",
        ("MTL::ArgumentEncoder", "setComputePipelineStates"): "metal::ArgumentEncoder::set_compute_pipeline_states",
        ("MTL::ArgumentEncoder", "setDepthStencilState"): "metal::ArgumentEncoder::set_depth_stencil_state",
        ("MTL::ArgumentEncoder", "setDepthStencilStates"): "metal::ArgumentEncoder::set_depth_stencil_states",
        ("MTL::ArgumentEncoder", "setIndirectCommandBuffer"): "metal::ArgumentEncoder::set_indirect_command_buffer",
        ("MTL::ArgumentEncoder", "setIndirectCommandBuffers"): "metal::ArgumentEncoder::set_indirect_command_buffers",
        ("MTL::ArgumentEncoder", "setIntersectionFunctionTable"): "metal::ArgumentEncoder::set_intersection_function_table",
        ("MTL::ArgumentEncoder", "setIntersectionFunctionTables"): "metal::ArgumentEncoder::set_intersection_function_tables",
        ("MTL::ArgumentEncoder", "setRenderPipelineState"): "metal::ArgumentEncoder::set_render_pipeline_state",
        ("MTL::ArgumentEncoder", "setRenderPipelineStates"): "metal::ArgumentEncoder::set_render_pipeline_states",
        ("MTL::ArgumentEncoder", "setSamplerState"): "metal::ArgumentEncoder::set_sampler_state",
        ("MTL::ArgumentEncoder", "setSamplerStates"): "metal::ArgumentEncoder::set_sampler_states",
        ("MTL::ArgumentEncoder", "setVisibleFunctionTable"): "metal::ArgumentEncoder::set_visible_function_table",
        ("MTL::ArgumentEncoder", "setVisibleFunctionTables"): "metal::ArgumentEncoder::set_visible_function_tables",
        # Indirect render/compute command state. Unsafe tessellation pointer
        # overloads intentionally remain absent.
        ("MTL::IndirectRenderCommand", "clearBarrier"): "metal::IndirectRenderCommand::clear_barrier",
        ("MTL::IndirectRenderCommand", "reset"): "metal::IndirectRenderCommand::reset",
        ("MTL::IndirectRenderCommand", "setBarrier"): "metal::IndirectRenderCommand::set_barrier",
        ("MTL::IndirectRenderCommand", "setCullMode"): "metal::IndirectRenderCommand::set_cull_mode",
        ("MTL::IndirectRenderCommand", "setDepthBias"): "metal::IndirectRenderCommand::set_depth_bias",
        ("MTL::IndirectRenderCommand", "setDepthClipMode"): "metal::IndirectRenderCommand::set_depth_clip_mode",
        ("MTL::IndirectRenderCommand", "setDepthStencilState"): "metal::IndirectRenderCommand::set_depth_stencil_state",
        ("MTL::IndirectRenderCommand", "setFragmentBuffer"): "metal::IndirectRenderCommand::set_fragment_buffer",
        ("MTL::IndirectRenderCommand", "setFrontFacingWinding"): "metal::IndirectRenderCommand::set_front_facing_winding",
        ("MTL::IndirectRenderCommand", "setMeshBuffer"): "metal::IndirectRenderCommand::set_mesh_buffer",
        ("MTL::IndirectRenderCommand", "setObjectBuffer"): "metal::IndirectRenderCommand::set_object_buffer",
        ("MTL::IndirectRenderCommand", "setObjectThreadgroupMemoryLength"): "metal::IndirectRenderCommand::set_object_threadgroup_memory_length",
        ("MTL::IndirectRenderCommand", "setRenderPipelineState"): "metal::IndirectRenderCommand::set_render_pipeline_state",
        ("MTL::IndirectRenderCommand", "setTriangleFillMode"): "metal::IndirectRenderCommand::set_triangle_fill_mode",
        ("MTL::IndirectRenderCommand", "drawPrimitives"): "metal::IndirectRenderCommand::draw_primitives",
        ("MTL::IndirectRenderCommand", "drawIndexedPrimitives"): "metal::IndirectRenderCommand::draw_indexed_primitives",
        ("MTL::IndirectRenderCommand", "drawMeshThreadgroups"): "metal::IndirectRenderCommand::draw_mesh_threadgroups",
        ("MTL::IndirectRenderCommand", "drawMeshThreads"): "metal::IndirectRenderCommand::draw_mesh_threads",
        ("MTL::IndirectComputeCommand", "clearBarrier"): "metal::IndirectComputeCommand::clear_barrier",
        ("MTL::IndirectComputeCommand", "reset"): "metal::IndirectComputeCommand::reset",
        ("MTL::IndirectComputeCommand", "setBarrier"): "metal::IndirectComputeCommand::set_barrier",
        ("MTL::IndirectComputeCommand", "setComputePipelineState"): "metal::IndirectComputeCommand::set_compute_pipeline_state",
        ("MTL::IndirectComputeCommand", "setImageblockWidth"): "metal::IndirectComputeCommand::set_imageblock_size",
        ("MTL::IndirectComputeCommand", "setStageInRegion"): "metal::IndirectComputeCommand::set_stage_in_region",
        ("MTL::IndirectComputeCommand", "setThreadgroupMemoryLength"): "metal::IndirectComputeCommand::set_threadgroup_memory_length",
        ("MTL::IndirectComputeCommand", "concurrentDispatchThreadgroups"): "metal::IndirectComputeCommand::concurrent_dispatch_threadgroups",
        ("MTL::IndirectComputeCommand", "concurrentDispatchThreads"): "metal::IndirectComputeCommand::concurrent_dispatch_threads",
        # Metal IO typestate, callbacks, and checked file/resource ranges.
        ("MTL::IOCommandQueue", "commandBuffer"): "metal::IoCommandQueue::command_buffer",
        ("MTL::IOCommandQueue", "commandBufferWithUnretainedReferences"): "metal::IoCommandQueue::command_buffer",
        ("MTL::IOCommandQueue", "enqueueBarrier"): "metal::IoCommandQueue::enqueue_barrier",
        ("MTL::IOCommandQueue", "label"): "metal::IoCommandQueue::label",
        ("MTL::IOCommandQueue", "setLabel"): "metal::IoCommandQueue::set_label",
        ("MTL::IOCommandBuffer", "addBarrier"): "metal::IoCommandBuffer::add_barrier",
        ("MTL::IOCommandBuffer", "addCompletedHandler"): "metal::IoCommandBuffer::on_complete",
        ("MTL::IOCommandBuffer", "commit"): "metal::IoCommandBuffer::commit",
        ("MTL::IOCommandBuffer", "copyStatusToBuffer"): "metal::IoCommandBuffer::copy_status_to_buffer",
        ("MTL::IOCommandBuffer", "enqueue"): "metal::IoCommandBuffer::enqueue",
        ("MTL::IOCommandBuffer", "error"): "metal::IoCommandBuffer::error",
        ("MTL::IOCommandBuffer", "label"): "metal::IoCommandBuffer::label",
        ("MTL::IOCommandBuffer", "loadBuffer"): "metal::IoCommandBuffer::load_buffer",
        ("MTL::IOCommandBuffer", "loadBytes"): "metal::IoCommandQueue::read_bytes",
        ("MTL::IOCommandBuffer", "loadTexture"): "metal::IoCommandBuffer::load_texture",
        ("MTL::IOCommandBuffer", "popDebugGroup"): "metal::IoCommandBuffer::pop_debug_group",
        ("MTL::IOCommandBuffer", "pushDebugGroup"): "metal::IoCommandBuffer::push_debug_group",
        ("MTL::IOCommandBuffer", "setLabel"): "metal::IoCommandBuffer::set_label",
        ("MTL::IOCommandBuffer", "signalEvent"): "metal::IoCommandBuffer::signal_event",
        ("MTL::IOCommandBuffer", "status"): "metal::IoCommandBuffer::status",
        ("MTL::IOCommandBuffer", "tryCancel"): "metal::SubmittedIoCommandBuffer::try_cancel",
        ("MTL::IOCommandBuffer", "wait"): "metal::IoCommandBuffer::wait_for_event",
        ("MTL::IOCommandBuffer", "waitUntilCompleted"): "metal::SubmittedIoCommandBuffer::wait",
        ("MTL::IOFileHandle", "label"): "metal::IoFileHandle::label",
        ("MTL::IOFileHandle", "setLabel"): "metal::IoFileHandle::set_label",
        # Acceleration-structure descriptors and command encoding.
        ("MTL::AccelerationStructure", "gpuResourceID"): "metal::AccelerationStructure::gpu_resource_id",
        ("MTL::PrimitiveAccelerationStructureDescriptor", "geometryDescriptors"): "metal::PrimitiveAccelerationStructureDescriptor::geometry_descriptors_vec",
        ("MTL::PrimitiveAccelerationStructureDescriptor", "setGeometryDescriptors"): "metal::PrimitiveAccelerationStructureDescriptor::set_geometry_descriptors_slice",
        ("MTL::AccelerationStructureMotionTriangleGeometryDescriptor", "vertexBuffers"): "metal::AccelerationStructureMotionTriangleGeometryDescriptor::vertex_buffers_vec",
        ("MTL::AccelerationStructureMotionTriangleGeometryDescriptor", "setVertexBuffers"): "metal::AccelerationStructureMotionTriangleGeometryDescriptor::set_vertex_buffers_slice",
        ("MTL::AccelerationStructureMotionBoundingBoxGeometryDescriptor", "boundingBoxBuffers"): "metal::AccelerationStructureMotionBoundingBoxGeometryDescriptor::bounding_box_buffers_vec",
        ("MTL::AccelerationStructureMotionBoundingBoxGeometryDescriptor", "setBoundingBoxBuffers"): "metal::AccelerationStructureMotionBoundingBoxGeometryDescriptor::set_bounding_box_buffers_slice",
        ("MTL::AccelerationStructureMotionCurveGeometryDescriptor", "controlPointBuffers"): "metal::AccelerationStructureMotionCurveGeometryDescriptor::control_point_buffers_vec",
        ("MTL::AccelerationStructureMotionCurveGeometryDescriptor", "setControlPointBuffers"): "metal::AccelerationStructureMotionCurveGeometryDescriptor::set_control_point_buffers_slice",
        ("MTL::AccelerationStructureMotionCurveGeometryDescriptor", "radiusBuffers"): "metal::AccelerationStructureMotionCurveGeometryDescriptor::radius_buffers_vec",
        ("MTL::AccelerationStructureMotionCurveGeometryDescriptor", "setRadiusBuffers"): "metal::AccelerationStructureMotionCurveGeometryDescriptor::set_radius_buffers_slice",
        ("MTL::InstanceAccelerationStructureDescriptor", "instancedAccelerationStructures"): "metal::InstanceAccelerationStructureDescriptor::instanced_acceleration_structures_vec",
        ("MTL::InstanceAccelerationStructureDescriptor", "setInstancedAccelerationStructures"): "metal::InstanceAccelerationStructureDescriptor::set_instanced_acceleration_structures_slice",
        ("MTL::AccelerationStructureCommandEncoder", "buildAccelerationStructure"): "metal::AccelerationStructureEncoder::build",
        ("MTL::AccelerationStructureCommandEncoder", "copyAccelerationStructure"): "metal::AccelerationStructureEncoder::copy",
        ("MTL::AccelerationStructureCommandEncoder", "copyAndCompactAccelerationStructure"): "metal::AccelerationStructureEncoder::copy_and_compact",
        ("MTL::AccelerationStructureCommandEncoder", "sampleCountersInBuffer"): "metal::AccelerationStructureEncoder::sample_counters",
        ("MTL::AccelerationStructureCommandEncoder", "updateFence"): "metal::AccelerationStructureEncoder::update_fence",
        ("MTL::AccelerationStructureCommandEncoder", "useHeap"): "metal::AccelerationStructureEncoder::use_heap",
        ("MTL::AccelerationStructureCommandEncoder", "useHeaps"): "metal::AccelerationStructureEncoder::use_heaps",
        ("MTL::AccelerationStructureCommandEncoder", "useResource"): "metal::AccelerationStructureEncoder::use_resource",
        ("MTL::AccelerationStructureCommandEncoder", "useResources"): "metal::AccelerationStructureEncoder::use_resources",
        ("MTL::AccelerationStructureCommandEncoder", "waitForFence"): "metal::AccelerationStructureEncoder::wait_for_fence",
        # Device value queries and unique-name factories.
        ("MTL::Device", "architecture"): "metal::Device::architecture",
        ("MTL::Device", "counterSets"): "metal::Device::counter_sets",
        ("MTL::Device", "accelerationStructureSizes"): "metal::Device::acceleration_structure_sizes",
        ("MTL::Device", "convertSparsePixelRegions"): "metal::Device::sparse_pixel_regions_to_tiles",
        ("MTL::Device", "convertSparseTileRegions"): "metal::Device::sparse_tile_regions_to_pixels",
        ("MTL::Device", "newBinaryArchive"): "metal::Device::new_binary_archive",
        ("MTL::Device", "newCounterSampleBuffer"): "metal::Device::new_counter_sample_buffer",
        ("MTL::Device", "newDepthStencilState"): "metal::Device::new_depth_stencil_state",
        ("MTL::Device", "newEvent"): "metal::Device::new_event",
        ("MTL::Device", "newFence"): "metal::Device::new_fence",
        ("MTL::Device", "newHeap"): "metal::Device::new_heap",
        ("MTL::Device", "newIndirectCommandBuffer"): "metal::Device::new_indirect_command_buffer",
        ("MTL::Device", "newRasterizationRateMap"): "metal::Device::new_rasterization_rate_map",
        ("MTL::Device", "newSamplerState"): "metal::Device::new_sampler_state",
        # Binary archives, function stitching, and function tables.
        ("MTL::BinaryArchiveDescriptor", "alloc"): "metal::BinaryArchiveDescriptor::new",
        ("MTL::BinaryArchiveDescriptor", "init"): "metal::BinaryArchiveDescriptor::new",
        ("MTL::BinaryArchiveDescriptor", "setUrl"): "metal::BinaryArchiveDescriptor::set_file_path",
        ("MTL::BinaryArchiveDescriptor", "url"): "metal::BinaryArchiveDescriptor::file_path",
        ("MTL::BinaryArchive", "addComputePipelineFunctions"): "metal::BinaryArchive::add_compute_pipeline_functions",
        ("MTL::BinaryArchive", "addFunction"): "metal::BinaryArchive::add_function",
        ("MTL::BinaryArchive", "addLibrary"): "metal::BinaryArchive::add_stitched_library",
        ("MTL::BinaryArchive", "addMeshRenderPipelineFunctions"): "metal::BinaryArchive::add_mesh_render_pipeline_functions",
        ("MTL::BinaryArchive", "addRenderPipelineFunctions"): "metal::BinaryArchive::add_render_pipeline_functions",
        ("MTL::BinaryArchive", "addTileRenderPipelineFunctions"): "metal::BinaryArchive::add_tile_render_pipeline_functions",
        ("MTL::BinaryArchive", "serializeToURL"): "metal::BinaryArchive::serialize_to_file",
        ("MTL::BinaryArchive", "setLabel"): "metal::BinaryArchive::set_optional_label",
        ("MTL::FunctionStitchingInputNode", "alloc"): "metal::FunctionStitchingInputNode::new",
        ("MTL::FunctionStitchingFunctionNode", "alloc"): "metal::FunctionStitchingFunctionNode::new",
        ("MTL::FunctionStitchingFunctionNode", "arguments"): "metal::FunctionStitchingFunctionNode::arguments_vec",
        ("MTL::FunctionStitchingFunctionNode", "controlDependencies"): "metal::FunctionStitchingFunctionNode::control_dependencies_vec",
        ("MTL::FunctionStitchingFunctionNode", "setArguments"): "metal::FunctionStitchingFunctionNode::set_arguments_slice",
        ("MTL::FunctionStitchingFunctionNode", "setControlDependencies"): "metal::FunctionStitchingFunctionNode::set_control_dependencies_slice",
        ("MTL::FunctionStitchingGraph", "alloc"): "metal::FunctionStitchingGraph::new",
        ("MTL::FunctionStitchingGraph", "attributes"): "metal::FunctionStitchingGraph::attributes_vec",
        ("MTL::FunctionStitchingGraph", "nodes"): "metal::FunctionStitchingGraph::nodes_vec",
        ("MTL::FunctionStitchingGraph", "setAttributes"): "metal::FunctionStitchingGraph::set_attributes_slice",
        ("MTL::FunctionStitchingGraph", "setNodes"): "metal::FunctionStitchingGraph::set_nodes_slice",
        ("MTL::StitchedLibraryDescriptor", "alloc"): "metal::StitchedLibraryDescriptor::new",
        ("MTL::StitchedLibraryDescriptor", "init"): "metal::StitchedLibraryDescriptor::new",
        ("MTL::StitchedLibraryDescriptor", "binaryArchives"): "metal::StitchedLibraryDescriptor::binary_archives_vec",
        ("MTL::StitchedLibraryDescriptor", "functionGraphs"): "metal::StitchedLibraryDescriptor::function_graphs_vec",
        ("MTL::StitchedLibraryDescriptor", "functions"): "metal::StitchedLibraryDescriptor::functions_vec",
        ("MTL::StitchedLibraryDescriptor", "setBinaryArchives"): "metal::StitchedLibraryDescriptor::set_binary_archives_slice",
        ("MTL::StitchedLibraryDescriptor", "setFunctionGraphs"): "metal::StitchedLibraryDescriptor::set_function_graphs_slice",
        ("MTL::StitchedLibraryDescriptor", "setFunctions"): "metal::StitchedLibraryDescriptor::set_functions_slice",
        ("MTL::VisibleFunctionTableDescriptor", "alloc"): "metal::VisibleFunctionTableDescriptor::new",
        ("MTL::VisibleFunctionTableDescriptor", "init"): "metal::VisibleFunctionTableDescriptor::new",
        ("MTL::VisibleFunctionTableDescriptor", "visibleFunctionTableDescriptor"): "metal::VisibleFunctionTableDescriptor::new",
        ("MTL::IntersectionFunctionTableDescriptor", "alloc"): "metal::IntersectionFunctionTableDescriptor::new",
        ("MTL::IntersectionFunctionTableDescriptor", "init"): "metal::IntersectionFunctionTableDescriptor::new",
        ("MTL::IntersectionFunctionTableDescriptor", "intersectionFunctionTableDescriptor"): "metal::IntersectionFunctionTableDescriptor::new",
        ("MTL::VisibleFunctionTable", "gpuResourceID"): "metal::VisibleFunctionTable::gpu_resource_id",
        ("MTL::VisibleFunctionTable", "setFunction"): "metal::VisibleFunctionTable::set_function",
        ("MTL::VisibleFunctionTable", "setFunctions"): "metal::VisibleFunctionTable::set_functions",
        ("MTL::IntersectionFunctionTable", "gpuResourceID"): "metal::IntersectionFunctionTable::gpu_resource_id",
        ("MTL::IntersectionFunctionTable", "setBuffer"): "metal::IntersectionFunctionTable::set_buffer",
        ("MTL::IntersectionFunctionTable", "setBuffers"): "metal::IntersectionFunctionTable::set_buffers",
        ("MTL::IntersectionFunctionTable", "setFunction"): "metal::IntersectionFunctionTable::set_function",
        ("MTL::IntersectionFunctionTable", "setFunctions"): "metal::IntersectionFunctionTable::set_functions",
        ("MTL::IntersectionFunctionTable", "setVisibleFunctionTable"): "metal::IntersectionFunctionTable::set_visible_function_table",
        ("MTL::IntersectionFunctionTable", "setVisibleFunctionTables"): "metal::IntersectionFunctionTable::set_visible_function_tables",
        # Tensor pointer/configuration APIs collapse into checked Rust layouts.
        ("MTL::TensorExtents", "alloc"): "metal::CheckedTensorExtents::new",
        ("MTL::TensorExtents", "extentAtDimensionIndex"): "metal::CheckedTensorExtents::get",
        ("MTL::TensorExtents", "rank"): "metal::CheckedTensorExtents::rank",
        ("MTL::TensorDescriptor", "dimensions"): "metal::CheckedTensorDescriptor::new",
        ("MTL::TensorDescriptor", "setDimensions"): "metal::CheckedTensorDescriptor::new",
        ("MTL::TensorDescriptor", "strides"): "metal::CheckedTensorDescriptor::new",
        ("MTL::TensorDescriptor", "setStrides"): "metal::CheckedTensorDescriptor::new",
        ("MTL::TensorDescriptor", "dataType"): "metal::CheckedTensorDescriptor::new",
        ("MTL::TensorDescriptor", "setDataType"): "metal::CheckedTensorDescriptor::new",
        ("MTL::TensorDescriptor", "usage"): "metal::CheckedTensorDescriptor::new",
        ("MTL::TensorDescriptor", "setUsage"): "metal::CheckedTensorDescriptor::new",
        ("MTL::TensorDescriptor", "resourceOptions"): "metal::CheckedTensorDescriptor::new",
        ("MTL::TensorDescriptor", "setResourceOptions"): "metal::CheckedTensorDescriptor::new",
        # Auxiliary encoders preserve the CommandBuffer exclusive borrow.
        ("MTL::ParallelRenderCommandEncoder", "renderCommandEncoder"): "metal::ParallelRenderCommandEncoder::render_encoder",
        ("MTL::ParallelRenderCommandEncoder", "setColorStoreAction"): "metal::ParallelRenderCommandEncoder::set_color_store_action",
        ("MTL::ParallelRenderCommandEncoder", "setColorStoreActionOptions"): "metal::ParallelRenderCommandEncoder::set_color_store_action_options",
        ("MTL::ParallelRenderCommandEncoder", "setDepthStoreAction"): "metal::ParallelRenderCommandEncoder::set_depth_store_action",
        ("MTL::ParallelRenderCommandEncoder", "setDepthStoreActionOptions"): "metal::ParallelRenderCommandEncoder::set_depth_store_action_options",
        ("MTL::ParallelRenderCommandEncoder", "setStencilStoreAction"): "metal::ParallelRenderCommandEncoder::set_stencil_store_action",
        ("MTL::ParallelRenderCommandEncoder", "setStencilStoreActionOptions"): "metal::ParallelRenderCommandEncoder::set_stencil_store_action_options",
        ("MTL::ResourceStateCommandEncoder", "moveTextureMappingsFromTexture"): "metal::ResourceStateCommandEncoder::move_texture_mappings",
        ("MTL::ResourceStateCommandEncoder", "updateFence"): "metal::ResourceStateCommandEncoder::update_fence",
        ("MTL::ResourceStateCommandEncoder", "updateTextureMappings"): "metal::ResourceStateCommandEncoder::update_texture_mappings",
        ("MTL::ResourceStateCommandEncoder", "waitForFence"): "metal::ResourceStateCommandEncoder::wait_for_fence",
    }
)

ACTUAL_METHOD_SIGNATURES.update(
    {
        ("MTL::ComputeCommandEncoder", "setSamplerState", "void setSamplerState(const MTL::SamplerState* sampler, NS::UInteger index);"): "metal::ComputeCommandEncoder::set_sampler_state",
        ("MTL::ComputeCommandEncoder", "setSamplerState", "void setSamplerState(const MTL::SamplerState* sampler, float lodMinClamp, float lodMaxClamp, NS::UInteger index);"): "metal::ComputeCommandEncoder::set_sampler_state_with_lod",
        ("MTL::ComputeCommandEncoder", "setSamplerStates", "void setSamplerStates(const MTL::SamplerState* const samplers[], const float lodMinClamps[], const float lodMaxClamps[], NS::Range range);"): "metal::ComputeCommandEncoder::set_sampler_states_with_lod",
        ("MTL::ComputeCommandEncoder", "memoryBarrier", "void memoryBarrier(MTL::BarrierScope scope);"): "metal::ComputeCommandEncoder::memory_barrier",
        ("MTL::ComputeCommandEncoder", "memoryBarrier", "void memoryBarrier(const MTL::Resource* const resources[], NS::UInteger count);"): "metal::ComputeCommandEncoder::memory_barriers",
        ("MTL::ComputeCommandEncoder", "executeCommandsInBuffer", "void executeCommandsInBuffer(const MTL::IndirectCommandBuffer* indirectCommandBuffer, NS::Range executionRange);"): "metal::ComputeCommandEncoder::execute_commands",
        ("MTL::ComputeCommandEncoder", "executeCommandsInBuffer", "void executeCommandsInBuffer(const MTL::IndirectCommandBuffer* indirectCommandbuffer, const MTL::Buffer* indirectRangeBuffer, NS::UInteger indirectBufferOffset);"): "metal::ComputeCommandEncoder::execute_commands_indirect",
        ("MTL::ArgumentEncoder", "setArgumentBuffer", "void setArgumentBuffer(const MTL::Buffer* argumentBuffer, NS::UInteger offset);"): "metal::ArgumentEncoder::set_argument_buffer",
        ("MTL::ArgumentEncoder", "setArgumentBuffer", "void setArgumentBuffer(const MTL::Buffer* argumentBuffer, NS::UInteger startOffset, NS::UInteger arrayElement);"): "metal::ArgumentEncoder::set_argument_buffer_element",
        ("MTL::IndirectRenderCommand", "setVertexBuffer", "void setVertexBuffer(const MTL::Buffer* buffer, NS::UInteger offset, NS::UInteger index);"): "metal::IndirectRenderCommand::set_vertex_buffer",
        ("MTL::IndirectRenderCommand", "setVertexBuffer", "void setVertexBuffer(const MTL::Buffer* buffer, NS::UInteger offset, NS::UInteger stride, NS::UInteger index);"): "metal::IndirectRenderCommand::set_vertex_buffer_with_stride",
        ("MTL::IndirectComputeCommand", "setKernelBuffer", "void setKernelBuffer(const MTL::Buffer* buffer, NS::UInteger offset, NS::UInteger index);"): "metal::IndirectComputeCommand::set_kernel_buffer",
        ("MTL::IndirectComputeCommand", "setKernelBuffer", "void setKernelBuffer(const MTL::Buffer* buffer, NS::UInteger offset, NS::UInteger stride, NS::UInteger index);"): "metal::IndirectComputeCommand::set_kernel_buffer_with_stride",
        ("MTL::BlitCommandEncoder", "copyFromBuffer", "void copyFromBuffer(const MTL::Buffer* sourceBuffer, NS::UInteger sourceOffset, NS::UInteger sourceBytesPerRow, NS::UInteger sourceBytesPerImage, MTL::Size sourceSize, const MTL::Texture* destinationTexture, NS::UInteger destinationSlice, NS::UInteger destinationLevel, MTL::Origin destinationOrigin);"): "metal::BlitCommandEncoder::copy_buffer_to_texture",
        ("MTL::BlitCommandEncoder", "copyFromTexture", "void copyFromTexture(const MTL::Texture* sourceTexture, NS::UInteger sourceSlice, NS::UInteger sourceLevel, MTL::Origin sourceOrigin, MTL::Size sourceSize, const MTL::Texture* destinationTexture, NS::UInteger destinationSlice, NS::UInteger destinationLevel, MTL::Origin destinationOrigin);"): "metal::BlitCommandEncoder::copy_texture_region",
        ("MTL::BlitCommandEncoder", "copyFromTexture", "void copyFromTexture(const MTL::Texture* sourceTexture, NS::UInteger sourceSlice, NS::UInteger sourceLevel, MTL::Origin sourceOrigin, MTL::Size sourceSize, const MTL::Buffer* destinationBuffer, NS::UInteger destinationOffset, NS::UInteger destinationBytesPerRow, NS::UInteger destinationBytesPerImage);"): "metal::BlitCommandEncoder::copy_texture_to_buffer",
        ("MTL::BlitCommandEncoder", "copyFromTexture", "void copyFromTexture(const MTL::Texture* sourceTexture, NS::UInteger sourceSlice, NS::UInteger sourceLevel, const MTL::Texture* destinationTexture, NS::UInteger destinationSlice, NS::UInteger destinationLevel, NS::UInteger sliceCount, NS::UInteger levelCount);"): "metal::BlitCommandEncoder::copy_texture_subresources",
        ("MTL::BlitCommandEncoder", "optimizeContentsForCPUAccess", "void optimizeContentsForCPUAccess(const MTL::Texture* texture, NS::UInteger slice, NS::UInteger level);"): "metal::BlitCommandEncoder::optimize_texture_slice_for_cpu",
        ("MTL::BlitCommandEncoder", "optimizeContentsForGPUAccess", "void optimizeContentsForGPUAccess(const MTL::Texture* texture, NS::UInteger slice, NS::UInteger level);"): "metal::BlitCommandEncoder::optimize_texture_slice_for_gpu",
        ("MTL::Device", "newIOCommandQueue", "IOCommandQueue* newIOCommandQueue(const MTL::IOCommandQueueDescriptor* descriptor, NS::Error** error);"): "metal::Device::new_io_command_queue",
        ("MTL::Device", "newIOFileHandle", "IOFileHandle* newIOFileHandle(const NS::URL* url, NS::Error** error);"): "metal::Device::new_io_file_handle",
        ("MTL::Device", "newIOFileHandle", "IOFileHandle* newIOFileHandle(const NS::URL* url, MTL::IOCompressionMethod compressionMethod, NS::Error** error);"): "metal::Device::new_io_file_handle",
        ("MTL::Device", "newIOHandle", "IOFileHandle* newIOHandle(const NS::URL* url, NS::Error** error);"): "metal::Device::new_io_file_handle",
        ("MTL::Device", "newIOHandle", "IOFileHandle* newIOHandle(const NS::URL* url, MTL::IOCompressionMethod compressionMethod, NS::Error** error);"): "metal::Device::new_io_file_handle",
        ("MTL::CommandBuffer", "accelerationStructureCommandEncoder", "AccelerationStructureCommandEncoder* accelerationStructureCommandEncoder();"): "metal::CommandBuffer::acceleration_structure_encoder",
        ("MTL::CommandBuffer", "accelerationStructureCommandEncoder", "AccelerationStructureCommandEncoder* accelerationStructureCommandEncoder(const MTL::AccelerationStructurePassDescriptor* descriptor);"): "metal::CommandBuffer::acceleration_structure_encoder_with_descriptor",
        ("MTL::AccelerationStructureCommandEncoder", "refitAccelerationStructure", "void refitAccelerationStructure(const MTL::AccelerationStructure* sourceAccelerationStructure, const MTL::AccelerationStructureDescriptor* descriptor, const MTL::AccelerationStructure* destinationAccelerationStructure, const MTL::Buffer* scratchBuffer, NS::UInteger scratchBufferOffset);"): "metal::AccelerationStructureEncoder::refit",
        ("MTL::AccelerationStructureCommandEncoder", "refitAccelerationStructure", "void refitAccelerationStructure(const MTL::AccelerationStructure* sourceAccelerationStructure, const MTL::AccelerationStructureDescriptor* descriptor, const MTL::AccelerationStructure* destinationAccelerationStructure, const MTL::Buffer* scratchBuffer, NS::UInteger scratchBufferOffset, MTL::AccelerationStructureRefitOptions options);"): "metal::AccelerationStructureEncoder::refit",
        ("MTL::AccelerationStructureCommandEncoder", "writeCompactedAccelerationStructureSize", "void writeCompactedAccelerationStructureSize(const MTL::AccelerationStructure* accelerationStructure, const MTL::Buffer* buffer, NS::UInteger offset);"): "metal::AccelerationStructureEncoder::write_compacted_size_u32",
        ("MTL::AccelerationStructureCommandEncoder", "writeCompactedAccelerationStructureSize", "void writeCompactedAccelerationStructureSize(const MTL::AccelerationStructure* accelerationStructure, const MTL::Buffer* buffer, NS::UInteger offset, MTL::DataType sizeDataType);"): "metal::AccelerationStructureEncoder::write_compacted_size_u64",
        ("MTL::Device", "heapTextureSizeAndAlign", "SizeAndAlign heapTextureSizeAndAlign(const MTL::TextureDescriptor* desc);"): "metal::Device::heap_texture_size_and_align",
        ("MTL::Device", "heapAccelerationStructureSizeAndAlign", "SizeAndAlign heapAccelerationStructureSizeAndAlign(const MTL::AccelerationStructureDescriptor* descriptor);"): "metal::Device::heap_acceleration_structure_descriptor_size_and_align",
        ("MTL::Device", "newCommandQueue", "CommandQueue* newCommandQueue(const MTL::CommandQueueDescriptor* descriptor);"): "metal::Device::new_command_queue_from_descriptor",
        ("MTL::Device", "newArgumentEncoder", "ArgumentEncoder* newArgumentEncoder(const NS::Array* arguments);"): "metal::Device::new_argument_encoder",
        ("MTL::Device", "newArgumentEncoder", "ArgumentEncoder* newArgumentEncoder(const MTL::BufferBinding* bufferBinding);"): "metal::Device::new_argument_encoder_from_buffer_binding",
        ("MTL::Device", "newBuffer", "Buffer* newBuffer(const void* pointer, NS::UInteger length, MTL::ResourceOptions options);"): "metal::Device::new_buffer_with_bytes",
        ("MTL::Device", "newBuffer", "Buffer* newBuffer(NS::UInteger length, MTL::ResourceOptions options, MTL::SparsePageSize placementSparsePageSize);"): "metal::Device::new_placement_sparse_buffer",
        ("MTL::Device", "newSharedTexture", "Texture* newSharedTexture(const MTL::TextureDescriptor* descriptor);"): "metal::Device::new_shared_texture",
        ("MTL::Device", "newSharedTexture", "Texture* newSharedTexture(const MTL::SharedTextureHandle* sharedHandle);"): "metal::Device::new_shared_texture_from_handle",
        ("MTL::Device", "newDefaultLibrary", "Library* newDefaultLibrary();"): "metal::Device::new_default_library",
        ("MTL::Device", "newSharedEvent", "SharedEvent* newSharedEvent();"): "metal::Device::new_shared_event",
        ("MTL::Device", "newSharedEvent", "SharedEvent* newSharedEvent(const MTL::SharedEventHandle* sharedEventHandle);"): "metal::Device::new_shared_event_from_handle",
        ("MTL::Device", "newDynamicLibrary", "DynamicLibrary* newDynamicLibrary(const MTL::Library* library, NS::Error** error);"): "metal::Device::new_dynamic_library",
        ("MTL::Device", "functionHandle", "FunctionHandle* functionHandle(const MTL::Function* function);"): "metal::Device::function_handle",
        ("MTL::Device", "newAccelerationStructure", "AccelerationStructure* newAccelerationStructure(NS::UInteger size);"): "metal::Device::new_acceleration_structure",
        ("MTL::Device", "newAccelerationStructure", "AccelerationStructure* newAccelerationStructure(const MTL::AccelerationStructureDescriptor* descriptor);"): "metal::Device::new_acceleration_structure_from_descriptor",
        ("MTL::FunctionStitchingInputNode", "init", "FunctionStitchingInputNode* init();"): "metal::FunctionStitchingInputNode::new",
        ("MTL::FunctionStitchingInputNode", "init", "FunctionStitchingInputNode* init(NS::UInteger argument);"): "metal::FunctionStitchingInputNode::with_argument_index",
        ("MTL::FunctionStitchingFunctionNode", "init", "FunctionStitchingFunctionNode* init();"): "metal::FunctionStitchingFunctionNode::new",
        ("MTL::FunctionStitchingFunctionNode", "init", "FunctionStitchingFunctionNode* init(const NS::String* name, const NS::Array* arguments, const NS::Array* controlDependencies);"): "metal::FunctionStitchingFunctionNode::with_details",
        ("MTL::FunctionStitchingGraph", "init", "FunctionStitchingGraph* init();"): "metal::FunctionStitchingGraph::new",
        ("MTL::FunctionStitchingGraph", "init", "FunctionStitchingGraph* init(const NS::String* functionName, const NS::Array* nodes, const MTL::FunctionStitchingFunctionNode* outputNode, const NS::Array* attributes);"): "metal::FunctionStitchingGraph::with_details",
        ("MTL::IntersectionFunctionTable", "setOpaqueTriangleIntersectionFunction", "void setOpaqueTriangleIntersectionFunction(MTL::IntersectionFunctionSignature signature, NS::UInteger index);"): "metal::IntersectionFunctionTable::set_opaque_triangle_function",
        ("MTL::IntersectionFunctionTable", "setOpaqueTriangleIntersectionFunction", "void setOpaqueTriangleIntersectionFunction(MTL::IntersectionFunctionSignature signature, NS::Range range);"): "metal::IntersectionFunctionTable::set_opaque_triangle_function_range",
        ("MTL::IntersectionFunctionTable", "setOpaqueCurveIntersectionFunction", "void setOpaqueCurveIntersectionFunction(MTL::IntersectionFunctionSignature signature, NS::UInteger index);"): "metal::IntersectionFunctionTable::set_opaque_curve_function",
        ("MTL::IntersectionFunctionTable", "setOpaqueCurveIntersectionFunction", "void setOpaqueCurveIntersectionFunction(MTL::IntersectionFunctionSignature signature, NS::Range range);"): "metal::IntersectionFunctionTable::set_opaque_curve_function_range",
        ("MTL::TensorExtents", "init", "TensorExtents* init();"): "metal::CheckedTensorExtents::new",
        ("MTL::TensorExtents", "init", "TensorExtents* init(NS::UInteger rank, const NS::Integer* values);"): "metal::CheckedTensorExtents::new",
        ("MTL::Buffer", "newTensor", "Tensor* newTensor(const MTL::TensorDescriptor* descriptor, NS::UInteger offset, NS::Error** error);"): "metal::Buffer::new_tensor",
        ("MTL::CommandBuffer", "parallelRenderCommandEncoder", "ParallelRenderCommandEncoder* parallelRenderCommandEncoder(const MTL::RenderPassDescriptor* renderPassDescriptor);"): "metal::CommandBuffer::parallel_render_encoder",
        ("MTL::CommandBuffer", "resourceStateCommandEncoder", "ResourceStateCommandEncoder* resourceStateCommandEncoder();"): "metal::CommandBuffer::resource_state_encoder",
        ("MTL::CommandBuffer", "resourceStateCommandEncoder", "ResourceStateCommandEncoder* resourceStateCommandEncoder(const MTL::ResourceStatePassDescriptor* resourceStatePassDescriptor);"): "metal::CommandBuffer::resource_state_encoder_with_descriptor",
        ("MTL::ResourceStateCommandEncoder", "updateTextureMapping", "void updateTextureMapping(const MTL::Texture* texture, const MTL::SparseTextureMappingMode mode, const MTL::Region region, const NS::UInteger mipLevel, const NS::UInteger slice);"): "metal::ResourceStateCommandEncoder::update_texture_mapping",
        ("MTL::ResourceStateCommandEncoder", "updateTextureMapping", "void updateTextureMapping(const MTL::Texture* texture, const MTL::SparseTextureMappingMode mode, const MTL::Buffer* indirectBuffer, NS::UInteger indirectBufferOffset);"): "metal::ResourceStateCommandEncoder::update_texture_mapping_indirect",
    }
)

SUBSTITUTE_METHODS = {
    ("MTL::Buffer", "contents"),
    ("MTL::Buffer", "didModifyRange"),
    ("MTL::Texture", "getBytes"),
    ("MTL::CommandQueue", "commandBufferWithUnretainedReferences"),
    ("MTL::IOCommandQueue", "commandBufferWithUnretainedReferences"),
    ("MTL::IOCommandBuffer", "loadBytes"),
    ("MTL::Device", "newIOHandle"),
}

SLICE_SUBSTITUTE_METHODS = {
    ("MTL::LinkedFunctions", "setPrivateFunctions"),
    ("MTL4::StaticLinkingDescriptor", "setPrivateFunctionDescriptors"),
    ("MTL::FunctionDescriptor", "setBinaryArchives"),
    ("MTL4::StitchedFunctionDescriptor", "setFunctionDescriptors"),
    ("MTL4::RenderPassDescriptor", "setSamplePositions"),
    ("MTL::CompileOptions", "setLibraries"),
    ("MTL::CompileOptions", "setPreprocessorMacros"),
    ("MTL4::MachineLearningPipelineDescriptor", "setInputDimensions"),
    ("MTL::ComputeCommandEncoder", "setBuffers"),
    ("MTL::ComputeCommandEncoder", "setTextures"),
    ("MTL::CommandBuffer", "useResidencySets"),
    ("MTL::CommandQueue", "addResidencySets"),
    ("MTL::CommandQueue", "removeResidencySets"),
    ("MTL::ResidencySet", "addAllocations"),
    ("MTL::ResidencySet", "removeAllocations"),
    ("MTL::ComputeCommandEncoder", "setSamplerStates"),
    ("MTL::ComputeCommandEncoder", "setVisibleFunctionTables"),
    ("MTL::ComputeCommandEncoder", "setIntersectionFunctionTables"),
    ("MTL::ComputeCommandEncoder", "useHeaps"),
    ("MTL::ComputeCommandEncoder", "useResources"),
    ("MTL::ComputeCommandEncoder", "memoryBarrier"),
    ("MTL::ArgumentEncoder", "setBuffers"),
    ("MTL::ArgumentEncoder", "setTextures"),
    ("MTL::ArgumentEncoder", "setComputePipelineStates"),
    ("MTL::ArgumentEncoder", "setDepthStencilStates"),
    ("MTL::ArgumentEncoder", "setIndirectCommandBuffers"),
    ("MTL::ArgumentEncoder", "setIntersectionFunctionTables"),
    ("MTL::ArgumentEncoder", "setRenderPipelineStates"),
    ("MTL::ArgumentEncoder", "setSamplerStates"),
    ("MTL::ArgumentEncoder", "setVisibleFunctionTables"),
    ("MTL::PrimitiveAccelerationStructureDescriptor", "setGeometryDescriptors"),
    ("MTL::AccelerationStructureMotionTriangleGeometryDescriptor", "setVertexBuffers"),
    ("MTL::AccelerationStructureMotionBoundingBoxGeometryDescriptor", "setBoundingBoxBuffers"),
    ("MTL::AccelerationStructureMotionCurveGeometryDescriptor", "setControlPointBuffers"),
    ("MTL::AccelerationStructureMotionCurveGeometryDescriptor", "setRadiusBuffers"),
    ("MTL::InstanceAccelerationStructureDescriptor", "setInstancedAccelerationStructures"),
    ("MTL::AccelerationStructureCommandEncoder", "useHeaps"),
    ("MTL::AccelerationStructureCommandEncoder", "useResources"),
    ("MTL::Device", "convertSparsePixelRegions"),
    ("MTL::Device", "convertSparseTileRegions"),
    ("MTL::FunctionStitchingFunctionNode", "setArguments"),
    ("MTL::FunctionStitchingFunctionNode", "setControlDependencies"),
    ("MTL::FunctionStitchingGraph", "setAttributes"),
    ("MTL::FunctionStitchingGraph", "setNodes"),
    ("MTL::StitchedLibraryDescriptor", "setBinaryArchives"),
    ("MTL::StitchedLibraryDescriptor", "setFunctionGraphs"),
    ("MTL::StitchedLibraryDescriptor", "setFunctions"),
    ("MTL::VisibleFunctionTable", "setFunctions"),
    ("MTL::IntersectionFunctionTable", "setBuffers"),
    ("MTL::IntersectionFunctionTable", "setFunctions"),
    ("MTL::IntersectionFunctionTable", "setVisibleFunctionTables"),
    ("MTL::ResourceStateCommandEncoder", "updateTextureMappings"),
    ("MTL::RenderCommandEncoder", "setVertexBuffers"),
    ("MTL::RenderCommandEncoder", "setFragmentBuffers"),
    ("MTL::RenderCommandEncoder", "setTileBuffers"),
    ("MTL::RenderCommandEncoder", "setObjectBuffers"),
    ("MTL::RenderCommandEncoder", "setMeshBuffers"),
    ("MTL::RenderCommandEncoder", "setVertexTextures"),
    ("MTL::RenderCommandEncoder", "setFragmentTextures"),
    ("MTL::RenderCommandEncoder", "setTileTextures"),
    ("MTL::RenderCommandEncoder", "setObjectTextures"),
    ("MTL::RenderCommandEncoder", "setMeshTextures"),
    ("MTL::RenderCommandEncoder", "setVertexSamplerStates"),
    ("MTL::RenderCommandEncoder", "setFragmentSamplerStates"),
    ("MTL::RenderCommandEncoder", "setTileSamplerStates"),
    ("MTL::RenderCommandEncoder", "setObjectSamplerStates"),
    ("MTL::RenderCommandEncoder", "setMeshSamplerStates"),
    ("MTL::RenderCommandEncoder", "setVertexVisibleFunctionTables"),
    ("MTL::RenderCommandEncoder", "setFragmentVisibleFunctionTables"),
    ("MTL::RenderCommandEncoder", "setTileVisibleFunctionTables"),
    ("MTL::RenderCommandEncoder", "setVertexIntersectionFunctionTables"),
    ("MTL::RenderCommandEncoder", "setFragmentIntersectionFunctionTables"),
    ("MTL::RenderCommandEncoder", "setTileIntersectionFunctionTables"),
    ("MTL::RenderCommandEncoder", "setScissorRects"),
    ("MTL::RenderCommandEncoder", "setViewports"),
    ("MTL::RenderCommandEncoder", "setVertexAmplificationCount"),
    ("MTL::RenderCommandEncoder", "useHeaps"),
    ("MTL::RenderCommandEncoder", "useResources"),
    ("MTL4::PrimitiveAccelerationStructureDescriptor", "setGeometryDescriptors"),
    ("MTL4::CommandQueue", "commit"),
    ("MTL4::CommandQueue", "addResidencySets"),
    ("MTL4::CommandQueue", "removeResidencySets"),
    ("MTL4::CommandBuffer", "useResidencySets"),
    ("MTL4::CompilerTaskOptions", "setLookupArchives"),
    ("MTL4::StaticLinkingDescriptor", "setFunctionDescriptors"),
    ("MTL4::StaticLinkingDescriptor", "setPrivateFunctionDescriptors"),
    ("MTL4::StaticLinkingDescriptor", "setGroups"),
    ("MTL4::PipelineStageDynamicLinkingDescriptor", "setBinaryLinkedFunctions"),
    ("MTL4::PipelineStageDynamicLinkingDescriptor", "setPreloadedLibraries"),
    ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "setFragmentAdditionalBinaryFunctions"),
    ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "setMeshAdditionalBinaryFunctions"),
    ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "setObjectAdditionalBinaryFunctions"),
    ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "setTileAdditionalBinaryFunctions"),
    ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "setVertexAdditionalBinaryFunctions"),
}

for _parent, _methods in PIPELINE_DESCRIPTOR_METHODS.items():
    for _cpp_name, _rust_name in _methods.items():
        if _rust_name.startswith("set_") and (
            _rust_name.endswith("_slice")
            or _rust_name.endswith("_map")
        ):
            SLICE_SUBSTITUTE_METHODS.add((_parent, _cpp_name))

SLICE_SUBSTITUTE_SIGNATURES = {
    (
        "MTL::RasterizationRateMapDescriptor",
        "rasterizationRateMapDescriptor",
        "static RasterizationRateMapDescriptor* rasterizationRateMapDescriptor(MTL::Size screenSize, NS::UInteger layerCount, const MTL::RasterizationRateLayerDescriptor* const* layers);",
    ),
    (
        "MTL::Device",
        "newArgumentEncoder",
        "ArgumentEncoder* newArgumentEncoder(const NS::Array* arguments);",
    ),
    (
        "MTL::FunctionStitchingFunctionNode",
        "init",
        "FunctionStitchingFunctionNode* init(const NS::String* name, const NS::Array* arguments, const NS::Array* controlDependencies);",
    ),
    (
        "MTL::FunctionStitchingGraph",
        "init",
        "FunctionStitchingGraph* init(const NS::String* functionName, const NS::Array* nodes, const MTL::FunctionStitchingFunctionNode* outputNode, const NS::Array* attributes);",
    ),
    (
        "MTL::IntersectionFunctionTable",
        "setOpaqueTriangleIntersectionFunction",
        "void setOpaqueTriangleIntersectionFunction(MTL::IntersectionFunctionSignature signature, NS::Range range);",
    ),
    (
        "MTL::IntersectionFunctionTable",
        "setOpaqueCurveIntersectionFunction",
        "void setOpaqueCurveIntersectionFunction(MTL::IntersectionFunctionSignature signature, NS::Range range);",
    ),
    (
        "MTL::ResourceStateCommandEncoder",
        "updateTextureMapping",
        "void updateTextureMapping(const MTL::Texture* texture, const MTL::SparseTextureMappingMode mode, const MTL::Buffer* indirectBuffer, NS::UInteger indirectBufferOffset);",
    ),
    (
        "MTL::RenderCommandEncoder",
        "memoryBarrier",
        "void memoryBarrier(const MTL::Resource* const resources[], NS::UInteger count, MTL::RenderStages after, MTL::RenderStages before);",
    ),
    (
        "MTL::RenderCommandEncoder",
        "deprecated",
        "[[deprecated( )]] void useResources(const MTL::Resource* const resources[], NS::UInteger count, MTL::ResourceUsage usage);",
    ),
}

OWNED_COLLECTION_SUBSTITUTE_METHODS = {
    ("MTL::LinkedFunctions", "privateFunctions"),
    ("MTL4::StaticLinkingDescriptor", "privateFunctionDescriptors"),
    ("MTL::FunctionDescriptor", "binaryArchives"),
    ("MTL::CounterSet", "counters"),
    ("MTL::FunctionReflection", "bindings"),
    ("MTL::Tensor", "auxiliaryPlanes"),
    ("MTL4::StitchedFunctionDescriptor", "functionDescriptors"),
    ("MTL4::RenderPassDescriptor", "getSamplePositions"),
    ("MTL4::PipelineDataSetSerializer", "serializeAsPipelinesScript"),
    ("MTL::CommandBufferEncoderInfo", "debugSignposts"),
    ("MTL::CompileOptions", "libraries"),
    ("MTL::CompileOptions", "preprocessorMacros"),
    ("MTL4::MachineLearningPipelineReflection", "bindings"),
    ("MTL::Library", "functionNames"),
    ("MTL::Function", "functionConstantsDictionary"),
    ("MTL::Function", "stageInputAttributes"),
    ("MTL::Function", "vertexAttributes"),
    ("MTL::RasterizationRateLayerDescriptor", "horizontalSampleStorage"),
    ("MTL::RasterizationRateLayerDescriptor", "verticalSampleStorage"),
    ("MTL::RasterizationRateMapDescriptor", "layers"),
    ("MTL::ResidencySet", "allAllocations"),
    ("MTL::PrimitiveAccelerationStructureDescriptor", "geometryDescriptors"),
    ("MTL::AccelerationStructureMotionTriangleGeometryDescriptor", "vertexBuffers"),
    ("MTL::AccelerationStructureMotionBoundingBoxGeometryDescriptor", "boundingBoxBuffers"),
    ("MTL::AccelerationStructureMotionCurveGeometryDescriptor", "controlPointBuffers"),
    ("MTL::AccelerationStructureMotionCurveGeometryDescriptor", "radiusBuffers"),
    ("MTL::InstanceAccelerationStructureDescriptor", "instancedAccelerationStructures"),
    ("MTL::Device", "counterSets"),
    ("MTL::Device", "getDefaultSamplePositions"),
    ("MTL::FunctionStitchingFunctionNode", "arguments"),
    ("MTL::FunctionStitchingFunctionNode", "controlDependencies"),
    ("MTL::FunctionStitchingGraph", "attributes"),
    ("MTL::FunctionStitchingGraph", "nodes"),
    ("MTL::StitchedLibraryDescriptor", "binaryArchives"),
    ("MTL::StitchedLibraryDescriptor", "functionGraphs"),
    ("MTL::StitchedLibraryDescriptor", "functions"),
    ("MTL4::PrimitiveAccelerationStructureDescriptor", "geometryDescriptors"),
    ("MTL4::CompilerTaskOptions", "lookupArchives"),
    ("MTL4::StaticLinkingDescriptor", "functionDescriptors"),
    ("MTL4::StaticLinkingDescriptor", "privateFunctionDescriptors"),
    ("MTL4::StaticLinkingDescriptor", "groups"),
    ("MTL4::PipelineStageDynamicLinkingDescriptor", "binaryLinkedFunctions"),
    ("MTL4::PipelineStageDynamicLinkingDescriptor", "preloadedLibraries"),
    ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "fragmentAdditionalBinaryFunctions"),
    ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "meshAdditionalBinaryFunctions"),
    ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "objectAdditionalBinaryFunctions"),
    ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "tileAdditionalBinaryFunctions"),
    ("MTL4::RenderPipelineBinaryFunctionsDescriptor", "vertexAdditionalBinaryFunctions"),
    ("MTL::StructType", "members"),
    ("MTL::TensorReferenceType", "auxiliaryPlanes"),
    ("MTL::TensorBinding", "auxiliaryPlanes"),
}

for _parent, _methods in PIPELINE_DESCRIPTOR_METHODS.items():
    for _cpp_name, _rust_name in _methods.items():
        if (
            _rust_name.endswith("_vec")
            or _rust_name.endswith("_map")
        ):
            OWNED_COLLECTION_SUBSTITUTE_METHODS.add((_parent, _cpp_name))

CHECKED_INDEX_SUBSTITUTE_METHODS = {
    ("MTL::PipelineBufferDescriptorArray", "object"),
    ("MTL::PipelineBufferDescriptorArray", "setObject"),
    ("MTL::BlitPassSampleBufferAttachmentDescriptorArray", "object"),
    ("MTL::BlitPassSampleBufferAttachmentDescriptorArray", "setObject"),
    ("MTL::ResourceStatePassSampleBufferAttachmentDescriptorArray", "object"),
    ("MTL::ResourceStatePassSampleBufferAttachmentDescriptorArray", "setObject"),
    ("MTL::AccelerationStructurePassSampleBufferAttachmentDescriptorArray", "object"),
    ("MTL::AccelerationStructurePassSampleBufferAttachmentDescriptorArray", "setObject"),
    ("MTL::RenderPipelineColorAttachmentDescriptorArray", "object"),
    ("MTL::RenderPipelineColorAttachmentDescriptorArray", "setObject"),
    ("MTL::TileRenderPipelineColorAttachmentDescriptorArray", "object"),
    ("MTL::TileRenderPipelineColorAttachmentDescriptorArray", "setObject"),
}

RAII_SUBSTITUTE_METHODS = {
    ("MTL::CaptureScope", "beginScope"),
    ("MTL::CaptureScope", "endScope"),
    ("MTL::IOCommandBuffer", "addCompletedHandler"),
    ("MTL4::CommandBuffer", "beginCommandBuffer"),
    ("MTL4::CommandBuffer", "endCommandBuffer"),
    ("MTL4::CommandEncoder", "endEncoding"),
    ("MTL4::CommandQueue", "commit"),
}

POINTER_SUBSTITUTE_METHODS = {
    ("MTL::SharedEventListener", "dispatchQueue"),
    ("MTL::CaptureDescriptor", "captureObject"),
    ("MTL::CaptureDescriptor", "setCaptureObject"),
    ("MTL::RasterizationRateSampleArray", "object"),
    ("MTL::RasterizationRateSampleArray", "setObject"),
    ("MTL::RasterizationRateLayerArray", "object"),
    ("MTL::RasterizationRateLayerArray", "setObject"),
    ("MTL::Texture", "replaceRegion"),
    ("MTL::IOCommandBuffer", "loadBytes"),
    ("MTL::IOCommandQueue", "commandBufferWithUnretainedReferences"),
    ("MTL::Device", "newIOHandle"),
    ("MTL::BinaryArchiveDescriptor", "setUrl"),
    ("MTL::BinaryArchiveDescriptor", "url"),
    ("MTL::BinaryArchive", "serializeToURL"),
    ("MTL::RenderCommandEncoder", "setVertexBytes"),
    ("MTL::RenderCommandEncoder", "setFragmentBytes"),
    ("MTL::RenderCommandEncoder", "setTileBytes"),
    ("MTL::RenderCommandEncoder", "setObjectBytes"),
    ("MTL::RenderCommandEncoder", "setMeshBytes"),
}

for _parent, _cpp_name, _rust_name in METAL4_ACCELERATION_BUFFER_PROPERTIES:
    POINTER_SUBSTITUTE_METHODS.add(
        (_parent, f"set{_cpp_name[0].upper()}{_cpp_name[1:]}")
    )

POINTER_SUBSTITUTE_SIGNATURES = {
    (
        "MTL::Device",
        "newLibrary",
        "Library* newLibrary(const dispatch_data_t data, NS::Error** error);",
    ),
    (
        "MTL4::ArgumentTable",
        "setAddress",
        "void setAddress(MTL::GPUAddress gpuAddress, NS::UInteger bindingIndex);",
    ),
    (
        "MTL4::ArgumentTable",
        "setAddress",
        "void setAddress(MTL::GPUAddress gpuAddress, NS::UInteger stride, NS::UInteger bindingIndex);",
    ),
    (
        "MTL4::ArgumentTable",
        "setResource",
        "void setResource(MTL::ResourceID resourceID, NS::UInteger bindingIndex);",
    ),
    (
        "MTL4::ArgumentTable",
        "setSamplerState",
        "void setSamplerState(MTL::ResourceID resourceID, NS::UInteger bindingIndex);",
    ),
    (
        "MTL4::ArgumentTable",
        "setTexture",
        "void setTexture(MTL::ResourceID resourceID, NS::UInteger bindingIndex);",
    ),
    (
        "MTL::RasterizationRateLayerDescriptor",
        "init",
        "RasterizationRateLayerDescriptor* init(MTL::Size sampleCount, const float* horizontal, const float* vertical);",
    ),
    (
        "MTL::Device",
        "newBuffer",
        "Buffer* newBuffer(const void* pointer, NS::UInteger length, MTL::ResourceOptions options);",
    ),
    (
        "MTL::Device",
        "newBuffer",
        "Buffer* newBuffer(const void* pointer, NS::UInteger length, MTL::ResourceOptions options, void (^deallocator)(void*, NS::UInteger));",
    ),
    (
        "MTL::TensorExtents",
        "init",
        "TensorExtents* init(NS::UInteger rank, const NS::Integer* values);",
    ),
    (
        "MTL::SharedEventListener",
        "init",
        "SharedEventListener* init(const dispatch_queue_t dispatchQueue);",
    ),
}

TENSOR_DESCRIPTOR_SUBSTITUTE_METHODS = {
    ("MTL::TensorDescriptor", "dimensions"),
    ("MTL::TensorDescriptor", "setDimensions"),
    ("MTL::TensorDescriptor", "strides"),
    ("MTL::TensorDescriptor", "setStrides"),
    ("MTL::TensorDescriptor", "dataType"),
    ("MTL::TensorDescriptor", "setDataType"),
    ("MTL::TensorDescriptor", "usage"),
    ("MTL::TensorDescriptor", "setUsage"),
    ("MTL::TensorDescriptor", "resourceOptions"),
    ("MTL::TensorDescriptor", "setResourceOptions"),
}

SAFE_RETENTION_CONTRACT_METHODS = {
    ("MTL::CommandBufferDescriptor", "retainedReferences"),
    ("MTL::CommandBufferDescriptor", "setRetainedReferences"),
}

SCOPED_INDIRECT_COMMAND_SUBSTITUTE_METHODS = {
    ("MTL::IndirectCommandBuffer", "indirectComputeCommand"),
    ("MTL::IndirectCommandBuffer", "indirectRenderCommand"),
    ("MTL::IndirectCommandBuffer", "reset"),
}

SCOPED_ARGUMENT_SUBSTITUTE_METHODS = {
    ("MTL::ArgumentEncoder", "constantData"),
    ("MTL::IndirectRenderCommand", "drawIndexedPatches"),
    ("MTL::IndirectRenderCommand", "drawPatches"),
}

METAL4_COMMAND_SUBSTITUTE_METHODS = {
    ("MTL4::CommandQueue", "updateBufferMappings"),
    ("MTL4::CommandQueue", "copyBufferMappingsFromBuffer"),
    ("MTL4::CommandQueue", "updateTextureMappings"),
    ("MTL4::CommandQueue", "copyTextureMappingsFromTexture"),
    ("MTL4::RenderCommandEncoder", "drawIndexedPrimitives"),
    ("MTL4::RenderCommandEncoder", "drawPrimitives"),
    ("MTL4::RenderCommandEncoder", "drawMeshThreadgroups"),
    ("MTL4::RenderCommandEncoder", "executeCommandsInBuffer"),
    ("MTL4::RenderCommandEncoder", "setScissorRects"),
    ("MTL4::RenderCommandEncoder", "setVertexAmplificationCount"),
    ("MTL4::RenderCommandEncoder", "setViewports"),
    ("MTL4::ComputeCommandEncoder", "dispatchThreadgroups"),
    ("MTL4::ComputeCommandEncoder", "dispatchThreads"),
    ("MTL4::ComputeCommandEncoder", "executeCommandsInBuffer"),
}

METAL4_COMPLETION_SUBSTITUTE_METHODS = {
    ("MTL4::CommandBuffer", "resolveCounterHeap"),
    ("MTL4::CommandEncoder", "commandBuffer"),
    ("MTL4::CommandQueueDescriptor", "feedbackQueue"),
    ("MTL4::CommandQueueDescriptor", "setFeedbackQueue"),
    ("MTL4::CommitFeedback", "error"),
}

SAFE_RETENTION_CONTRACT_SIGNATURES = {
    (
        "MTL::CommandQueue",
        "commandBuffer",
        "CommandBuffer* commandBuffer(const MTL::CommandBufferDescriptor* descriptor);",
    ),
}

CALLBACK_SUBSTITUTE_SIGNATURES = {
    key
    for key in ACTUAL_METHOD_SIGNATURES
    if (key[0] == "MTL4::Compiler" and "CompilerTask*" in key[2])
    or (key[0] == "MTL::Device" and "CompletionHandler" in key[2])
    or (key[0] == "MTL::Library" and "completionHandler" in key[2])
    or key[0] == "MTL::LogState"
    or key[1] in {"addPresentedHandler", "notifyListener"}
}

PATH_SUBSTITUTE_SIGNATURES = {
    key
    for key in ACTUAL_METHOD_SIGNATURES
    if key[0] in {"MTL4::Compiler", "MTL::Device"} and "NS::URL*" in key[2]
}

PATH_SUBSTITUTE_METHODS = {
    ("MTL4::PipelineDataSetSerializer", "serializeAsArchiveAndFlushToURL"),
    ("MTL::DynamicLibrary", "serializeToURL"),
}

SAFE_COUNTER_HEAP_SUBSTITUTE_SIGNATURES = {
    (
        "MTL::Device",
        "newCounterHeap",
        "MTL4::CounterHeap* newCounterHeap(const MTL4::CounterHeapDescriptor* descriptor, NS::Error** error);",
    ),
}

IOSURFACE_SUBSTITUTE_SIGNATURES = {
    (
        "MTL::Device",
        "newTexture",
        "Texture* newTexture(const MTL::TextureDescriptor* descriptor, const IOSurfaceRef iosurface, NS::UInteger plane);",
    ),
}

TEXTURE_VIEW_POOL_SUBSTITUTE_SIGNATURES = {
    key
    for key in ACTUAL_METHOD_SIGNATURES
    if key[0] == "MTL::TextureViewPool"
    and ("TextureViewDescriptor" in key[2] or key[1] == "setTextureViewFromBuffer")
}

BLIT_SAFE_SUBSTITUTE_SIGNATURES = {
    key
    for key in ACTUAL_METHOD_SIGNATURES
    if key[0] == "MTL::BlitCommandEncoder"
    and key[1]
    in {
        "getTextureAccessCounters",
        "resolveCounters",
        "synchronizeResource",
    }
    or (
        key[0] == "MTL::BlitCommandEncoder"
        and "MTL::BlitOption options" in key[2]
    )
    or (
        key[0] == "MTL::BlitCommandEncoder"
        and key[1] == "copyFromTensor"
        and "TensorPlaneType" in key[2]
    )
}

METAL4_BLIT_SUBSTITUTE_SIGNATURES = {
    key
    for key, rust in ACTUAL_METHOD_SIGNATURES.items()
    if key[0] == "MTL4::ComputeCommandEncoder"
    and rust
    in {
        "metal4::RecordingComputeEncoder::copy_buffer_to_texture",
        "metal4::RecordingComputeEncoder::copy_texture_to_buffer",
        "metal4::RecordingComputeEncoder::copy_texture_region",
        "metal4::RecordingComputeEncoder::copy_tensor",
    }
}

METAL4_ACCELERATION_SUBSTITUTE_SIGNATURES = {
    key
    for key in ACTUAL_METHOD_SIGNATURES
    if key[0] == "MTL4::ComputeCommandEncoder"
    and "AccelerationStructure" in key[1]
}

CHECKED_TENSOR_ATTACHMENT_SUBSTITUTE_METHODS = {
    ("MTL::TensorBufferAttachments", "buffer"),
    ("MTL::TensorBufferAttachments", "offset"),
    ("MTL::TensorBufferAttachments", "setBuffer"),
}

RESOURCE_TAIL_SUBSTITUTE_METHODS = {
    ("MTL::Resource", "setOwner"),
    ("MTL::ResourceViewPool", "copyResourceViewsFromPool"),
}

CAPTURE_SINGLETON_SUBSTITUTE_METHODS = {
    ("MTL::CaptureManager", "alloc"),
    ("MTL::CaptureManager", "init"),
}

TENSOR_READ_WRITE_SUBSTITUTE_METHODS = {
    ("MTL::Tensor", "getBytes"),
    ("MTL::Tensor", "replaceSliceOrigin"),
}

ENCODER_FACTORY_SUBSTITUTE_METHODS = {
    ("MTL::CommandBuffer", "computeCommandEncoder"),
    ("MTL::CommandBuffer", "renderCommandEncoder"),
}

DEVICE_CHECKED_TENSOR_SIGNATURES = {
    key
    for key in ACTUAL_METHOD_SIGNATURES
    if key[0] == "MTL::Device" and key[1] in {"newTensor", "tensorSizeAndAlign"}
}

FUNCTION_CONSTANT_SUBSTITUTE_SIGNATURES = {
    key
    for key in ACTUAL_METHOD_SIGNATURES
    if key[0] == "MTL::FunctionConstantValues"
}

PIPELINE_STATE_SUBSTITUTE_METHODS = {
    ("MTL::ComputePipelineState", "functionHandle"),
    ("MTL::ComputePipelineState", "newComputePipelineStateWithBinaryFunctions"),
    ("MTL::RenderPipelineState", "functionHandle"),
    ("MTL::RenderPipelineState", "newRenderPipelineState"),
}

SHADER_TAIL_SUBSTITUTE_METHODS = {
    ("MTL::CounterSampleBuffer", "resolveCounterRange"),
    ("MTL::FunctionLogDebugLocation", "URL"),
}

FUNCTION_REFLECTION_SUBSTITUTE_SIGNATURES = {
    (
        "MTL::Function",
        "newArgumentEncoder",
        "ArgumentEncoder* newArgumentEncoder(NS::UInteger bufferIndex, const MTL::AutoreleasedArgument* reflection);",
    ),
}

SAFE_RENAME_SUBSTITUTE_SIGNATURES = {
    key
    for key in ACTUAL_METHOD_SIGNATURES
    if key[0]
    in {
        "MTL::Argument",
        "MTL::Binding",
        "MTL::TextureBinding",
        "MTL::RenderPipelineColorAttachmentDescriptor",
        "MTL::MeshRenderPipelineDescriptor",
        "MTL::VertexAttribute",
        "MTL::Attribute",
        "MTL::DepthStencilDescriptor",
        "MTL4::MeshRenderPipelineDescriptor",
        "MTL4::RenderPipelineDescriptor",
    }
    and key[1] == "deprecated"
}

RUNTIME_AVAILABILITY_PARENTS = {
    "MTL::TensorAuxiliaryPlaneDescriptorMap",
    "MTL::Tensor",
    "MTL::BlitPassDescriptor",
    "MTL::ResourceStatePassDescriptor",
    "MTL::PrimitiveAccelerationStructureDescriptor",
    "MTL::AccelerationStructureTriangleGeometryDescriptor",
    "MTL::AccelerationStructureBoundingBoxGeometryDescriptor",
    "MTL::MotionKeyframeData",
    "MTL::AccelerationStructureMotionTriangleGeometryDescriptor",
    "MTL::AccelerationStructureMotionBoundingBoxGeometryDescriptor",
    "MTL::AccelerationStructureCurveGeometryDescriptor",
    "MTL::AccelerationStructureMotionCurveGeometryDescriptor",
    "MTL::InstanceAccelerationStructureDescriptor",
    "MTL::IndirectInstanceAccelerationStructureDescriptor",
    "MTL::AccelerationStructurePassDescriptor",
    "MTL::VertexBufferLayoutDescriptorArray",
    "MTL::VertexAttributeDescriptorArray",
    "MTL::VertexDescriptor",
    "MTL::BufferLayoutDescriptorArray",
    "MTL::AttributeDescriptorArray",
    "MTL::StageInputOutputDescriptor",
    "MTL::CaptureDescriptor",
    "MTL::CaptureManager",
    "MTL::CaptureScope",
    "MTL::ComputePassDescriptor",
    "MTL::RasterizationRateLayerArray",
    "MTL::RasterizationRateLayerDescriptor",
    "MTL::RasterizationRateMap",
    "MTL::RasterizationRateMapDescriptor",
    "MTL::RasterizationRateSampleArray",
    "MTL::ResidencySet",
    "MTL::IOCommandBuffer",
    "MTL::IOCommandQueue",
    "MTL::IOFileHandle",
    "MTL::AccelerationStructure",
    "MTL::AccelerationStructureCommandEncoder",
    "MTL::BinaryArchive",
    "MTL::BinaryArchiveDescriptor",
    "MTL::FunctionStitchingFunctionNode",
    "MTL::FunctionStitchingGraph",
    "MTL::FunctionStitchingInputNode",
    "MTL::IntersectionFunctionTable",
    "MTL::IntersectionFunctionTableDescriptor",
    "MTL::StitchedLibraryDescriptor",
    "MTL::VisibleFunctionTable",
    "MTL::VisibleFunctionTableDescriptor",
    "MTL::ParallelRenderCommandEncoder",
    "MTL::ResourceStateCommandEncoder",
    "MTL::Drawable",
    "MTL::SharedEvent",
    "MTL::SharedEventListener",
    "MTL::StructMember",
    "MTL::StructType",
    "MTL::ArrayType",
    "MTL::PointerType",
    "MTL::TensorReferenceType",
    "MTL::TensorBinding",
    "MTL::TextureViewDescriptor",
}
RUNTIME_AVAILABILITY_PARENTS.update(PIPELINE_DESCRIPTOR_METHODS)

RUNTIME_AVAILABILITY_RUST_METHODS = {
    "metal::ArgumentDescriptor::new",
    "metal::FunctionDescriptor::new",
    "metal::SamplerDescriptor::r_address_mode",
    "metal::SamplerDescriptor::set_r_address_mode",
    "metal::SamplerState::gpu_resource_id",
    "metal::DepthStencilState::gpu_resource_id",
    "metal::FunctionHandle::gpu_resource_id",
    "metal::LinkedFunctions::new",
    "metal::IoScratchBufferAllocator::new_scratch_buffer",
    "metal::TextureViewPool::set_texture_view",
    "metal::RasterizationRateMap::physical_size",
    "metal::Device::new_default_library_from_bundle",
    "metal::CommandEncoder::barrier_after_queue_stages",
    "metal::Device::function_handle_from_binary",
    "metal::Device::new_mtl4_command_allocator",
    "metal::Device::new_mtl4_command_allocator_from_descriptor",
    "metal::Device::new_mtl4_compiler",
    "metal::Device::new_mtl4_command_queue_from_descriptor",
    "metal::Device::new_pipeline_data_set_serializer",
    "metal::Device::new_residency_set",
    "metal::Device::new_texture_view_pool",
    "metal::Device::size_of_counter_heap_entry",
    "metal::Resource::is_aliasable",
    "metal::Resource::make_aliasable",
    "metal::Resource::set_purgeable_state",
    "metal::ResourceViewPool::base_resource_id",
    "metal::Device::new_mtl4_argument_table",
    # Newer render-encoder selectors are weakly checked by the safe FFI layer.
    "metal::RenderCommandEncoder::dispatch_threads_per_tile",
    "metal::RenderCommandEncoder::draw_indexed_patches",
    "metal::RenderCommandEncoder::draw_indexed_patches_indirect",
    "metal::RenderCommandEncoder::draw_mesh_threadgroups",
    "metal::RenderCommandEncoder::draw_mesh_threadgroups_indirect",
    "metal::RenderCommandEncoder::draw_mesh_threads",
    "metal::RenderCommandEncoder::draw_patches",
    "metal::RenderCommandEncoder::draw_patches_indirect",
    "metal::RenderCommandEncoder::execute_commands",
    "metal::RenderCommandEncoder::execute_commands_indirect",
    "metal::RenderCommandEncoder::memory_barrier",
    "metal::RenderCommandEncoder::memory_barriers",
    "metal::RenderCommandEncoder::sample_counters",
    "metal::RenderCommandEncoder::set_color_attachment_map",
    "metal::RenderCommandEncoder::set_depth_clip_mode",
    "metal::RenderCommandEncoder::set_depth_test_bounds",
    "metal::RenderCommandEncoder::set_fragment_acceleration_structure",
    "metal::RenderCommandEncoder::set_mesh_buffer",
    "metal::RenderCommandEncoder::set_mesh_buffer_offset",
    "metal::RenderCommandEncoder::set_mesh_buffers",
    "metal::RenderCommandEncoder::set_mesh_bytes",
    "metal::RenderCommandEncoder::set_mesh_sampler",
    "metal::RenderCommandEncoder::set_mesh_samplers",
    "metal::RenderCommandEncoder::set_mesh_samplers_with_lod_clamps",
    "metal::RenderCommandEncoder::set_mesh_texture",
    "metal::RenderCommandEncoder::set_mesh_textures",
    "metal::RenderCommandEncoder::set_object_buffer",
    "metal::RenderCommandEncoder::set_object_buffer_offset",
    "metal::RenderCommandEncoder::set_object_buffers",
    "metal::RenderCommandEncoder::set_object_bytes",
    "metal::RenderCommandEncoder::set_object_sampler",
    "metal::RenderCommandEncoder::set_object_samplers",
    "metal::RenderCommandEncoder::set_object_samplers_with_lod_clamps",
    "metal::RenderCommandEncoder::set_object_texture",
    "metal::RenderCommandEncoder::set_object_textures",
    "metal::RenderCommandEncoder::set_object_threadgroup_memory_length",
    "metal::RenderCommandEncoder::set_threadgroup_memory_length",
    "metal::RenderCommandEncoder::set_tile_acceleration_structure",
    "metal::RenderCommandEncoder::set_tile_buffer",
    "metal::RenderCommandEncoder::set_tile_buffer_offset",
    "metal::RenderCommandEncoder::set_tile_buffers",
    "metal::RenderCommandEncoder::set_tile_bytes",
    "metal::RenderCommandEncoder::set_tile_intersection_function_table",
    "metal::RenderCommandEncoder::set_tile_intersection_function_tables",
    "metal::RenderCommandEncoder::set_tile_sampler",
    "metal::RenderCommandEncoder::set_tile_samplers",
    "metal::RenderCommandEncoder::set_tile_samplers_with_lod_clamps",
    "metal::RenderCommandEncoder::set_tile_texture",
    "metal::RenderCommandEncoder::set_tile_textures",
    "metal::RenderCommandEncoder::set_tile_visible_function_table",
    "metal::RenderCommandEncoder::set_tile_visible_function_tables",
    "metal::RenderCommandEncoder::set_vertex_acceleration_structure",
    "metal::RenderCommandEncoder::set_vertex_amplification",
    "metal::RenderCommandEncoder::texture_barrier",
    "metal::RenderCommandEncoder::tile_size",
    "metal::RenderCommandEncoder::update_fence",
    "metal::RenderCommandEncoder::use_heap",
    "metal::RenderCommandEncoder::use_heaps",
    "metal::RenderCommandEncoder::use_resource",
    "metal::RenderCommandEncoder::use_resources",
    "metal::RenderCommandEncoder::wait_for_fence",
}

FOUNDATION_CONSTANTS = {
    "BundleDidLoadNotification": "foundation::BUNDLE_DID_LOAD_NOTIFICATION",
    "BundleResourceRequestLowDiskSpaceNotification": "foundation::BUNDLE_RESOURCE_REQUEST_LOW_DISK_SPACE_NOTIFICATION",
    "ProcessInfoThermalStateDidChangeNotification": "foundation::PROCESS_INFO_THERMAL_STATE_DID_CHANGE_NOTIFICATION",
    "ProcessInfoPowerStateDidChangeNotification": "foundation::PROCESS_INFO_POWER_STATE_DID_CHANGE_NOTIFICATION",
    "ProcessInfoPerformanceProfileDidChangeNotification": "foundation::PROCESS_INFO_PERFORMANCE_PROFILE_DID_CHANGE_NOTIFICATION",
    "CocoaErrorDomain": "foundation::COCOA_ERROR_DOMAIN",
    "POSIXErrorDomain": "foundation::POSIX_ERROR_DOMAIN",
    "OSStatusErrorDomain": "foundation::OS_STATUS_ERROR_DOMAIN",
    "MachErrorDomain": "foundation::MACH_ERROR_DOMAIN",
    "UnderlyingErrorKey": "foundation::UNDERLYING_ERROR_KEY",
    "LocalizedDescriptionKey": "foundation::LOCALIZED_DESCRIPTION_KEY",
    "LocalizedFailureReasonErrorKey": "foundation::LOCALIZED_FAILURE_REASON_ERROR_KEY",
    "LocalizedRecoverySuggestionErrorKey": "foundation::LOCALIZED_RECOVERY_SUGGESTION_ERROR_KEY",
    "LocalizedRecoveryOptionsErrorKey": "foundation::LOCALIZED_RECOVERY_OPTIONS_ERROR_KEY",
    "RecoveryAttempterErrorKey": "foundation::RECOVERY_ATTEMPTER_ERROR_KEY",
    "HelpAnchorErrorKey": "foundation::HELP_ANCHOR_ERROR_KEY",
    "DebugDescriptionErrorKey": "foundation::DEBUG_DESCRIPTION_ERROR_KEY",
    "LocalizedFailureErrorKey": "foundation::LOCALIZED_FAILURE_ERROR_KEY",
    "StringEncodingErrorKey": "foundation::STRING_ENCODING_ERROR_KEY",
    "URLErrorKey": "foundation::URL_ERROR_KEY",
    "FilePathErrorKey": "foundation::FILE_PATH_ERROR_KEY",
    "NotFound": "foundation::NOT_FOUND",
    "IntegerMax": "foundation::INTEGER_MAX",
    "IntegerMin": "foundation::INTEGER_MIN",
    "UIntegerMax": "foundation::UINTEGER_MAX",
    "DeviceCertificationiPhonePerformanceGaming": "foundation::DeviceCertification::iphone_performance_gaming",
    "ProcessPerformanceProfileDefault": "foundation::ProcessPerformanceProfile::default_profile",
    "ProcessPerformanceProfileSustained": "foundation::ProcessPerformanceProfile::sustained",
}

FOUNDATION_AVAILABILITY_CONSTANTS = {
    "DeviceCertificationiPhonePerformanceGaming",
    "ProcessPerformanceProfileDefault",
    "ProcessPerformanceProfileSustained",
}

METAL_CONSTANTS = {
    "BinaryArchiveDomain": "metal::binary_archive_error_domain",
    "CounterErrorDomain": "metal::counter_error_domain",
    "CommonCounterTimestamp": "metal::CommonCounter::timestamp",
    "CommonCounterTessellationInputPatches": "metal::CommonCounter::tessellation_input_patches",
    "CommonCounterVertexInvocations": "metal::CommonCounter::vertex_invocations",
    "CommonCounterPostTessellationVertexInvocations": "metal::CommonCounter::post_tessellation_vertex_invocations",
    "CommonCounterClipperInvocations": "metal::CommonCounter::clipper_invocations",
    "CommonCounterClipperPrimitivesOut": "metal::CommonCounter::clipper_primitives_out",
    "CommonCounterFragmentInvocations": "metal::CommonCounter::fragment_invocations",
    "CommonCounterFragmentsPassed": "metal::CommonCounter::fragments_passed",
    "CommonCounterComputeKernelInvocations": "metal::CommonCounter::compute_kernel_invocations",
    "CommonCounterTotalCycles": "metal::CommonCounter::total_cycles",
    "CommonCounterVertexCycles": "metal::CommonCounter::vertex_cycles",
    "CommonCounterTessellationCycles": "metal::CommonCounter::tessellation_cycles",
    "CommonCounterPostTessellationVertexCycles": "metal::CommonCounter::post_tessellation_vertex_cycles",
    "CommonCounterFragmentCycles": "metal::CommonCounter::fragment_cycles",
    "CommonCounterRenderTargetWriteCycles": "metal::CommonCounter::render_target_write_cycles",
    "CommonCounterSetTimestamp": "metal::CommonCounterSet::timestamp",
    "CommonCounterSetStageUtilization": "metal::CommonCounterSet::stage_utilization",
    "CommonCounterSetStatistic": "metal::CommonCounterSet::statistic",
    "DeviceWasAddedNotification": "metal::DeviceNotificationName::device_was_added",
    "DeviceRemovalRequestedNotification": "metal::DeviceNotificationName::device_removal_requested",
    "DeviceWasRemovedNotification": "metal::DeviceNotificationName::device_was_removed",
    "CommandBufferEncoderInfoErrorKey": "metal::command_buffer_encoder_info_error_key",
    "IOErrorDomain": "metal::io_error_domain",
    "LogStateErrorDomain": "metal::log_state_error_domain",
    "TensorDomain": "metal::tensor_error_domain",
}

METAL_FUNCTIONS = {
    "IOCompressionContextDefaultChunkSize": "metal::IoCompressionContext::default_chunk_size",
    "IOCreateCompressionContext": "metal::IoCompressionContext::new",
    "IOCompressionContextAppendData": "metal::IoCompressionContext::append",
    "IOFlushAndDestroyCompressionContext": "metal::IoCompressionContext::finish",
}

METAL_GLOBAL_FUNCTIONS = {
    "CopyAllDevices": "metal::Device::all",
    "CopyAllDevicesWithObserver": "metal::Device::all_with_observer",
    "RemoveDeviceObserver": "metal::DeviceObserverRegistration",
}

METAL_VERSION_MACROS = {
    "METALCPP_VERSION_MAJOR": "metal::METAL_CPP_VERSION_MAJOR",
    "METALCPP_VERSION_MINOR": "metal::METAL_CPP_VERSION_MINOR",
    "METALCPP_VERSION_PATCH": "metal::METAL_CPP_VERSION_PATCH",
    "METALCPP_SUPPORTS_VERSION": "metal::metal_cpp_supports_version",
}

CALLBACK_ALIAS_MAPPINGS = {
    "MTL4::CommitFeedbackHandler": "metal4::SubmittedCommandBuffers::wait",
    "MTL4::CommitFeedbackHandlerFunction": "metal4::SubmittedCommandBuffers::wait",
    "MTL::FunctionCompletionHandlerFunction": "metal::Library::function_with_descriptor_async",
    "MTL::LogHandlerFunction": "metal::LogState::add_log_handler",
    "MTL::NewDynamicLibraryCompletionHandler": "metal4::Compiler::new_dynamic_library_async",
    "MTL::NewDynamicLibraryCompletionHandlerFunction": "metal4::Compiler::new_dynamic_library_async",
    "MTL4::NewComputePipelineStateCompletionHandler": "metal4::Compiler::new_compute_pipeline_async",
    "MTL4::NewComputePipelineStateCompletionHandlerFunction": "metal4::Compiler::new_compute_pipeline_async",
    "MTL4::NewRenderPipelineStateCompletionHandler": "metal4::Compiler::new_render_pipeline_async",
    "MTL4::NewRenderPipelineStateCompletionHandlerFunction": "metal4::Compiler::new_render_pipeline_async",
    "MTL4::NewBinaryFunctionCompletionHandler": "metal4::Compiler::new_binary_function_async",
    "MTL4::NewBinaryFunctionCompletionHandlerFunction": "metal4::Compiler::new_binary_function_async",
    "MTL4::NewMachineLearningPipelineStateCompletionHandler": "metal4::Compiler::new_machine_learning_pipeline_async",
    "MTL4::NewMachineLearningPipelineStateCompletionHandlerFunction": "metal4::Compiler::new_machine_learning_pipeline_async",
    "MTL::CommandBufferHandler": "metal::CommandBuffer::on_complete",
    "MTL::HandlerFunction": "metal::CommandBuffer::on_complete",
    "MTL::DeviceNotificationHandlerBlock": "metal::Device::all_with_observer",
    "MTL::DeviceNotificationHandlerFunction": "metal::Device::all_with_observer",
    "MTL::NewLibraryCompletionHandler": "metal::Device::new_library_from_source_async",
    "MTL::NewLibraryCompletionHandlerFunction": "metal::Device::new_library_from_source_async",
    "MTL::NewRenderPipelineStateCompletionHandler": "metal::Device::new_render_pipeline_async",
    "MTL::NewRenderPipelineStateCompletionHandlerFunction": "metal::Device::new_render_pipeline_async",
    "MTL::NewRenderPipelineStateWithReflectionCompletionHandler": "metal::Device::new_render_pipeline_with_reflection_async",
    "MTL::NewRenderPipelineStateWithReflectionCompletionHandlerFunction": "metal::Device::new_render_pipeline_with_reflection_async",
    "MTL::NewComputePipelineStateCompletionHandler": "metal::Device::new_compute_pipeline_async",
    "MTL::NewComputePipelineStateCompletionHandlerFunction": "metal::Device::new_compute_pipeline_async",
    "MTL::NewComputePipelineStateWithReflectionCompletionHandler": "metal::Device::new_compute_pipeline_with_reflection_async",
    "MTL::NewComputePipelineStateWithReflectionCompletionHandlerFunction": "metal::Device::new_compute_pipeline_with_reflection_async",
    "MTL::IOCommandBufferHandler": "metal::IoCommandBuffer::on_complete",
    "MTL::IOCommandBufferHandlerFunction": "metal::IoCommandBuffer::on_complete",
    "MTL::DrawablePresentedHandler": "metal::Drawable::on_presented",
    "MTL::DrawablePresentedHandlerFunction": "metal::Drawable::on_presented",
    "MTL::SharedEventNotificationBlock": "metal::SharedEvent::notify_at",
    "MTL::SharedEventNotificationFunction": "metal::SharedEvent::notify_at",
}

OWNED_ALIAS_SUBSTITUTES = {
    "MTL::AutoreleasedArgument": "metal::Argument",
    "MTL::AutoreleasedComputePipelineReflection": "metal::ComputePipelineReflection",
    "MTL::AutoreleasedRenderPipelineReflection": "metal::RenderPipelineReflection",
}

COMMIT_FEEDBACK_ALIASES = {
    "MTL4::CommitFeedbackHandler",
    "MTL4::CommitFeedbackHandlerFunction",
}

COMMIT_FEEDBACK_SUBSTITUTE_SIGNATURES = {
    key
    for key in ACTUAL_METHOD_SIGNATURES
    if key[0] == "MTL4::CommitOptions" and key[1] == "addFeedbackHandler"
}


def actual_mapping(declaration: dict[str, Any]) -> str | None:
    qualified_name = declaration["qualified_name"]
    if declaration["kind"] == "class":
        return ACTUAL_CLASSES.get(qualified_name) or FOUNDATION_SUBSTITUTE_CLASSES.get(qualified_name)
    if declaration["kind"] == "method":
        signature_mapping = ACTUAL_METHOD_SIGNATURES.get(
            (
                declaration.get("parent", ""),
                declaration["name"],
                declaration["signature"],
            )
        )
        return signature_mapping or ACTUAL_METHODS.get(
            (declaration.get("parent", ""), declaration["name"])
        ) or FOUNDATION_SUBSTITUTE_METHODS.get((declaration.get("parent", ""), declaration["name"]))
    if declaration["kind"] in {"alias", "enum", "options", "struct"}:
        if qualified_name in {"NS::ObserverBlock", "NS::ObserverFunction"}:
            return "foundation::NotificationCenter::add_observer"
        if qualified_name == "MTL::IOCompressionContext":
            return "metal::IoCompressionContext"
        if qualified_name in CALLBACK_ALIAS_MAPPINGS:
            return CALLBACK_ALIAS_MAPPINGS[qualified_name]
        if qualified_name in OWNED_ALIAS_SUBSTITUTES:
            return OWNED_ALIAS_SUBSTITUTES[qualified_name]
        value_mapping = ACTUAL_VALUES.get(qualified_name)
        if value_mapping:
            return value_mapping
    if declaration["kind"] == "field":
        if declaration.get("parent") == "NS::FastEnumerationState":
            return "foundation::Enumerator"
        parent_mapping = ACTUAL_VALUES.get(declaration.get("parent", ""))
        if parent_mapping:
            return f"{parent_mapping}::{snake_case(declaration['name'])}"
    if declaration["kind"] == "function" and declaration["name"] == "CreateSystemDefaultDevice":
        return "metal::Device::system_default"
    if declaration["kind"] == "function" and declaration["framework"] == "Metal":
        return METAL_GLOBAL_FUNCTIONS.get(declaration["name"]) or METAL_FUNCTIONS.get(
            declaration["name"]
        )
    if declaration["kind"] == "constant" and declaration["name"] == "MAX_TIMESTAMP_COUNTERS":
        return "metal::MAX_TIMESTAMP_COUNTERS"
    if declaration["kind"] == "constant" and declaration["framework"] == "Metal":
        return METAL_CONSTANTS.get(declaration["name"])
    if declaration["kind"] == "constant" and declaration["framework"] == "Foundation":
        return FOUNDATION_CONSTANTS.get(declaration["name"])
    if declaration["kind"] == "struct" and qualified_name == "NS::FastEnumerationState":
        return "foundation::Enumerator"
    if declaration["kind"] == "macro" and declaration["name"] == "MTLSTR":
        return "foundation::String::from"
    if declaration["kind"] == "macro":
        return METAL_VERSION_MACROS.get(declaration["name"])
    return None


def generated_value_mapping(declaration: dict[str, Any]) -> str | None:
    qualified_name = declaration["qualified_name"]
    if declaration["kind"] == "enum_member":
        manual = MANUAL_ENUM_MEMBERS.get((declaration.get("parent", ""), declaration["name"]))
        if manual:
            return manual
    if declaration["framework"] not in {"Foundation", "Metal"}:
        return None
    if declaration["kind"] in {"enum", "options"}:
        if qualified_name in MANUAL_TYPES:
            return None
        name = qualified_name.rsplit("::", 1)[-1]
        return f"{module_for(qualified_name)}::{name}"
    if declaration["kind"] == "enum_member":
        parent = declaration.get("parent", "")
        if parent in EXTENSIBLE_MANUAL_TYPES:
            name = parent.rsplit("::", 1)[-1]
            return f"metal::{name}::{declaration['name']}"
        if parent in MANUAL_TYPES:
            return None
        name = parent.rsplit("::", 1)[-1]
        return f"{module_for(parent)}::{name}::{declaration['name']}"
    return None


def generated_struct_mapping(declaration: dict[str, Any]) -> str | None:
    if declaration["framework"] not in {"Foundation", "Metal"}:
        return None
    if declaration["kind"] == "struct":
        qualified_name = declaration["qualified_name"]
        if qualified_name in MANUAL_STRUCTS:
            return None
        name = qualified_name.rsplit("::", 1)[-1]
        return f"{module_for(qualified_name)}::{name}"
    if declaration["kind"] == "field":
        parent = declaration.get("parent", "")
        if parent in MANUAL_STRUCTS:
            return None
        name = parent.rsplit("::", 1)[-1]
        return f"{module_for(parent)}::{name}::{snake_case(declaration['name'])}"
    return None


def generated_object_mapping(declaration: dict[str, Any]) -> str | None:
    if declaration["kind"] != "class" or "::" not in declaration["qualified_name"]:
        return None
    qualified_name = declaration["qualified_name"]
    if qualified_name not in generated_object_mapping.available:
        return None
    return f"{module_for(qualified_name)}::{qualified_name.rsplit('::', 1)[-1]}"


generated_object_mapping.available = set()  # type: ignore[attr-defined]


def mapping_for(
    declaration: dict[str, Any], generated_methods: dict[str, str], generated_aliases: dict[str, str]
) -> dict[str, str]:
    direct = actual_mapping(declaration)
    if direct:
        if (
            declaration.get("qualified_name") in FOUNDATION_SUBSTITUTE_CLASSES
            or (declaration.get("parent", ""), declaration["name"])
            in FOUNDATION_SUBSTITUTE_METHODS
            or declaration.get("qualified_name") == "NS::FastEnumerationState"
            or declaration.get("parent") == "NS::FastEnumerationState"
            or (declaration["kind"] == "macro" and declaration["name"] == "MTLSTR")
            or declaration.get("qualified_name") in {"NS::ObserverBlock", "NS::ObserverFunction"}
        ):
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The Foundation ownership, collection, pointer, or enumeration helper is replaced by an owned Rust value, trait, iterator, or RAII operation.",
                "evidence": "public Rust-native Foundation substitute with no Objective-C pointer exposure",
            }
        if declaration.get("qualified_name") in TYPESTATE_SUBSTITUTE_CLASSES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The cloneable protocol shell is replaced by a non-cloneable command-buffer or encoder typestate that enforces recording and submission order.",
                "evidence": "public typestate facade with exclusive encoder ownership",
            }
        if declaration.get("name") in METAL_GLOBAL_FUNCTIONS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The Objective-C device array and observer token are replaced by an owned Vec<Device>, a repeatable Rust closure, and an RAII registration.",
                "evidence": "owned device discovery plus panic-isolated RAII observer state",
            }
        if declaration.get("name") in METAL_VERSION_MACROS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The preprocessor-only reference version helper is represented by typed Rust constants and a const capability predicate.",
                "evidence": "canonical public Rust constants and const function",
            }
        if (
            declaration.get("qualified_name") == "MTL::IOCompressionContext"
            or declaration.get("name") in METAL_FUNCTIONS
        ):
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The raw compression context and free-function lifetime are replaced by an owned IoCompressionContext with new/append/finish and Drop cleanup.",
                "evidence": "safe RAII facade with checked byte slices and explicit terminal status",
            }
        if declaration.get("qualified_name") in COMMIT_FEEDBACK_ALIASES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The native commit-feedback callback is replaced by consuming submission typestate and an explicit wait that returns owned completion state.",
                "evidence": "SubmittedCommandBuffers::wait consumes the submission and preserves completion ordering",
            }
        if declaration.get("qualified_name") in CALLBACK_ALIAS_MAPPINGS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The native callback ABI alias is replaced by a panic-isolated Rust closure accepted by the safe facade.",
                "evidence": "safe closure adapter with owned callback state",
            }
        if declaration.get("qualified_name") in OWNED_ALIAS_SUBSTITUTES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The non-owning autoreleased C++ alias is replaced by the owned facade value returned from the safe factory.",
                "evidence": "owned RAII facade with no autorelease lifetime exposure",
            }
        method_key = (declaration.get("parent", ""), declaration["name"])
        method_signature_key = (
            declaration.get("parent", ""),
            declaration["name"],
            declaration["signature"],
        )
        if method_signature_key in CALLBACK_SUBSTITUTE_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The Objective-C block or C++ function callback is replaced by a panic-isolated FnOnce + Send + 'static closure and an owned result or task.",
                "evidence": "safe one-shot callback state machine with owned result/error conversion",
            }
        if method_signature_key in COMMIT_FEEDBACK_SUBSTITUTE_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The feedback block is installed internally by submit; consuming wait returns the owned completion Result without exposing feedback ABI or callback state.",
                "evidence": "submission typestate, panic-isolated feedback adapter, and consuming completion wait",
            }
        if (
            method_signature_key in PATH_SUBSTITUTE_SIGNATURES
            or method_key in PATH_SUBSTITUTE_METHODS
        ):
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The NSURL parameter is replaced by a borrowed Rust Path and converted inside the audited FFI boundary.",
                "evidence": "safe Rust path facade and selector-gated FFI conversion",
            }
        if method_signature_key in SAFE_RENAME_SUBSTITUTE_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The deprecated helper spelling is represented by the canonical checked Rust predicate.",
                "evidence": "selector-gated safe facade with explicit Boolean semantics",
            }
        if method_key in VALUE_HELPER_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The C++ convenience constructor or unchecked subscript is represented by a Default-capable Rust value with public typed fields or an owned fixed-size array.",
                "evidence": "generated safe Rust value representation with no raw storage access",
            }
        if method_signature_key in SAFE_COUNTER_HEAP_SUBSTITUTE_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The general descriptor factory is narrowed to a validated timestamp-counter count with an owned heap and a fixed upper bound.",
                "evidence": "checked timestamp counter factory with no descriptor or raw counter storage exposure",
            }
        if method_signature_key in IOSURFACE_SUBSTITUTE_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The raw IOSurfaceRef is replaced by an owned IoSurface identity with checked plane selection and nil/error conversion.",
                "evidence": "owned IOSurface RAII wrapper and selector-gated texture factory",
            }
        if method_signature_key in TEXTURE_VIEW_POOL_SUBSTITUTE_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The pool overload is replaced by a checked same-device descriptor/view construction with alignment, range, and index validation.",
                "evidence": "owned intermediate texture view and selector-gated pool update",
            }
        if method_signature_key in BLIT_SAFE_SUBSTITUTE_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The raw output-buffer, generic Resource, tensor-plane, or format-dependent blit overload is narrowed to checked typed resources and submission-bound owned staging results.",
                "evidence": "typed blit facade with range/layout validation and submission identity",
            }
        if method_signature_key in METAL4_BLIT_SUBSTITUTE_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "Parallel offsets, strides, slices, levels, and option overloads are replaced by validated image-layout and texture-selection value objects.",
                "evidence": "recording typestate blit with overflow, range, and subresource validation",
            }
        if method_signature_key in METAL4_ACCELERATION_SUBSTITUTE_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "Opaque MTL4 BufferRange GPU addresses are derived internally from typed Buffer ranges with device, alignment, span, and overlap checks.",
                "evidence": "recording typestate acceleration commands with no public GPU address",
            }
        if method_key in CHECKED_TENSOR_ATTACHMENT_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The plane-indexed attachment API is replaced by a checked plane, retained Buffer, validated offset, and complete TensorLayout proof.",
                "evidence": "owned checked tensor attachment map with no raw plane storage exposure",
            }
        if method_key in RESOURCE_TAIL_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The raw owner token or unchecked pool copy is replaced by an opaque owned identity and checked same-device Rust ranges.",
                "evidence": "typed resource ownership and range-checked pool facade",
            }
        if method_key in CAPTURE_SINGLETON_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "Standalone Objective-C manager allocation is replaced by the process capture singleton and scoped RAII capture operations.",
                "evidence": "owned capture session facade with no public allocation helper",
            }
        if method_key in TENSOR_READ_WRITE_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "Raw caller-owned tensor memory is replaced by checked origin/dimension/layout slices and owned Vec<u8> reads or borrowed &[u8] writes.",
                "evidence": "tensor span, plane, stride, storage-mode, and byte-length validation",
            }
        if method_key in ENCODER_FACTORY_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The native encoder shell is replaced by an exclusive borrow of the recording CommandBuffer and a Drop-balanced encoding lifetime.",
                "evidence": "non-cloneable encoder typestate prevents commit while recording",
            }
        if method_signature_key in DEVICE_CHECKED_TENSOR_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The independently mutable tensor descriptor and attachment pointers are replaced by checked layout and attachment proofs with same-device validation.",
                "evidence": "checked tensor factory with owned NSError conversion and no Objective-C collection exposure",
            }
        if method_signature_key in FUNCTION_CONSTANT_SUBSTITUTE_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The untyped constant pointer is replaced by an aligned checked byte slice with exact DataType width and range validation.",
                "evidence": "safe byte-slice constant facade with no raw pointer exposure",
            }
        if method_key in PIPELINE_STATE_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "Function identity and Objective-C binary-function arrays are replaced by checked name lookup or borrowed Rust slices with owned Error conversion.",
                "evidence": "safe pipeline derivation and function-handle facade",
            }
        if method_key in SHADER_TAIL_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The NSRange/NSData or NSURL result is replaced by a checked Rust range and owned optional Vec<u8> or String.",
                "evidence": "owned Rust result with selector and range validation",
            }
        if method_signature_key in FUNCTION_REFLECTION_SUBSTITUTE_SIGNATURES:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The autoreleased reflection out-value is returned as an owned optional Argument beside the safe encoder.",
                "evidence": "owned tuple result with checked argument-buffer index",
            }
        if method_key in RAII_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The independently callable begin/end pair is replaced by a scoped RAII operation that always balances teardown, including during unwinding.",
                "evidence": "safe closure facade and audited Drop guard",
            }
        if method_key in TENSOR_DESCRIPTOR_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "Independently mutable tensor dimensions, strides, data type, usage, and resource options are replaced by one validated CheckedTensorDescriptor construction.",
                "evidence": "checked tensor layout proof with exact byte-span validation",
            }
        if (
            method_key in SAFE_RETENTION_CONTRACT_METHODS
            or method_signature_key in SAFE_RETENTION_CONTRACT_SIGNATURES
        ):
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The facade accepts the descriptor only under its resource-retention invariant and rejects retainedReferences=false before creating a command buffer.",
                "evidence": "safe descriptor facade plus command-queue invariant check",
            }
        if method_key in SCOPED_INDIRECT_COMMAND_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The unchecked command lookup or NSRange reset is replaced by checked indexing/ranges and an HRTB-scoped recording closure so the command shell cannot escape.",
                "evidence": "bounds-checked scoped facade with non-escaping command lifetime",
            }
        if method_key in SCOPED_ARGUMENT_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "Raw constant storage or indirect patch command shells are replaced by HRTB-scoped slices/recording closures with complete offset and footprint checks.",
                "evidence": "non-escaping command lifetime and checked CPU-visible byte storage",
            }
        if method_key in METAL4_COMMAND_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "Raw GPU addresses, pointer arrays, and explicit operation counts are replaced by typed Buffer ranges and checked Rust slices on a recording typestate encoder.",
                "evidence": "non-cloneable recording facade with range, device, and operation-slice validation",
            }
        if method_key in METAL4_COMPLETION_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "Raw buffer ranges, encoder back-references, dispatch queues, and feedback NSError are absorbed by recording/submission typestate and a consuming completion Result.",
                "evidence": "submission-bound staging, exclusive recording borrow, and owned completion error",
            }
        if method_key == ("MTL4::CounterHeap", "resolveCounterRange"):
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "CPU-side direct resolve is replaced by RecordingCommandBuffer staging and CompletedCommandBuffers resolution bound to the same submission identity.",
                "evidence": "submission-bound staging readback rejects identity mismatch and returns owned Vec<u64>",
            }
        if method_key in CHECKED_INDEX_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The unchecked Objective-C indexed collection access is replaced by a bounds-checked Rust operation.",
                "evidence": "safe checked-index facade and selector-gated FFI wrapper",
            }
        if method_key in OWNED_COLLECTION_SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The Objective-C collection or borrowed storage is copied into an owned Rust Vec or other checked collection.",
                "evidence": "owned Rust collection facade with no Objective-C collection exposure",
            }
        if (
            method_key in POINTER_SUBSTITUTE_METHODS
            or method_signature_key in POINTER_SUBSTITUTE_SIGNATURES
        ):
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The raw object/pointer representation is replaced by a typed target, checked slice, or owned Rust value.",
                "evidence": "safe typed facade with range and lifetime validation",
            }
        if (
            method_key in SLICE_SUBSTITUTE_METHODS
            or method_signature_key in SLICE_SUBSTITUTE_SIGNATURES
        ):
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "Parallel C pointer arrays and explicit counts/ranges are replaced by a checked Rust slice.",
                "evidence": "safe slice facade, checked element/range validation, and audited FFI wrapper",
            }
        if (
            declaration["framework"] == "MetalFX"
            or declaration["qualified_name"].startswith("MTL4::")
            or declaration.get("parent", "") in RUNTIME_AVAILABILITY_PARENTS
            or direct in RUNTIME_AVAILABILITY_RUST_METHODS
            or declaration["name"] in FOUNDATION_AVAILABILITY_CONSTANTS
            or (declaration["kind"] == "constant" and declaration["name"] in METAL_CONSTANTS)
            or direct in {"metal::Device::capability", "metal::Device::numeric_property"}
            or direct.endswith("::shader_validation")
            or direct in {
                "metal::RenderPipelineDescriptor::options",
                "metal::RenderPipelineDescriptor::set_options",
                "metal::RenderPassDescriptor::options",
                "metal::RenderPassDescriptor::set_options",
                "metal::RenderPassDescriptor::sample_positions",
                "metal::RenderPassDescriptor::set_sample_positions",
                "metal::Device::supports_family",
                "metal::Device::supports_feature_set",
                "metal::Device::supports_counter_sampling",
                "metal::Device::supports_rasterization_rate_map",
                "metal::Device::supports_vertex_amplification_count",
                "metal::Device::should_maximize_concurrent_compilation",
                "metal::Device::set_should_maximize_concurrent_compilation",
                "metal::Device::default_sample_positions",
                "metal::Device::heap_acceleration_structure_size_and_align",
                "metal::Device::sparse_tile_size",
                "metal::RenderCommandEncoder::set_depth_clip_mode",
                "metal::RenderCommandEncoder::set_depth_test_bounds",
                "metal::RenderCommandEncoder::tile_size",
                "metal::RenderCommandEncoder::texture_barrier",
                "metal::BlitCommandEncoder::optimize_texture_for_cpu",
                "metal::BlitCommandEncoder::optimize_texture_for_gpu",
                "metal::ComputeCommandEncoder::set_buffer_with_stride",
                "metal::ComputeCommandEncoder::set_buffer_offset_with_stride",
                "metal::ComputeCommandEncoder::set_bytes_with_stride",
                "metal::ComputeCommandEncoder::set_stage_in_region_indirect",
                "metal::Buffer::new_tensor",
                "metal::Device::new_mtl4_command_buffer",
                "metal::Device::new_mtl4_command_queue",
            }
        ):
            return {
                "status": "availability",
                "rust": direct,
                "availability": "The safe facade checks runtime framework or selector support before use.",
                "evidence": "safe facade, audited FFI wrapper, and runtime capability check",
            }
        if (declaration.get("parent", ""), declaration["name"]) in SUBSTITUTE_METHODS:
            return {
                "status": "substitute",
                "rust": direct,
                "notes": "The raw mapped-memory or caller-owned output pointer is replaced by checked CPU writes or submission-bound staging readback.",
                "evidence": "safe facade, audited FFI wrapper, and submission identity validation",
            }
        return {
            "status": "implemented",
            "rust": direct,
            "evidence": "safe facade and audited FFI wrapper",
        }

    generated_value = generated_value_mapping(declaration)
    if generated_value:
        return {
            "status": "implemented",
            "rust": generated_value,
            "evidence": "generated safe scalar wrapper with checked integer representation",
        }

    generated_struct = generated_struct_mapping(declaration)
    if generated_struct:
        return {
            "status": "implemented",
            "rust": generated_struct,
            "evidence": "generated safe Rust value representation for a plain Metal struct",
        }

    generated_alias = generated_aliases.get(declaration["id"])
    if generated_alias:
        return {
            "status": "substitute",
            "rust": generated_alias,
            "notes": "The C++ alias is represented by its owned object wrapper or safe Rust scalar/value type.",
            "evidence": "safe Rust type substitution with no raw pointer or callback ABI exposure",
        }

    generated_object = generated_object_mapping(declaration)
    if generated_object:
        return {
            "status": "implemented",
            "rust": generated_object,
            "evidence": "generated opaque owned RAII wrapper; methods are covered separately",
        }

    generated_method = generated_methods.get(declaration["id"])
    if generated_method:
        return {
            "status": "availability",
            "rust": generated_method,
            "availability": "Returns ErrorKind::Unsupported when the runtime object does not expose the selector; nullable values remain a separate Option.",
            "evidence": "canonical facade wrapper over a selector-gated safe FFI method",
        }

    return {
        "status": "unimplemented",
        "reason": "No audited safe facade mapping has been implemented yet.",
        "evidence": "metal-cpp declaration inventory",
    }


def render_markdown(inventory: dict[str, Any], mappings: dict[str, dict[str, str]]) -> str:
    counts = Counter(mapping["status"] for mapping in mappings.values())
    by_framework: dict[str, Counter[str]] = {}
    by_header: dict[tuple[str, str], Counter[str]] = {}
    by_kind: dict[tuple[str, str], Counter[str]] = {}
    for declaration in inventory["declarations"]:
        status = mappings[declaration["id"]]["status"]
        framework = declaration["framework"]
        by_framework.setdefault(framework, Counter())[status] += 1
        by_header.setdefault((framework, declaration["header"]), Counter())[status] += 1
        by_kind.setdefault((framework, declaration["kind"]), Counter())[status] += 1

    lines = [
        "# API coverage",
        "",
        "This file is generated from `api/metal-cpp-inventory.json` and",
        "`api/coverage.json`. The ledger has one explicit entry for every public",
        "declaration in the local Apple metal-cpp snapshot.",
        "",
        f"Reference digest: `{inventory['reference']['content_sha256']}`.",
        "",
        "Statuses:",
        "",
        "- `implemented`: a pinned/generated or handwritten audited FFI mapping exists; the public facade may group several C++ overloads into one checked Rust operation.",
        "- `availability`: an implemented API is represented, but object creation is gated by the Apple framework/runtime capability query.",
        "- `substitute`: C++ ownership, helper, scalar, or pointer shape is",
        "  grouped into a safe Rust value or RAII abstraction.",
        "- `unimplemented`: no audited safe facade mapping exists yet.",
        "",
        "Generated Metal bindings are implementation sources behind",
        "`metal-rust-ffi`; they are not re-exported as raw Objective-C APIs.",
        "The `rust` target in the ledger preserves selector-level traceability,",
        "while the evidence and notes identify the safe facade grouping or",
        "substitution that callers actually use.",
        "",
        f"Total declarations: **{len(mappings)}**.",
        f"Implemented: **{counts['implemented']}**; availability-gated: **{counts['availability']}**; substituted: **{counts['substitute']}**; unimplemented: **{counts['unimplemented']}**.",
        "",
        "| Framework | Implemented | Availability | Substitute | Unimplemented | Total |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for framework in sorted(by_framework):
        counter = by_framework[framework]
        total = sum(counter.values())
        lines.append(
            f"| {framework} | {counter['implemented']} | {counter['availability']} | {counter['substitute']} | {counter['unimplemented']} | {total} |"
        )
    lines += [
        "",
        "## Header summary",
        "",
        "Each reference header is retained in the ledger so a new or removed",
        "header cannot disappear behind a framework-level percentage.",
        "",
        "| Framework | Header | Implemented | Availability | Substitute | Unimplemented | Total |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for (framework, header), counter in sorted(by_header.items()):
        total = sum(counter.values())
        lines.append(
            f"| {framework} | `{header}` | {counter['implemented']} | {counter['availability']} | {counter['substitute']} | {counter['unimplemented']} | {total} |"
        )
    lines += [
        "",
        "## Declaration-kind summary",
        "",
        "The machine-readable inventory preserves the original qualified name",
        "and signature for every class, method, enum, option, field, constant,",
        "alias, function, and macro.",
        "",
        "| Framework | Kind | Implemented | Availability | Substitute | Unimplemented | Total |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for (framework, kind), counter in sorted(by_kind.items()):
        total = sum(counter.values())
        lines.append(
            f"| {framework} | `{kind}` | {counter['implemented']} | {counter['availability']} | {counter['substitute']} | {counter['unimplemented']} | {total} |"
        )
    lines += [
        "",
        "The machine-readable ledger is checked with:",
        "",
        "```sh",
        "python3 scripts/generate_api_inventory.py --check",
        "python3 scripts/check-api-coverage.py",
        "```",
        "",
        "A changed reference digest requires regenerating the inventory and reviewing every new or removed ID.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=Path("api/metal-cpp-inventory.json"))
    parser.add_argument("--coverage", type=Path, default=Path("api/coverage.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/API_COVERAGE.md"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    declarations = inventory["declarations"]
    generated_methods = generated_facade_method_paths(declarations)
    generated_aliases = generated_facade_alias_paths(declarations)
    generated_object_mapping.available = available_object_names(declarations)  # type: ignore[attr-defined]
    mappings = {
        declaration["id"]: mapping_for(declaration, generated_methods, generated_aliases)
        for declaration in declarations
    }
    coverage = {
        "schema": 2,
        "description": "One explicit safe-Rust mapping for every declaration in the local metal-cpp inventory.",
        "reference_sha256": inventory["reference"]["content_sha256"],
        "generated_by": "scripts/generate_api_coverage.py",
        "mappings": dict(sorted(mappings.items())),
    }
    coverage_text = json.dumps(coverage, indent=2, sort_keys=True) + "\n"
    markdown_text = render_markdown(inventory, mappings)
    if args.check:
        stale = []
        if not args.coverage.is_file() or args.coverage.read_text(encoding="utf-8") != coverage_text:
            stale.append(args.coverage)
        if not args.markdown.is_file() or args.markdown.read_text(encoding="utf-8") != markdown_text:
            stale.append(args.markdown)
        if stale:
            for path in stale:
                print(f"generated coverage artifact is stale: {path}", file=sys.stderr)
            return 1
        print(f"coverage artifacts are current for {len(mappings)} mappings")
        return 0

    args.coverage.write_text(coverage_text, encoding="utf-8")
    args.markdown.write_text(markdown_text, encoding="utf-8")
    print(f"generated {len(mappings)} mappings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
