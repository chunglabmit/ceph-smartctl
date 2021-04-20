#! /usr/bin/python
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import re

from ansible.module_utils.basic import AnsibleModule
import json

def main():
    module = AnsibleModule(argument_spec={})
    rc, stdout, stderr = module.run_command(
        ["smartctl", "--scan"])
    lines = stdout.split("\n")
    ansible_facts = {}
    for line in lines:
        if not line.startswith("/dev/bus/0"):
            continue
        device = line.split(" ")[2]
        ansible_facts[device] = {}
        rc, stdout, stderr = module.run_command(
            ["smartctl", "-H", "-d", device, "/dev/bus/0"])
        for smartline in stdout.split("\n"):
            if smartline.endswith(": PASSED"):
                ansible_facts[device]["PASSED"] = True
                break
        else:
            module.fail_json(msg="Device %s did not pass" % device)
            return
    module.exit_json(failed=False, smartctl=ansible_facts)


if __name__ == "__main__":
    main()
