# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: proto/core/node/common/action/beaver_action.proto
"""Generated protocol buffer code."""
# third party
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


# syft absolute
from syft.proto.core.common import (
    common_object_pb2 as proto_dot_core_dot_common_dot_common__object__pb2,
)
from syft.proto.core.io import address_pb2 as proto_dot_core_dot_io_dot_address__pb2
from syft.proto.core.tensor import (
    share_tensor_pb2 as proto_dot_core_dot_tensor_dot_share__tensor__pb2,
)

DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b"\n1proto/core/node/common/action/beaver_action.proto\x12\x1csyft.core.node.common.action\x1a$proto/core/tensor/share_tensor.proto\x1a%proto/core/common/common_object.proto\x1a\x1bproto/core/io/address.proto\"\xe0\x01\n\x0c\x42\x65\x61verAction\x12*\n\x03\x65ps\x18\x01 \x01(\x0b\x32\x1d.syft.core.tensor.ShareTensor\x12%\n\x06\x65ps_id\x18\x02 \x01(\x0b\x32\x15.syft.core.common.UID\x12,\n\x05\x64\x65lta\x18\x03 \x01(\x0b\x32\x1d.syft.core.tensor.ShareTensor\x12'\n\x08\x64\x65lta_id\x18\x04 \x01(\x0b\x32\x15.syft.core.common.UID\x12&\n\x07\x61\x64\x64ress\x18\x05 \x01(\x0b\x32\x15.syft.core.io.Addressb\x06proto3"
)


_BEAVERACTION = DESCRIPTOR.message_types_by_name["BeaverAction"]
BeaverAction = _reflection.GeneratedProtocolMessageType(
    "BeaverAction",
    (_message.Message,),
    {
        "DESCRIPTOR": _BEAVERACTION,
        "__module__": "proto.core.node.common.action.beaver_action_pb2"
        # @@protoc_insertion_point(class_scope:syft.core.node.common.action.BeaverAction)
    },
)
_sym_db.RegisterMessage(BeaverAction)

if _descriptor._USE_C_DESCRIPTORS == False:

    DESCRIPTOR._options = None
    _BEAVERACTION._serialized_start = 190
    _BEAVERACTION._serialized_end = 414
# @@protoc_insertion_point(module_scope)
