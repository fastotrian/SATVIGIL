import math
import torch
import torch.nn as nn

def default_conv(in_channels, out_channels, kernel_size, bias=True):
    return nn.Conv2d(
        in_channels, out_channels, kernel_size,
        padding=(kernel_size//2), bias=bias)

class ResBlock(nn.Module):
    def __init__(
        self, conv, n_feats, kernel_size,
        bias=True, bn=False, act=nn.ReLU(True), res_scale=1):

        super(ResBlock, self).__init__()
        m = []
        for i in range(2):
            m.append(conv(n_feats, n_feats, kernel_size, bias=bias))
            if bn:
                m.append(nn.BatchNorm2d(n_feats))
            if i == 0:
                m.append(act)

        self.body = nn.Sequential(*m)
        self.res_scale = res_scale

    def forward(self, x):
        res = self.body(x).mul(self.res_scale)
        res += x
        return res

class Upsampler(nn.Sequential):
    def __init__(self, conv, scale, n_feats, bn=False, act=False, bias=True):
        m = []
        if (scale & (scale - 1)) == 0:    # Is scale = 2^n?
            for _ in range(int(math.log(scale, 2))):
                m.append(conv(n_feats, 4 * n_feats, 3, bias))
                m.append(nn.PixelShuffle(2))
                if bn:
                    m.append(nn.BatchNorm2d(n_feats))
                if act == 'relu':
                    m.append(nn.ReLU(True))
                elif act == 'prelu':
                    m.append(nn.PReLU(n_feats))

        elif scale == 3:
            m.append(conv(n_feats, 9 * n_feats, 3, bias))
            m.append(nn.PixelShuffle(3))
            if bn:
                m.append(nn.BatchNorm2d(n_feats))
            if act == 'relu':
                m.append(nn.ReLU(True))
            elif act == 'prelu':
                m.append(nn.PReLU(n_feats))
        else:
            raise NotImplementedError

        super(Upsampler, self).__init__(*m)

class EDSR(nn.Module):
    def __init__(self, n_resblocks=16, n_feats=64, scale=2, res_scale=1.0, n_colors=3, conv=default_conv):
        super(EDSR, self).__init__()
        
        kernel_size = 3
        act = nn.ReLU(True)
        
        self.head = conv(n_colors, n_feats, kernel_size)
        
        m_body = [
            ResBlock(
                conv, n_feats, kernel_size, act=act, res_scale=res_scale
            ) for _ in range(n_resblocks)
        ]
        self.body = nn.Sequential(*m_body)
        
        self.body_tail = conv(n_feats, n_feats, kernel_size)
        
        self.upsampler = Upsampler(conv, scale, n_feats, act=False)
        
        self.tail = conv(n_feats, n_colors, kernel_size)

    def forward(self, x):
        x = self.head(x)
        res = self.body(x)
        res = self.body_tail(res)
        res += x
        x = self.upsampler(res)
        x = self.tail(x)
        return x

def build_edsr(model_cfg=None):
    if model_cfg is None:
        model_cfg = {}
    return EDSR(
        n_resblocks=model_cfg.get("num_blocks", 16),
        n_feats=model_cfg.get("features", 64),
        scale=model_cfg.get("scale", 2),
        res_scale=model_cfg.get("res_scale", 1.0),
        n_colors=model_cfg.get("in_channels", 3)
    )
