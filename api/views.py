import os
import json
import IPy
from django.http import Http404
from django.conf import settings
from django.template import Context, Template, TemplateDoesNotExist
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from utils.ListVM import domlist, domdetail
from utils.ShutDownVM import destoryvm, shutdownvm
from utils.CreateVM import startvm, restartvm, createvm
from utils.DeleteVM import deletevm, delete_no_destroyvm
from utils.AnsibleUtil import AnsibleRun
from utils.IPool import ip_pool
from utils.RedisCon import rdscon, get_host
from utils.QemuCon import qemu_connect, qemu_isalive
from api.serializers import VMListSerializer, VMDetailSerializer


class AuthPermission(BasePermission):
    def has_permission(self, request, view):
        return True


# Create your views here.
'''
class Root(APIView):
    permission_classes = [AuthPermission, ]

    def get(self, request, format=None):
        host = request.headers.get('Host')

        # 获取默认的物理机器
        err, h = get_host()
        assert err is None, 'GET HOST ERROR'

        @qemu_isalive(host=h)
        def lst(conn):
            return domlist(conn)

        err, vm_list = lst()
        if err:
            return Response(vm_list, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        serializer = VMListSerializer(data=vm_list, many=True)
        if serializer.is_valid():
            vm_detail_list = {}
            for v in serializer.validated_data:
                vm_detail_list[v.get('name')] = 'http://{host}/api/v1/vms/{vm_name}/'.format(host=host,
                                                                                             vm_name=v.get('name'))
        route = {
            "vms": "http://{host}/api/v1/vms/".format(host=host),
            "hosts": "http://{host}/api/v1/hosts/".format(host=host),
            'ips': "http://{host}/api/v1/ips".format(host=host)
        }
        route.update(vm_detail_list)
        return Response(route, status=status.HTTP_200_OK)
'''

