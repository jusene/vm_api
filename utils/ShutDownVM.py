from utils.QemuCon import qemu_isalive


@qemu_isalive
def destoryvm(conn, name):
    '''
    :shutdoen force
    :param name:
    :return:
    '''
    try:
        dom = conn.lookupByName(name)
        ret = dom.destroy()
        if ret != 0:
            raise OSError('{} shutdown force error!'.format(name))
        else:
            return None, {"error": 0, "message": "{} shutdown force!".format(name)}
    except Exception as e:
        return True, {"error": 1, 'message': "{}".format(e)}



@qemu_isalive
def shutdownvm(conn, name):
    '''
    : shutdown
    :param name:
    :return:
    '''
    try:
        dom = conn.lookupByName(name)
        ret = dom.shutdown()
        if ret != 0:
            raise OSError('{} shutdown error!'.format((name)))
        else:
            return None, {"error": 0, "message": "{} shutdown!".format(name)}
    except Exception as e:
        return True, {"error": 1, "message": "{}".format(e)}