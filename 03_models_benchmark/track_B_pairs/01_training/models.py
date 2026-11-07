"""Learned methods 4-7 of the Track B ladder (Project_Description Sec. 6.3, plan 2026-11-06_1223).

All take two (B, 256, 160) images and return 4 logits (lensed, repeat, unrelated, impostor).
Time resolution stays at 2 samples up to the fusion; members can differ by up to 20 samples in time.
"""
import torch
from torch import nn
import torch.nn.functional as F

MAXLAG = 12  # in encoder steps of 2 samples: +-24 samples


def conv(i, o, stride):
    return nn.Sequential(nn.Conv2d(i, o, (5, 3), stride, (2, 1)), nn.GroupNorm(8, o), nn.ReLU())


class Encoder(nn.Module):
    """(B, in, 256, 160) -> (B, 4c, 16, 80)."""

    def __init__(self, cin=1, c=16):
        super().__init__()
        self.net = nn.Sequential(conv(cin, c, (2, 1)), conv(c, 2 * c, (2, 1)), conv(2 * c, 2 * c, (2, 2)), conv(2 * c, 4 * c, (2, 1)))

    def forward(self, x):
        return self.net(x)


def prep(x):
    return torch.asinh(x.float()).unsqueeze(1)  # bright bursts span orders of magnitude


def pool(x):
    return torch.cat([x.mean((2, 3)), x.amax((2, 3))], 1)


def mlp(i, o=4, h=128):
    return nn.Sequential(nn.Linear(i, h), nn.ReLU(), nn.Linear(h, o))


class TwoChannel(nn.Module):
    """Method 4: early fusion, no weight sharing. Not symmetric; evaluation averages both orders."""

    def __init__(self, c=16):
        super().__init__()
        self.enc, self.head = Encoder(2, c), mlp(8 * c)

    def forward(self, a, b):
        return self.head(pool(self.enc(torch.cat([prep(a), prep(b)], 1))))


class Classic(nn.Module):
    """Method 5: late fusion, compare two vector embeddings."""

    def __init__(self, c=16):
        super().__init__()
        self.enc, self.emb, self.head = Encoder(1, c), mlp(8 * c, 64), mlp(128)

    def forward(self, a, b):
        ea, eb = self.emb(pool(self.enc(prep(a)))), self.emb(pool(self.enc(prep(b))))
        return self.head(torch.cat([(ea - eb).abs(), ea * eb], 1))


class Fusion(nn.Module):
    """Method 6 (primary): feature-map fusion after a correlation layer finds the time alignment.
    Symmetric because both directions are computed and averaged. align=False is the Stage 4 ablation."""

    def __init__(self, c=16, align=True):
        super().__init__()
        self.enc, self.align = Encoder(1, c), align
        self.beta = nn.Parameter(torch.tensor(10.0))
        self.fuse = nn.Sequential(conv(8 * c, 4 * c, (2, 2)), conv(4 * c, 4 * c, (2, 2)))
        self.head = mlp(8 * c + 2 * MAXLAG + 1)

    def side(self, ga, gb):
        pb = F.pad(gb, (MAXLAG, MAXLAG))
        T = ga.shape[-1]
        shifts = [pb[..., l:l + T] for l in range(2 * MAXLAG + 1)]
        na = F.normalize((ga - ga.mean(-1, keepdim=True)).flatten(1), dim=1)
        corr = torch.stack([(na * F.normalize((s - s.mean(-1, keepdim=True)).flatten(1), dim=1)).sum(1) for s in shifts], 1)
        if self.align:
            w = torch.softmax(self.beta * corr, 1)
            gb = sum(w[:, i, None, None, None] * s for i, s in enumerate(shifts))
        f = self.fuse(torch.cat([(ga - gb).abs(), ga * gb], 1))
        return self.head(torch.cat([pool(f), corr], 1))

    def forward(self, a, b):
        ga, gb = self.enc(prep(a)), self.enc(prep(b))
        return 0.5 * (self.side(ga, gb) + self.side(gb, ga))


class CrossAttention(nn.Module):
    """Method 7: time-frequency patches of one burst attend to patches of the other, both directions."""

    def __init__(self, c=16):
        super().__init__()
        d = 4 * c
        self.enc, self.att = Encoder(1, c), nn.MultiheadAttention(d, 4, batch_first=True)
        self.fpos = nn.Parameter(torch.zeros(1, d, 8, 1))  # frequency position only: time must stay shift-free
        self.head = nn.Sequential(nn.LayerNorm(4 * d), mlp(4 * d))  # head input was near-constant across pairs (update 2026-11-06_2015)

    def tokens(self, x):
        return (F.avg_pool2d(self.enc(prep(x)), 2) + self.fpos).flatten(2).transpose(1, 2)

    def side(self, ta, tb):
        y = self.att(ta, tb, tb, need_weights=False)[0]
        d, p = (ta - y).abs(), ta * y
        return self.head(torch.cat([d.mean(1), d.amax(1), p.mean(1), p.amax(1)], 1))

    def forward(self, a, b):
        ta, tb = self.tokens(a), self.tokens(b)
        return 0.5 * (self.side(ta, tb) + self.side(tb, ta))


MODELS = {4: TwoChannel, 5: Classic, 6: Fusion, 7: CrossAttention}


def lensed_score(logits):
    """Log-odds of lensed against the other three classes."""
    return logits[:, 0] - torch.logsumexp(logits[:, 1:], 1)


if __name__ == "__main__":  # self-check: shapes, and symmetry of the models that claim it
    torch.manual_seed(0)
    a, b = torch.randn(3, 256, 160), torch.randn(3, 256, 160)
    for k, M in MODELS.items():
        m = M().eval()
        with torch.no_grad():
            ab, ba = m(a, b), m(b, a)
        assert ab.shape == (3, 4) and torch.isfinite(ab).all()
        if k != 4:
            assert torch.allclose(ab, ba, atol=1e-4), f"model {k} depends on member order"
        print(k, M.__name__, sum(p.numel() for p in m.parameters()), "params")
    # the alignment must undo a time shift: correlation peaks at the planted lag
    m = Fusion().eval()
    g = torch.randn(1, 64, 16, 80)
    gb = torch.roll(g, 5, -1)
    pb = F.pad(gb, (MAXLAG, MAXLAG))
    c = [F.cosine_similarity((g - g.mean(-1, keepdim=True)).flatten(1), (s - s.mean(-1, keepdim=True)).flatten(1)).item()
         for s in (pb[..., l:l + 80] for l in range(2 * MAXLAG + 1))]
    assert max(range(len(c)), key=c.__getitem__) == MAXLAG + 5
    print("models self-check OK")
