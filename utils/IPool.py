import IPy
import json
from utils.RedisCon import rdscon

def ip_pool(network):
    '''
    : 192.168.1.5-24
    :param network:
    :return:
    '''
    net = '.'.join(network.split('-')[0].split('.')[:3])
    src = network.split('-')[0].split('.')[-1]
    dest = network.split('-')[1]
    lst = ['.'.join([net, str(num)]) for num in range(int(src), int(dest)+1) if IPy.IP('.'.join([net, str(num)]))]
    try:
        err, rds = rdscon()
        assert err is None, "redis conn failed!"
        rds.set('ip::pool', json.dumps(lst))
        return None, {"error": 0, "message": "ip pool create ok!"}
    except Exception as e:
        return True, {"error": 1, "message": "{}".format(e)}
