import os
from utils.QemuCon import qemu_isalive
from utils.ShutDownVM import destoryvm
from django.conf import settings
from utils.AnsibleUtil import ansiblerun
from utils.AnsibleUtil import message as msg

@qemu_isalive
def deletevm(conn, name):
    '''
    : 1. destory vm
    : 2. undefine vm
    : 3. delete img
    :param name:
    :return:
    '''
    try:
        ret_message = []
        # destory
        err, message = destoryvm(name)
        if err:
            raise OSError('{} shutdown force error!'.format(name))
        ret_message.append(message)
        # undefine
        dom = conn.lookupByName(name)
        ret = dom.undefine()
        if ret != 0:
            raise OSError('{} undefine error!'.format(name))
        ret_message.append({"error": 0, "message": "{} undefine!".format(name)})
        # delete
        img_path = os.path.join(settings.IMG_PATH, name+'.qcow2')
        host_list = '{},'.format(settings.VM_HOST)
        task_list = [
            dict(action=dict(module='file', args="name={} state=absent".format(img_path))),
            dict(action=dict(module='file', args="path=/ddhome/kvm/config/{} state=absent".format(name)))
        ]
        ansiblerun(host_list, task_list)
        news = msg.get()
        if news['runner'] == "failed":
            raise OSError({"error": 1, "message": news.get(settings.VM_HOST)})
        elif news['runner'] == 'unreachable':
            raise OSError({"error": 1, "message": news.get(settings.VM_HOST)})
        elif news['runner'] == 'ok':
            ret_message.append({"error": 0, "message": news.get(settings.VM_HOST)})
            return None, ret_message
    except Exception as e:
        print(e)
        return True, {"error": 1, 'message': "{}".format(e)}


@qemu_isalive
def delete_no_destroyvm(conn, name):
    '''
    :
    :param conn:
    :param name:
    :return:
    '''
    try:
        ret_message = []
        # undefine
        dom = conn.lookupByName(name)
        ret = dom.undefine()
        if ret != 0:
            raise OSError('{} undefine error!'.format(name))
        ret_message.append({"error": 0, "message": "{} undefine!".format(name)})
        # delete
        img_path = os.path.join(settings.IMG_PATH, name + '.qcow2')
        host_list = '{},'.format(settings.VM_HOST)
        task_list = [
            dict(action=dict(module='file', args="name={} state=absent".format(img_path))),
        ]
        ansiblerun(host_list, task_list)
        news = msg.get()
        if news['runner'] == "failed":
            raise OSError({"error": 1, "message": news.get(settings.VM_HOST)})
        elif news['runner'] == 'unreachable':
            raise OSError({"error": 1, "message": news.get(settings.VM_HOST)})
        elif news['runner'] == 'ok':
            ret_message.append({"error": 0, "message": news.get(settings.VM_HOST)})
            return None, ret_message
    except Exception as e:
        print(e)
        return True, {"error": 1, 'message': "{}".format(e)}