#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Per-node audio level sampling for external / PipeWire patchbay nodes.
#
# Carla's engine only exposes peak values for its own plugins. External nodes
# (PipeWire clients, virtual BUS sinks, hardware I/O, monitors...) have no such
# API, so we sample their real levels ourselves using the exact same mechanism
# as pavucontrol: a PulseAudio peak-detect recording stream
# (PA_STREAM_PEAK_DETECT). The server runs a max-resampler and returns a single
# float per fragment, so no audio is transported.
#
# A non-threaded pa_mainloop is pumped from the GUI thread (see process()), so
# no locking is needed. The streams we create are tagged ("Clarameter.<node>" /
# app name "Clara Meters") so the frontend can hide them from the patchbay.
# ------------------------------------------------------------------------------------------------------------

import ctypes
import ctypes.util
import time

# --- libpulse constants -------------------------------------------------------------------------------------

PA_CONTEXT_UNCONNECTED = 0
PA_CONTEXT_CONNECTING = 1
PA_CONTEXT_AUTHORIZING = 2
PA_CONTEXT_SETTING_NAME = 3
PA_CONTEXT_READY = 4
PA_CONTEXT_FAILED = 5
PA_CONTEXT_TERMINATED = 6

PA_STREAM_UNCONNECTED = 0
PA_STREAM_CREATING = 1
PA_STREAM_READY = 2
PA_STREAM_FAILED = 3
PA_STREAM_TERMINATED = 4

PA_SAMPLE_FLOAT32LE = 5

PA_STREAM_DONT_MOVE = 0x0200
PA_STREAM_PEAK_DETECT = 0x0800
PA_STREAM_ADJUST_LATENCY = 0x2000

PEAK_STREAM_FLAGS = PA_STREAM_DONT_MOVE | PA_STREAM_PEAK_DETECT | PA_STREAM_ADJUST_LATENCY

# Marker so we (and others) can recognise and hide our observer streams
STREAM_NAME_PREFIX = "Clarameter."
APP_NAME = "Clara Meters"

DEBUG_RAW_PEAKS = False


class _pa_sample_spec(ctypes.Structure):
    _fields_ = [
        ("format", ctypes.c_int),
        ("rate", ctypes.c_uint32),
        ("channels", ctypes.c_uint8),
    ]


class _pa_buffer_attr(ctypes.Structure):
    _fields_ = [
        ("maxlength", ctypes.c_uint32),
        ("tlength", ctypes.c_uint32),
        ("prebuf", ctypes.c_uint32),
        ("minreq", ctypes.c_uint32),
        ("fragsize", ctypes.c_uint32),
    ]


_pa_context_notify_cb_t = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)
_pa_source_info_cb_t = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p)
_pa_stream_request_cb_t = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p)


def _load_libpulse():
    path = ctypes.util.find_library("pulse")
    if not path:
        return None
    try:
        lib = ctypes.CDLL(path)
    except OSError:
        return None

    lib.pa_mainloop_new.restype = ctypes.c_void_p
    lib.pa_mainloop_get_api.restype = ctypes.c_void_p
    lib.pa_mainloop_get_api.argtypes = (ctypes.c_void_p,)
    lib.pa_mainloop_iterate.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p)
    lib.pa_mainloop_iterate.restype = ctypes.c_int
    lib.pa_mainloop_free.argtypes = (ctypes.c_void_p,)

    lib.pa_context_new.restype = ctypes.c_void_p
    lib.pa_context_new.argtypes = (ctypes.c_void_p, ctypes.c_char_p)
    lib.pa_context_set_state_callback.argtypes = (ctypes.c_void_p, _pa_context_notify_cb_t, ctypes.c_void_p)
    lib.pa_context_connect.restype = ctypes.c_int
    lib.pa_context_connect.argtypes = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
    lib.pa_context_get_state.restype = ctypes.c_int
    lib.pa_context_get_state.argtypes = (ctypes.c_void_p,)
    lib.pa_context_get_source_info_list.restype = ctypes.c_void_p
    lib.pa_context_get_source_info_list.argtypes = (ctypes.c_void_p, _pa_source_info_cb_t, ctypes.c_void_p)
    lib.pa_context_disconnect.argtypes = (ctypes.c_void_p,)
    lib.pa_context_unref.argtypes = (ctypes.c_void_p,)
    lib.pa_operation_unref.argtypes = (ctypes.c_void_p,)

    lib.pa_stream_new.restype = ctypes.c_void_p
    lib.pa_stream_new.argtypes = (ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(_pa_sample_spec), ctypes.c_void_p)
    lib.pa_stream_set_read_callback.argtypes = (ctypes.c_void_p, _pa_stream_request_cb_t, ctypes.c_void_p)
    lib.pa_stream_connect_record.restype = ctypes.c_int
    lib.pa_stream_connect_record.argtypes = (
        ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(_pa_buffer_attr), ctypes.c_int)
    lib.pa_stream_disconnect.argtypes = (ctypes.c_void_p,)
    lib.pa_stream_unref.argtypes = (ctypes.c_void_p,)
    lib.pa_stream_peek.restype = ctypes.c_int
    lib.pa_stream_peek.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_size_t))
    lib.pa_stream_drop.restype = ctypes.c_int
    lib.pa_stream_drop.argtypes = (ctypes.c_void_p,)

    return lib