class VMList(APIView):
    permission_classes = [AuthPermission, ]

    def get(self, request, format=None):
        '''
        :param request:
        :param format:
        :return:
        '''

        # 获取默认的宿主机
        err, host = get_host()
        assert err is None, 'GET HOST ERROR'

        @qemu_isalive(host=host)
        def lst(conn):
            return domlist(conn)
        err, vm_list = lst()
        if err:
            return Response(vm_list, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        serializer = VMListSerializer(data=vm_list, many=True)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None):
        '''
        : create vm
        :param request:
        :param format:
        :return:
        '''
        vm_info = request.data
        try:
            vm_name = vm_info['name']
            vm_cpu = vm_info['cpu']
            vm_mem = vm_info['mem']
            vm_ip = vm_info['ip']
            vm_mask = vm_info['mask']
            vm_gateway = vm_info['gateway']
            vm_phyip = vm_info['pyhIp']
        except KeyError as e:
            return Response({'error': 1, "message": "{} param not found".format(e)},
                            status=status.HTTP_404_NOT_FOUND)
        # kvm配置文件
        try:
            with open('templates/VMXMLDesc.xml', 'r') as fp:
                vmdesc = fp.read()
        except Exception as e:
            raise TemplateDoesNotExist('VMXMLDesc.xml')
        # 网络配置文件
        try:
            with open('templates/ifcfg-eth0', 'r') as fp:
                ifdesc = fp.read()
        except Exception as e:
            raise TemplateDoesNotExist('ifcfg-eth0')
        # 以模板镜像创建镜像
        host_list = '{},'.format(vm_phyip)
        task_list = [
            dict(action=dict(module='shell',
                             args="/usr/bin/qemu-img create -f qcow2 -b {image_path}/model.qcow2 "
                                  "{image_path}/{name}.qcow2".format(image_path=settings.IMG_PATH, name=vm_name))),
        ]
        result = AnsibleRun(host_list, task_list)
        result.task_run()
        msg = result.get_result()
        if msg['failed']:
            return Response({"error": 1, "message": msg.get('failed')},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif msg['unreachable']:
            return Response({"error": 1, "message": msg.get('unreachable')},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif msg['ok']:
            temp = Template(vmdesc)
            temp_context = Context({"NAME": vm_name, "CPU": vm_cpu, "MEMORY": vm_mem,
                            "IMAGE": os.path.join(settings.IMG_PATH, '{}.qcow2'.format(vm_name))})
            ifcfg = Template(ifdesc)
            if_context = Context({"NAME": vm_name, "IPADDR": vm_ip, "NETMASK": vm_mask, "GATEWAY": vm_gateway})

            # 创建虚拟机
            @qemu_isalive(host=vm_phyip)
            def create(conn, xmldesc, ifdesc, name):
                return createvm(conn, xmldesc, ifdesc, name)
            err, news = create(temp.render(temp_context), ifcfg.render(if_context), vm_name)
            if err:
                return Response(news, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 启动虚拟机
            @qemu_isalive(host=vm_phyip)
            def start(conn, name):
                return startvm(conn, name)

            err, news = start(vm_name)
            if err:
                return Response(news, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"error": 0, 'message': "{} create!".format(vm_name)}, status=status.HTTP_201_CREATED)


class VMDetail(APIView):
    permission_classes = [AuthPermission, ]

    def get_object(self, phy, pk):
        @qemu_isalive(host=phy)
        def lst(conn):
            return domlist(conn)
        err, vm_list = lst()
        if err:
            return Response(vm_list, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if list(filter(lambda x: pk in x.values(), vm_list)):
            @qemu_isalive(host=phy)
            def lstdetail(conn, name):
                return domdetail(conn, name)

            err, vm_detail = lstdetail(pk)
            if err:
                raise Http404
            return vm_detail
        else:
            raise Http404

    def get(self, request, phy, pk=None, format=None):
        '''
        :list detail
        :param request:
        :param pk:
        :param format:
        :return:
        '''
        if pk:
            vm_detail = self.get_object(phy, pk)
            serializer = VMDetailSerializer(data=vm_detail)
            if serializer.is_valid():
                return Response(serializer.validated_data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            @qemu_isalive(host=phy)
            def lst(conn):
                return domlist(conn)

            err, vm_list = lst()
            if err:
                return Response(vm_list, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            serializer = VMListSerializer(data=vm_list, many=True)
            if serializer.is_valid():
                return Response(serializer.validated_data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, phy, pk, format=None):
        '''
        : shut off
        :param request:
        :param pk:
        :param force:
        :param format:
        :return:
        '''
        force = dict(request.headers).get('Force')
        vm_detail = self.get_object(phy, pk)
        serializer = VMDetailSerializer(data=vm_detail)
        if serializer.is_valid():
            name = serializer.data.get('name')
            state = serializer.data.get('status')
            if state == "shutoff":
                return Response({"error": 1, 'message': "{} aleardy shutoff!".format(name)},
                                status=status.HTTP_403_FORBIDDEN)
            if force == "true":
                @qemu_isalive(host=phy)
                def destory(conn, name):
                    return destoryvm(conn, name)
                err, message = destory(name)
                if err:
                    return Response(message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                return Response(message, status=status.HTTP_200_OK)
            elif force is None:
                @qemu_isalive(host=phy)
                def shutdown(conn, name):
                    return shutdownvm(conn, name)
                err, message = shutdown(name)
                if err:
                    return Response(message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                return Response(message, status=status.HTTP_200_OK)
            else:
                return Response({'error': 1, "message": 'unknown operator'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, phy, pk, format=None):
        '''
        : operator
        :param request:
        :param pk:
        :param format:
        :return:
        '''
        operator = request.data
        vm_detail = self.get_object(phy, pk)
        serializer = VMDetailSerializer(data=vm_detail)
        if serializer.is_valid():
            name = serializer.data.get('name')
            state = serializer.data.get('status')
            if operator.get('operator') is None:
                if state == "running":
                    return Response({"error": 1, 'message': "{} aleardy running!".format(name)},
                                    status=status.HTTP_403_FORBIDDEN)
                @qemu_isalive(host=phy)
                def start(conn, name):
                    return startvm(conn, name)
                err, message = start(name)

            elif operator.get('operator') == "reboot":
                if state == "shutoff":
                    return Response({"error": 1, 'message': "{} aleardy shutoff!".format(name)},
                                    status=status.HTTP_403_FORBIDDEN)
                @qemu_isalive(host=phy)
                def restart(conn, name):
                    return restartvm(conn, name)
                err, message = restart(name)

            elif operator.get('operator') == "delete":
                if state == "running":
                    @qemu_isalive(host=phy)
                    def delete(conn, phy, name):
                        return deletevm(conn, phy, name)
                    err, message = delete(phy, name)

                elif state == "shutoff":
                    @qemu_isalive(host=phy)
                    def delete_no_destroy(conn, name):
                        return delete_no_destroyvm(conn, name)
                    err, message = delete_no_destroy(name)
            if err:
                return Response(message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(message, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IPList(APIView):
    permission_classes = [AuthPermission, ]

    def get(self, request, format=None):
        '''
        :param request:
        :param pk:
        :param format:
        :return:
        '''
        err, rds = rdscon()
        if err:
            return Response({"error": 1, "message": rds},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            pool = rds.get("ip::pool")
        except Exception as e:
            pool = []
        return Response(json.loads(pool), status=status.HTTP_200_OK)

    def post(self, request, format=None):
        netdata = request.data.get("network")
        err, message = ip_pool(netdata)
        if err:
            return Response({"error": 1, "message": message},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(message, status=status.HTTP_201_CREATED)


class IPDetail(APIView):
    permission_classes = [AuthPermission, ]

    def delete(self, request, pk, format=None):
        try:
            IPy.IP(pk)

            err, rds = rdscon()
            if err:
                return Response({"error": 1, "message": '{}'.format(rds)},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            pool = rds.get("ip::pool")
            p = json.loads(pool)
            try:
                p.remove(pk)
            except Exception as e:
                return Response({"error": 1, "message": "{} does not exists on pool!".format(pk)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            rds.set("ip::pool", json.dumps(p))
            return Response({"error": 0, "message": "{} remove pool".format(pk)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": 1, "message": "{} is not a ip address".format(pk)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk, format=None):
        try:
            IPy.IP(pk)

            err, rds = rdscon()
            if err:
                return Response({"error": 1, "message": '{}'.format(rds)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            pool = rds.get("ip::pool")
            p = json.loads(pool)
            p.append(pk)
            s = set(p)
            p = list(s)
            rds.set("ip::pool", json.dumps(p))
            return Response({"error": 0, "message": "{} append pool".format(pk)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": 1, "message": "{} is not a ip address".format(pk)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HostList(APIView):
    permission_classes = [AuthPermission, ]

    def get(self, request, phy=None, format=None):
        '''
        : ansible facts
        :param request:
        :param format:
        :return:
        '''
        err, host = get_host()
        assert err is None, 'GET HOST ERROR'
        host_list = '{},'.format(phy or host)
        task_list = [
            dict(action=dict(module='script',
                             args='templates/sys_info.py')),
        ]
        ans = AnsibleRun(host_list, task_list)
        ans.task_run()
        return Response(ans.get_result(), status=status.HTTP_200_OK)

    def post(self, request, phy=None, format=None):
        '''
        : change  host
        :param request:
        :param format:
        :return:
        '''
        data = request.data
        vm_host = data.get('host')
        err, rds = rdscon()
        try:
            assert err is None, 'REDIS CONNECT ERROR'
            rds.set("host::ip", vm_host)
            return Response({"error": 0, "message": "host change ok"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": 1, "message": "{}".format(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HostDetail(APIView):
    permission_classes = [AuthPermission, ]

    def get(self, request, pk, format=None):
        '''
        :param request:
        :param pk:
        :param format:
        :return:
        '''
        try:
            err, conn = qemu_connect(pk)
            assert err is None, 'QEMU CONN ERROR'
            doms = list(map(lambda x: x.name(), conn.listAllDomains()))
            ips = []
            for d in doms:
                with open('templates/{}_ifcfg-eth0'.format(d)) as fp:
                    data = fp.readlines()
                    ipaddr = [line.split('=')[1].strip() for line in data if 'IPADDR' in line]
                    ips.append(ipaddr[0])
            doms_list = list(map(lambda x, y: {'name': x, 'ip': y}, doms, ips))
            return Response(doms_list, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": 1, "message": "{}".format(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

