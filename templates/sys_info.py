#!/usr/bin/env python

import psutil

sys_info = {
    "cpu": {
        "count": psutil.cpu_count(),
        'cpu_percent': psutil.cpu_percent(interval=0.5)
    },
    "mem": dict(zip(["total", "available", "percent", "used", "free", "active", "inactive", "buffers", "cached", "shared", "slab"],
              list(psutil.virtual_memory()))),
    "disk": [{disk.mountpoint: dict(zip(["total", "used", "free", "percent", 'mountpoint'],
                                   list(psutil.disk_usage(disk.mountpoint))))}
             for disk in psutil.disk_partitions()]

}

print(sys_info)