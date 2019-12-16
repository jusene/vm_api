from utils.QemuCon import qemu_isalive



def destoryvm(conn, name):
    '''
    :shutdoen force
    :param name:
    :return:
    '''
    try:
        dom = conn.lookupByName(name)
        ret = dom.destroy()
        assert ret == 0, '{} shutdown force error!'.format(name)
        return None, {"error": 0, "message": "{} shutdown force!".format(name)}
    except Exception as e:
        return True, {"error": 1, 'message': "{}".format(e)}




def shutdownvm(conn, name):
    '''
    : shutdown
    :param name:
    :return:
    '''
    try:
        dom = conn.lookupByName(name)
        ret = dom.shutdown()
        assert ret == 0, '{} shutdown error!'.format((name))
        return None, {"error": 0, "message": "{} shutdown!".format(name)}
    except Exception as e:
        return True, {"error": 1, "message": "{}".format(e)}