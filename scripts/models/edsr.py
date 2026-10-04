import torch
import torch.nn as nn
from typing import Dict, Any


class ResBlock(nn.Module):
    """Residual Block for EDSR without Batch Normalization."""
    def __init__(self, channels: int, res_scale: float = 1.0):
        super().__init__()
        self.res_scale = res_scale
        self.body = nn.Sequential(
            nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=True),
            nn.ReLU(inplace=True),
            nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=True)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.body(x) * self.res_scale
        return x + res


class EDSR(nn.Module):
    """Enhanced Deep Super-Resolution (EDSR) Network."""
    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        features: int = 64,
        num_blocks: int = 32,
        scale: int = 4,
        res_scale: float = 1.0
    ):
        super().__init__()
        self.scale = scale
        self.features = features
        self.num_blocks = num_blocks

        # Head conv
        self.head = nn.Conv2d(in_channels, features, kernel_size=3, padding=1, bias=True)

        # Body: sequence of ResBlocks
        body_blocks = [ResBlock(features, res_scale=res_scale) for _ in range(num_blocks)]
        self.body = nn.Sequential(*body_blocks)

        # Body tail conv
        self.body_tail = nn.Conv2d(features, features, kernel_size=3, padding=1, bias=True)

        # Upsampler (for scale=4: two 2x PixelShuffles)
        if scale == 4:
            self.upsampler = nn.Sequential(
                nn.Conv2d(features, features * 4, kernel_size=3, padding=1, bias=True),
                nn.PixelShuffle(2),
                nn.Conv2d(features, features * 4, kernel_size=3, padding=1, bias=True),
                nn.PixelShuffle(2)
            )
        elif scale in (2, 3):
            self.upsampler = nn.Sequential(
                nn.Conv2d(features, features * (scale ** 2), kernel_size=3, padding=1, bias=True),
                nn.PixelShuffle(scale)
            )
        else:
            raise ValueError(f"Unsupported upscaling factor: {scale}")

        # Reconstruction tail conv
        self.tail = nn.Conv2d(features, out_channels, kernel_size=3, padding=1, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.head(x)
        res = self.body_tail(self.body(h))
        res = res + h
        up = self.upsampler(res)
        out = self.tail(up)
        return out

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())


def build_edsr(cfg: Dict[str, Any]) -> EDSR:
    return EDSR(
        in_channels=cfg.get("in_channels", 3),
        out_channels=cfg.get("out_channels", 3),
        features=cfg.get("features", 64),
        num_blocks=cfg.get("num_blocks", 32),
        scale=cfg.get("scale", 4),
        res_scale=cfg.get("res_scale", 1.0)
    )
