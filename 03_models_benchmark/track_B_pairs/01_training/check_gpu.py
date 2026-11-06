"""Stage 0 GPU gate (plan 2026-11-06_1223): sm_120 support and one real mixed-precision conv step."""
import torch

assert torch.cuda.is_available(), "no CUDA"
cap, arch = torch.cuda.get_device_capability(), torch.cuda.get_arch_list()
print(torch.__version__, "cuda", torch.version.cuda, torch.cuda.get_device_name(0), cap, arch)
assert cap == (12, 0) and "sm_120" in arch, "build has no sm_120 kernels"
net = torch.nn.Sequential(torch.nn.Conv2d(2, 32, 3, padding=1), torch.nn.ReLU(), torch.nn.AdaptiveAvgPool2d(1),
                          torch.nn.Flatten(), torch.nn.Linear(32, 4)).cuda()
opt = torch.optim.AdamW(net.parameters())
x, y = torch.randn(64, 2, 256, 160, device="cuda"), torch.randint(0, 4, (64,), device="cuda")
with torch.autocast("cuda", dtype=torch.bfloat16):
    loss = torch.nn.functional.cross_entropy(net(x), y)
loss.backward()
opt.step()
assert torch.isfinite(loss) and all(torch.isfinite(p).all() for p in net.parameters())
print("GPU gate PASS, loss", float(loss))
