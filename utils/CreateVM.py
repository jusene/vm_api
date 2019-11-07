from utils.QemuCon import qemu_isalive
from django.conf import settings
from utils.AnsibleUtil import AnsibleRun


@qemu_isalive
def createvm(conn, xmldesc, ifdesc, name):
    '''
    : 1. define
    : 2. copy ifcfg-eth0
    : 3. virt-copy-in
    :param conn:
    :param xmldesc:
    :param rcdesc:
    :param name:
    :return:
    '''
    try:
        ret_message = []
        # define
        dom = conn.defineXML(xmldesc)
        assert dom.name() == name, '{} define error'.format(name)
        ret_message.append({"error": 0, "message": "{} define!".format(name)})
        # copy ifcfg-eth0 and virt-copy-in
        with open('templates/{}_ifcfg-eth0'.format(name), 'w') as fp:
            fp.write(ifdesc)
        host_list = '{},'.format(settings.VM_HOST)
        task_list = [
            dict(action=dict(module="file", args="path=/ddhome/kvm/config/{} state=directory".format(name))),
            dict(action=dict(module='copy', args='src=templates/{name}_ifcfg-eth0 '
                                                 'dest=/ddhome/kvm/config/{name}/ifcfg-eth0'.format(name=name))),
            dict(action=dict(module='shell', args='/usr/bin/virt-copy-in -d {name} /ddhome/kvm/config/{name}/ifcfg-eth0 '
                                                  '/etc/sysconfig/network-scripts/'.format(name=name)))
        ]
        ans = AnsibleRun(host_list, task_list)
        ans.task_run()
        msg = ans.get_result()
        if msg["failed"]:
            raise OSError({"error": 1, "message": msg.get('failed')})
        elif msg['unreachable']:
            raise OSError({"error": 1, "message": msg.get('unreachable')})
        elif msg['ok']:
            ret_message.append({"error": 0, "message": msg.get('ok')})
            return None, ret_message
    except Exception as e:
        return True, {"error": 1, "message": "{}".format(e)}


@qemu_isalive
def startvm(conn, name):
    '''
    : start
    :param name:
    :return:
    '''
    try:
        dom = conn.lookupByName(name)
        ret = dom.create()
        assert ret == 0, "{} start error!".format(name)
        return None, {"error": 0, "message": "{} start!".format(name)}
    except Exception as e:
        return True, {"error": 1, "message": "{}".format(e)}


@qemu_isalive
def restartvm(conn, name):
    '''
    : restart
    :param name:
    :return:
    '''
    try:
        dom = conn.lookupByName(name)
        ret = dom.reboot()
        assert ret == 0, '{} restart error!'.format(name)
        return None, {"error": 0, "message": "{} restart!".format(name)}
    except Exception as e:
        return True, {"error": 1, "message": "{}".format(e)}