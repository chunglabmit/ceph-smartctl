# CEPH-SMARTCTL

This ansible playbook checks all drives associated with an OSD for
failures using the `smartctl` utility. It does a `ceph-volume lvm list`
to find drives and OSDs and then issues a `smartctl -H` against each
drive found.

To run:

* Create a hosts file with header `[osds]`, e.g.

```
[osds]
osd1 ansible_host=192.168.1.1
osd2 ansible_host=192.168.1.2
...
```

* CD into this directory.

```bash
ansible-playbook -i hosts deploy/smartctl.yaml
```

## Limitations

Currently only works for Centos.