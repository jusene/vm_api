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
from utils.RedisCon import rdscon
from api.serializers import VMListSerializer, VMDetailSerializer


class AuthPermission(BasePermission):
    def has_permission(self, request, view):
        return True


# Create your views here.
class Root(APIView):
    permission_classes = [AuthPermission, ]

    def get(self, request, format=None):
        '''
        :param request:
        :param format:
        :return:
        '''
        host = request.headers.get('Host')
        err, vm_list = domlist()
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


class VMList(APIView):
    permission_classes = [AuthPermission, ]

    def get(self, request, format=None):
        '''
        :param request:
        :param format:
        :return:
        '''
        err, vm_list = domlist()
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
        except KeyError as e:
            return Response({'error': 1, "message": "{} param not found".format(e)},
                            status=status.HTTP_404_NOT_FOUND)
        try:
            with open('templates/VMXMLDesc.xml', 'r') as fp:
                vmdesc = fp.read()
        except Exception as e:
            raise TemplateDoesNotExist('VMXMLDesc.xml')

        try:
            with open('templates/ifcfg-eth0', 'r') as fp:
                ifdesc = fp.read()
        except Exception as e:
            raise TemplateDoesNotExist('ifcfg-eth0')
        host_list = '{},'.format(settings.VM_HOST)
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

            err, news = createvm(temp.render(temp_context), ifcfg.render(if_context), vm_name)
            if err:
                return Response(news, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            err, news = startvm(vm_name)
            if err:
                return Response(news, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"error": 0, 'message': "{} create!".format(vm_name)}, status=status.HTTP_201_CREATED)


class VMDetail(APIView):
    permission_classes = [AuthPermission, ]

    def get_object(self, pk):
        err, vm_list = domlist()
        if err:
            return Response(vm_list, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if list(filter(lambda x: pk in x.values(), vm_list)):
            err, vm_detail = domdetail(pk)
            if err:
                raise Http404
            return vm_detail
        else:
            raise Http404

    def get(self, request, pk, format=None):
        '''
        :list detail
        :param request:
        :param pk:
        :param format:
        :return:
        '''
        vm_detail = self.get_object(pk)
        serializer = VMDetailSerializer(data=vm_detail)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk, format=None):
        '''
        : shut off
        :param request:
        :param pk:
        :param force:
        :param format:
        :return:
        '''
        force = dict(request.headers).get('Force')
        vm_detail = self.get_object(pk)
        serializer = VMDetailSerializer(data=vm_detail)
        if serializer.is_valid():
            name = serializer.data.get('name')
            state = serializer.data.get('status')
            if state == "shutoff":
                return Response({"error": 1, 'message': "{} aleardy shutoff!".format(name)},
                                status=status.HTTP_403_FORBIDDEN)
            if force == "true":
                err, message = destoryvm(name)
                if err:
                    return Response(message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                return Response(message, status=status.HTTP_200_OK)
            elif force is None:
                err, message = shutdownvm(name)
                if err:
                    return Response(message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                return Response(message, status=status.HTTP_200_OK)
            else:
                return Response({'error': 1, "message": 'unknown operator'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk, format=None):
        '''
        : operator
        :param request:
        :param pk:
        :param format:
        :return:
        '''
        operator = request.data
        vm_detail = self.get_object(pk)
        serializer = VMDetailSerializer(data=vm_detail)
        if serializer.is_valid():
            name = serializer.data.get('name')
            state = serializer.data.get('status')
            if operator.get('operator') is None:
                if state == "running":
                    return Response({"error": 1, 'message': "{} aleardy running!".format(name)},
                                    status=status.HTTP_403_FORBIDDEN)
                err, message = startvm(name)

            elif operator.get('operator') == "reboot":
                if state == "shutoff":
                    return Response({"error": 1, 'message': "{} aleardy shutoff!".format(name)},
                                    status=status.HTTP_403_FORBIDDEN)
                err, message = restartvm(name)
            elif operator.get('operator') == "delete":
                if state == "running":
                    err, message = deletevm(name)
                elif state == "shutoff":
                    err, message = delete_no_destroyvm(name)

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
            return Response({"error": 1, "message": rds}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            pool = rds.get("ip::pool")
        except Exception as e:
            pool = []
        return Response(json.loads(pool), status=status.HTTP_200_OK)

    def post(self, request, format=None):
        netdata = request.data.get("network")
        err, message = ip_pool(netdata)
        if err:
            return Response({"error": 1, "message": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(message, status=status.HTTP_201_CREATED)


class IPDetail(APIView):
    permission_classes = [AuthPermission, ]

    def delete(self, request, pk, format=None):
        try:
            IPy.IP(pk)

            err, rds = rdscon()
            if err:
                return Response({"error": 1, "message": rds}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            pool = rds.get("ip::pool")
            p = json.loads(pool)
            try:
                p.remove(pk)
            except Exception as e:
                return Response({"error": 1, "message": "{} does not exists on pool!"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            rds.set("ip::pool", json.dumps(p))
            return Response({"error": 0, "message": "{} remove pool".format(pk)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": 1, "message": "{} is not a ip address".format(pk)})

    def put(self, request, pk, format=None):
        try:
            IPy.IP(pk)

            err, rds = rdscon()
            if err:
                return Response({"error": 1, "message": rds}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            pool = rds.get("ip::pool")
            p = json.loads(pool)
            p.append(pk)
            s = set(p)
            p = list(s)
            rds.set("ip::pool", json.dumps(p))
            return Response({"error": 0, "message": "{} append pool".format(pk)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": 1, "message": "{} is not a ip address".format(pk)})


class HostList(APIView):
    permission_classes = [AuthPermission, ]

    def get(self, request, format=None):
        '''
        : ansible facts
        :param request:
        :param format:
        :return:
        '''
        host_list = '{},'.format(settings.VM_HOST)
        task_list = [
            dict(action=dict(module='setup')),
        ]
        ans = AnsibleRun(host_list, task_list)
        ans.task_run()
        return Response(ans.get_result(), status=status.HTTP_200_OK)
