"""Expose the same Linux anonymous memfd API when CPython did not build its binding.

No temporary file, /dev/shm pathname, or disk-array fallback is permitted.
Linux x86-64 syscall 319 is defined by arch/x86/entry/syscalls/syscall_64.tbl.
"""
import ctypes
import mmap
import os
import platform
import sys

MFD_CLOEXEC = 1


def install(os_module=None, libc=None, machine=None, platform_name=None):
    module = os if os_module is None else os_module
    if (sys.platform if platform_name is None else platform_name) != "linux":
        raise RuntimeError("Linux anonymous memfd transport required")
    if callable(getattr(module, "memfd_create", None)):
        return getattr(module.memfd_create, "_phase3_backend", "os.memfd_create")
    library = ctypes.CDLL(None, use_errno=True) if libc is None else libc
    native = getattr(library, "memfd_create", None)
    if native is not None:
        native.argtypes = [ctypes.c_char_p, ctypes.c_uint]
        native.restype = ctypes.c_int
        backend = "libc.memfd_create"
    else:
        architecture = platform.machine() if machine is None else machine
        if architecture != "x86_64":
            raise RuntimeError("libc memfd unavailable; no verified syscall binding for " + architecture)
        syscall = library.syscall
        syscall.restype = ctypes.c_long
        backend = "linux-x86_64-syscall-319"

    def memfd_create(name, flags=MFD_CLOEXEC):
        encoded = os.fsencode(name)
        if b"\x00" in encoded:
            raise ValueError("embedded null byte")
        if not isinstance(flags, int) or not 0 <= flags <= 0xffffffff:
            raise OverflowError("memfd flags must fit unsigned int")
        ctypes.set_errno(0)
        if native is not None:
            descriptor = native(encoded, flags)
        else:
            descriptor = syscall(ctypes.c_long(319), ctypes.c_char_p(encoded), ctypes.c_uint(flags))
        if descriptor < 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), name)
        return int(descriptor)

    memfd_create._phase3_backend = backend
    module.memfd_create = memfd_create
    if not hasattr(module, "MFD_CLOEXEC"):
        module.MFD_CLOEXEC = MFD_CLOEXEC
    return backend


def probe():
    """Exercise the actual kernel API and anonymous mapping; fail closed on ENOSYS/EPERM."""
    import fcntl
    backend = install()
    descriptor = os.memfd_create("phase3_memfd_probe", flags=MFD_CLOEXEC)
    try:
        if not fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC:
            raise RuntimeError("memfd descriptor is missing CLOEXEC")
        target = os.readlink("/proc/self/fd/" + str(descriptor))
        if not target.lstrip("/").startswith("memfd:"):
            raise RuntimeError("descriptor is not an anonymous memfd")
        os.ftruncate(descriptor, 4096)
        with mmap.mmap(descriptor, 4096, access=mmap.ACCESS_WRITE) as mapping:
            mapping[:8] = b"phase3fd"
            if mapping[:8] != b"phase3fd":
                raise RuntimeError("anonymous memfd mapping roundtrip failed")
        return {"backend": backend, "anonymous": True, "cloexec": True,
                "mapping_roundtrip": True, "disk_fallback": False}
    finally:
        os.close(descriptor)
