#! /usr/bin/python
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# not only visible to ansible-doc, it also 'declares' the options the plugin requires and how to configure them.
DOCUMENTATION = '''
  short_description: Checks smartctl status on all Ceph drives
  version_added: "1.0"
  description:
      - This action uses ceph-volume lvm list to get the Ceph OSDs and their
      - associated drives and then uses smartctl to check their status
'''

from ansible.module_utils.basic import AnsibleModule
import json

#from ansible.utils.display import Display
#
#display = Display()

def main():
    module = AnsibleModule(argument_spec={})
    rc, stdout, stderr = module.run_command(
            ["sudo", "ceph-volume", "lvm", "list", "--format", "json"])
    with open("/tmp/ceph-volume.log", "w") as fd:
        json.dump(dict(rc=rc, stdout=stdout, stderr=stderr), fd,
                  indent=2)

    if rc:
        #display.vvvv("ceph-volume stderr:")
        #display.vvvv(result["stderr"])
        module.fail_json(msg="ceph-volume failed to run: %s" % stderr)
        return
    d = json.loads(stdout)
    all_devices = {}
    for osd in d:
        devices = []
        for dd in d[osd]:
            devices += dd["devices"]
        #display.vvvv("OSD %d has devices %s" % (osd, ",".join(devices)))
        all_devices[osd] = devices

    for osd, devices in all_devices.items():
        for device in devices:
            rc, stdout, stderr = module.run_command(
                ["sudo", "smartctl", "-H", device]
            )
            with open("/tmp/smartctl_%s.log" % osd, "w") as fd:
                json.dump(dict(rc=rc, stdout=stdout, stderr=stderr, device=device), fd)
            lines = [_.strip() for _ in stdout.split("\n")]
            if rc == 0:
                continue
            for i, line in enumerate(lines):
                if line.find(
                        "=== START OF READ SMART DATA SECTION ===") != -1:
                    status = lines[i+1]
                    module.fail_json(msg="OSD: %s, device: %s status: %s" %
                                (osd, device, status))
                    return
    module.exit_json(failed=False)

if __name__ == "__main__":
    main()