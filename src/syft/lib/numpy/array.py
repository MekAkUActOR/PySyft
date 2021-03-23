# third party
import numpy as np
import torch

# syft relative
from ...generate_wrapper import GenerateWrapper
from ...lib.torch.tensor_util import protobuf_tensor_deserializer
from ...lib.torch.tensor_util import protobuf_tensor_serializer
from ...proto.lib.torch.tensor_pb2 import TensorData


def object2proto(obj: np.ndarray) -> TensorData:
    tensor = torch.from_numpy(obj).clone()
    tensor_proto = protobuf_tensor_serializer(tensor)
    # TODO:
    # support numpy.object_, numpy.str_, numpy.unicode_,
    #         numpy.uint16, numpy.uint32, numpy.uint64,
    #         numpy.complex64, numpy.complex128
    return tensor_proto


def proto2object(proto: TensorData) -> np.ndarray:
    tensor = protobuf_tensor_deserializer(proto)
    obj = tensor.to('cpu').detach().numpy().copy()
    # TODO:
    # support numpy.object_, numpy.str_, numpy.unicode_,
    #         numpy.uint16, numpy.uint32, numpy.uint64,
    #         numpy.complex64, numpy.complex128

    return obj


GenerateWrapper(
    wrapped_type=np.ndarray,
    import_path="numpy.ndarray",
    protobuf_scheme=TensorData,
    type_object2proto=object2proto,
    type_proto2object=proto2object,
)
