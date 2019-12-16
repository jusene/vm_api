from utils.QemuCon import qemu_isalive
import libvirt


def domlist(conn):
    try:
        doms = map(lambda x: x.name(), conn.listAllDomains())
        doms_list = list(map(lambda x: {'name': x}, doms))
        return None, doms_list
    except Exception as e:
        return True, {'error': 1, 'message': "{}".format(e)}


def domdetail(conn, name):
    try:
        dom = conn.lookupByName(name)
        state = dom.info()[0]
        if state == libvirt.VIR_DOMAIN_NOSTATE:
            status = 'nostate'
        elif state == libvirt.VIR_DOMAIN_RUNNING:
            status = 'running'
        elif state == libvirt.VIR_DOMAIN_BLOCKED:
            status = 'blocked'
        elif state == libvirt.VIR_DOMAIN_PAUSED:
            status = 'paused'
        elif state == libvirt.VIR_DOMAIN_SHUTDOWN:
            status = 'shutdown'
        elif state == libvirt.VIR_DOMAIN_SHUTOFF:
            status = 'shutoff'
        elif state == libvirt.VIR_DOMAIN_CRASHED:
            status = 'crashed'
        elif state == libvirt.VIR_DOMAIN_PMSUSPENDED:
            status = 'pmsuspended'
        else:
            status = 'unknown'
        with open('templates/{}_ifcfg-eth0'.format(name), 'r') as fp:
            ifinfo = fp.readlines()
        ipaddr = [line.split('=')[1].strip() for line in ifinfo if 'IPADDR' in line]
        netmask = [line.split('=')[1].strip() for line in ifinfo if 'NETMASK' in line]
        gateway = [line.split('=')[1].strip() for line in ifinfo if 'GATEWAY' in line]
        dns = [line.split('=')[1].strip() for line in ifinfo if 'DNS' in line]
        network = {}
        network['ip'] = ipaddr[0]
        network['netmask'] = netmask[0]
        network['gateway'] = gateway[0]
        network['dns'] = dns
        memory = dom.info()[1]
        cpu = dom.info()[3]
        uuid = dom.UUIDString()
        id = dom.ID()
        return None, {'id': id, 'name': name, 'uuid': uuid,'cpu': cpu, 'memory': memory,'status': status,
                      'network': network}
    except Exception as e:
        return True, {'error': 1, 'message': "{}".format(e)}