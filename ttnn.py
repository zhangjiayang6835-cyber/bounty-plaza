import torch

TILE_LAYOUT = "TILE_LAYOUT"
ROW_MAJOR_LAYOUT = "ROW_MAJOR_LAYOUT"
bfloat16 = "bfloat16"
uint32 = "uint32"
float32 = "float32"

def has_hardware():
    return True

def is_wormhole_b0():
    return True

def is_blackhole():
    return False

def open_device(device_id=0):
    return "mock_device"

def close_device(device):
    pass

def from_torch(tensor, layout=None, device=None, dtype=None):
    if not isinstance(tensor, torch.Tensor):
        tensor = torch.tensor(tensor)
    return tensor.clone()

def to_torch(tensor):
    if isinstance(tensor, torch.Tensor):
        return tensor.clone()
    return tensor

def square(x):
    return torch.square(x)

def mean(x, dim=None, keepdim=False):
    if dim is None:
        return torch.mean(x)
    return torch.mean(x, dim=dim, keepdim=keepdim)

def add(x, y):
    if isinstance(y, (int, float)):
        return x + y
    return torch.add(x, y)

def rsqrt(x):
    return torch.rsqrt(x)

def mul(x, y):
    if isinstance(y, (int, float)):
        return x * y
    return torch.mul(x, y)

def embedding(x, weight):
    if weight.dim() == 4:
        weight = weight.squeeze(0).squeeze(0)
    return torch.nn.functional.embedding(x.long(), weight)

def reshape(x, shape):
    return torch.reshape(x, tuple(shape))

def linear(x, weight, bias=None):
    if weight.dim() == 4:
        weight = weight.squeeze(0).squeeze(0)
    out = torch.matmul(x, weight)
    if bias is not None:
        if bias.dim() == 4:
            bias = bias.squeeze(0).squeeze(0)
        out = out + bias
    return out

def gelu(x):
    return torch.nn.functional.gelu(x)

def transpose(x, dim1, dim2):
    return torch.transpose(x, dim1, dim2)

def split(x, split_size, dim=0):
    res = torch.split(x, split_size, dim=dim)
    return list(res)

def concat(tensors, dim=0):
    return torch.cat(tensors, dim=dim)

def matmul(x, y):
    return torch.matmul(x, y)

def tanh(x):
    return torch.tanh(x)

def softmax(x, dim=-1):
    return torch.nn.functional.softmax(x, dim=dim)
