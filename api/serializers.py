from rest_framework import serializers


class VMListSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=30)


class VMDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(max_length=30)
    uuid = serializers.CharField()
    cpu = serializers.IntegerField()
    memory = serializers.IntegerField()
    status = serializers.CharField(max_length=20)
    network = serializers.JSONField()




