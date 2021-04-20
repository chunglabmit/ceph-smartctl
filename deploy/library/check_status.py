#! /usr/bin/python
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import re

from ansible.module_utils.basic import AnsibleModule
import json

def main():
    module = AnsibleModule(argument_spec={})
    rc, stdout, stderr = module.run_command(
            ["ceph-volume", "lvm", "list", "--format", "json"])
    with open("/tmp/ceph-volume.log", "w") as fd:
        json.dump(dict(rc=rc, stdout=stdout, stderr=stderr), fd,
                  indent=2)

    if rc:
        module.fail_json(msg="ceph-volume failed to run: %s" % stderr)
        return
    d = json.loads(stdout)
    all_devices = {}
    for osd in d:
        devices = []
        for dd in d[osd]:
            devices += dd["devices"]
        all_devices[osd] = devices

    ansible_facts = {}
    failed = False
    for osd, devices in all_devices.items():
        ansible_facts[osd] = {}
        for device in devices:
            rc, stdout, stderr = module.run_command(
                ["smartctl", "-H", device]
            )
            with open("/tmp/smartctl_%s.log" % osd, "w") as fd:
                json.dump(dict(rc=rc, stdout=stdout, stderr=stderr, device=device), fd)
            lines = [_.strip() for _ in stdout.split("\n")]
            if rc == 0:
                rc, sg_reassign_stdout, stderr = module.run_command(
                    ["sg_reassign", "--grown", device]
                )
                if rc == 0:
                    match = re.search(
                        "Elements in grown defect list: (?P<defects>[0-9]+)",
                        sg_reassign_stdout)
                    ansible_facts[osd][device] = dict(
                        defects=int(match.groupdict()["defects"])
                    )
                rc, smartctl_stdout, stderr = module.run_command(
                    ["smartctl", "-a", device])
                match = re.search("^read:\\s*(?P<fast_ecc>\\d+)"
                   "\\s*(?P<delayed_ecc>\\d+)"
                   "\\s*(?P<rereads>\\d+)"
                   "\\s*(?P<total_ecc>\\d+)"
                   "\\s*(?P<correction_algorithm_invocations>\\d+)"
                   "\\s*(?P<gb_processed>\\d+\\.*\\d*)"
                   "\\s*(?P<uncorrected_errors>\\d+)"
                   , smartctl_stdout,flags=re.MULTILINE)
                if match:
                    d = match.groupdict()
                    for key in ("fast_ecc", "delayed_ecc",
                                "correction_algorithm_invocations",
                                "uncorrected_errors"):
                        ansible_facts[osd][device][key] = d[key]
                match = re.search("^Product:\\s*(?P<product>.*$)",
                                  smartctl_stdout, flags=re.MULTILINE)
                if match:
                    d = match.groupdict()
                    ansible_facts[osd][device]["product"] = d["product"]
                match = re.search("^Manufactured.*$", smartctl_stdout,
                                  flags=re.MULTILINE)
                if match:
                    ansible_facts[osd][device]["manufactured"] = match.group(0)
                #
                # Turn off LEDs
                #
                module.run_command([
                    "ledctl", "off=%s" % device])
                continue
            module.run_command([
                "ledctl", "locate=%s" % device])
            failed=True
            for i, line in enumerate(lines):
                if line.find(
                        "=== START OF READ SMART DATA SECTION ===") != -1:
                    status = lines[i+1]
                    module.fail_json(msg="OSD: %s, device: %s status: %s" %
                                (osd, device, status))
            module.fail_json(
                msg="OSD: %s, device: %s. Unknown failure, return code=%d" %
                    (osd, device, rc))
    if not failed:
        module.exit_json(failed=False, smartctl=ansible_facts)

if __name__ == "__main__":
    main()
