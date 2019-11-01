from utils.QemuCon import qemu_isalive
from django.conf import settings
from utils.AnsibleUtil import message, ansiblerun


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
        if dom.name() != name:
            raise OSError('{} define error'.format(name))
        else:
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
        ansiblerun(host_list, task_list)
        news = message.get()
        if news['runner'] == "failed":
            raise OSError({"error": 1, "message": news.get(settings.VM_HOST)})
        elif news['runner'] == 'unreachable':
            raise OSError({"error": 1, "message": news.get(settings.VM_HOST)})
        elif news['runner'] == 'ok':
            ret_message.append({"error": 0, "message": news.get(settings.VM_HOST)})
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
        if ret != 0:
            raise OSError('{} start error!'.format((name)))
        else:
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
        if ret != 0:
            raise OSError('{} restart error!'.format((name)))
        else:
            return None, {"error": 0, "message": "{} restart!".format(name)}
    except Exception as e:
        return True, {"error": 1, "message": "{}".format(e)}