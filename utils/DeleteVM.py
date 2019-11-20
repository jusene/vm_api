import os
from utils.QemuCon import qemu_isalive
from django.conf import settings
from utils.ShutDownVM import destoryvm
from utils.AnsibleUtil import AnsibleRun
from utils.RedisCon import get_host


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
        print(err)
        assert err is None, '{} shutdown force error!'.format(name)
        ret_message.append(message)
        # undefine
        dom = conn.lookupByName(name)
        ret = dom.undefine()
        assert ret == 0, '{} undefine error!'.format(name)
        ret_message.append({"error": 0, "message": "{} undefine!".format(name)})
        # delete
        img_path = os.path.join(settings.IMG_PATH, name+'.qcow2')
        err, host = get_host()
        assert err is None, "GET HOST ERROR"
        host_list = '{},'.format(host)
        task_list = [
            dict(action=dict(module='file', args="name={} state=absent".format(img_path))),
            dict(action=dict(module='file', args="path=/ddhome/kvm/config/{} state=absent".format(name)))
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
        assert ret == 0, '{} undefine error!'.format(name)
        ret_message.append({"error": 0, "message": "{} undefine!".format(name)})
        # delete
        img_path = os.path.join(settings.IMG_PATH, name + '.qcow2')
        err, host = get_host()
        assert err is None, "GET HOST ERROR"
        host_list = '{},'.format(host)
        task_list = [
            dict(action=dict(module='file', args="name={} state=absent".format(img_path))),
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
        print(e)
        return True, {"error": 1, 'message': "{}".format(e)}