class PulsePeakSampler(object):
    """Samples real per-node peaks from pipewire-pulse using PA_STREAM_PEAK_DETECT."""

    def __init__(self):
        self._lib = None
        self._ml = None
        self._ctx = None
        self._state = PA_CONTEXT_UNCONNECTED
        self._sources = set()       # valid pulse source (and monitor source) names
        self._sources_ready = False
        self._requested_sources = False
        self._desired = set()       # requested node names (from canvas groups)
        self._resolved = {}         # node name -> pulse target name
        self._streams = {}          # node name -> stream pointer
        self._levels = {}           # node name -> peak 0.0 - 1.0
        self._op = None
        self._unavailable = False
        # keep callback instances alive for the lifetime of the sampler
        self._state_cb = _pa_context_notify_cb_t(self._on_context_state)
        self._source_cb = _pa_source_info_cb_t(self._on_source_info)
        self._read_cb = _pa_stream_request_cb_t(self._on_stream_read)

    # -- lifecycle -------------------------------------------------------------------------------------------

    def is_available(self):
        return not self._unavailable

    def is_running(self):
        return self._ml is not None

    def start(self):
        if self._unavailable or self._ml is not None:
            return self.is_running()
        lib = _load_libpulse()
        if lib is None:
            self._unavailable = True
            return False
        self._lib = lib
        try:
            self._ml = lib.pa_mainloop_new()
            if not self._ml:
                raise RuntimeError("pa_mainloop_new failed")
            api = lib.pa_mainloop_get_api(self._ml)
            self._ctx = lib.pa_context_new(api, APP_NAME.encode("utf-8"))
            if not self._ctx:
                raise RuntimeError("pa_context_new failed")
            lib.pa_context_set_state_callback(self._ctx, self._state_cb, None)
            if lib.pa_context_connect(self._ctx, None, 0, None) < 0:
                raise RuntimeError("pa_context_connect failed")
        except Exception:
            self._teardown()
            self._unavailable = True
            return False
        return True

    def stop(self):
        self._teardown()

    def _teardown(self):
        lib = self._lib
        if lib is None:
            return
        for name in list(self._streams):
            self._remove_stream(name)
        if self._ctx:
            try:
                lib.pa_context_disconnect(self._ctx)
                lib.pa_context_unref(self._ctx)
            except Exception:
                pass
        if self._ml:
            try:
                lib.pa_mainloop_free(self._ml)
            except Exception:
                pass
        self._ctx = None
        self._ml = None
        self._state = PA_CONTEXT_UNCONNECTED
        self._sources = set()
        self._sources_ready = False
        self._requested_sources = False
        self._resolved = {}
        self._levels = {}

    # -- pumping ---------------------------------------------------------------------------------------------

    def process(self):
        """Pump the mainloop a few times (non-blocking). Call from the GUI thread."""
        if self._ml is None or self._lib is None:
            return
        for _ in range(6):
            self._lib.pa_mainloop_iterate(self._ml, 0, None)
        if self._state == PA_CONTEXT_READY and not self._requested_sources:
            self._requested_sources = True
            try:
                self._op = self._lib.pa_context_get_source_info_list(self._ctx, self._source_cb, None)
            except Exception:
                pass
        if self._sources_ready:
            self._reconcile()

    # -- target management -----------------------------------------------------------------------------------

    def set_nodes(self, names):
        new = {n for n in names if n}
        if new != self._desired:
            self._desired = new
            if self._sources_ready:
                self._reconcile()

    def has_target(self, name):
        """True when this node has a PulseAudio source/monitor we can sample."""
        if not name or not self._sources_ready:
            return False
        return self._resolve_target(name) is not None

    def level_for(self, name):
        if not name:
            return 0.0
        # Peak-hold envelope smoothing: decay levels over time so transient/quiet audio
        # doesn't immediately drop to zero and cause rapid cable pulse flicker.
        now = time.monotonic()
        if not hasattr(self, "_held_levels"):
            self._held_levels = {}
            self._held_times = {}

        raw = self._levels.get(name, 0.0)
        held = self._held_levels.get(name, 0.0)
        last_t = self._held_times.get(name, now)
        dt = max(0.0, now - last_t)

        if raw >= held:
            held = raw
            self._held_times[name] = now
        else:
            # Hold peak for 150ms, then decay smoothly (~70% per 100ms)
            if dt > 0.15:
                decay_rate = 0.85 ** ((dt - 0.15) / 0.04)
                held = max(raw, held * decay_rate)
                if held < 0.005:
                    held = 0.0

        self._held_levels[name] = held
        return held

    def levels(self):
        return dict(self._levels)

    def _resolve_target(self, name):
        if name in self._resolved:
            return self._resolved[name]
        target = None
        if name in self._sources:
            target = name
        elif (name + ".monitor") in self._sources:
            target = name + ".monitor"
        else:
            name_norm = name.lower().replace(" ", "_").replace("-", "_")
            for src in self._sources:
                src_norm = src.lower().replace("-", "_")
                if name_norm in src_norm or src_norm in name_norm:
                    target = src
                    break
        self._resolved[name] = target
        return target

    def _reconcile(self):
        for name in list(self._streams):
            if name not in self._desired:
                self._remove_stream(name)
        for name in self._desired:
            if name in self._streams:
                continue
            target = self._resolve_target(name)
            if target is not None:
                self._add_stream(name, target)
        for name in list(self._levels):
            if name not in self._streams:
                del self._levels[name]

    # -- streams ---------------------------------------------------------------------------------------------

    def _add_stream(self, name, target):
        lib = self._lib
        try:
            ss = _pa_sample_spec(PA_SAMPLE_FLOAT32LE, 25, 1)
            attr = _pa_buffer_attr(0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, ctypes.sizeof(ctypes.c_float))
            stream = lib.pa_stream_new(self._ctx, (STREAM_NAME_PREFIX + name).encode("utf-8"), ctypes.byref(ss), None)
            if not stream:
                return
            lib.pa_stream_set_read_callback(stream, self._read_cb, None)
            if lib.pa_stream_connect_record(stream, target.encode("utf-8"), ctypes.byref(attr), PEAK_STREAM_FLAGS) < 0:
                lib.pa_stream_unref(stream)
                return
            self._streams[name] = stream
        except Exception:
            pass

    def _remove_stream(self, name):
        stream = self._streams.pop(name, None)
        self._levels.pop(name, None)
        if stream and self._lib:
            try:
                self._lib.pa_stream_disconnect(stream)
                self._lib.pa_stream_unref(stream)
            except Exception:
                pass

    # -- callbacks -------------------------------------------------------------------------------------------

    def _on_context_state(self, context, userdata):
        try:
            self._state = self._lib.pa_context_get_state(context)
        except Exception:
            self._state = PA_CONTEXT_FAILED

    def _on_source_info(self, context, info, eol, userdata):
        try:
            if eol:
                self._sources_ready = True
                self._reconcile()
                return
            if not info:
                return
            # pa_source_info's first member is `const char *name`
            name = ctypes.cast(info, ctypes.POINTER(ctypes.c_char_p))[0]
            if name:
                self._sources.add(name.decode("utf-8", "replace"))
        except Exception:
            pass

    def _on_stream_read(self, stream, nbytes, userdata):
        lib = self._lib
        data = ctypes.c_void_p()
        length = ctypes.c_size_t()
        if lib.pa_stream_peek(stream, ctypes.byref(data), ctypes.byref(length)) < 0:
            return
        if DEBUG_RAW_PEAKS and data.value and length.value:
            raw = ctypes.string_at(data.value, min(length.value, 16))
            try:
                first = ctypes.cast(data.value, ctypes.POINTER(ctypes.c_float))[0]
            except Exception:
                first = -1.0
            print("[pwlevels] nbytes=%d raw=%s first=%r" % (length.value, raw.hex(), first))
        if data.value and length.value >= ctypes.sizeof(ctypes.c_float):
            try:
                count = length.value // ctypes.sizeof(ctypes.c_float)
                arr = ctypes.cast(data, ctypes.POINTER(ctypes.c_float))
                peak = float(arr[count - 1])
                if peak < 0.0:
                    peak = 0.0
                elif peak > 1.0:
                    peak = 1.0
                # find the name for this stream pointer
                key = getattr(stream, "value", stream)
                for name, ptr in self._streams.items():
                    ptr_val = getattr(ptr, "value", ptr)
                    if ptr_val == key:
                        self._levels[name] = peak
                        break
            except Exception:
                pass
        lib.pa_stream_drop(stream)


_sampler = None


def get_sampler():
    global _sampler
    if _sampler is None:
        _sampler = PulsePeakSampler()
    return _sampler
