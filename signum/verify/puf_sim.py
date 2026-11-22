"""SIGNUM 설계 검증 계산 2: 광학 PUF 몬테카를로 시뮬레이션.
- 진품 재측정(스마트폰 촬영 노이즈·정렬 오차) vs 다른 개체 vs 정밀 복제 시도의
  비트 해밍 거리(HD) 분포를 비교해 오인식률을 추정한다.
- 물리 모델은 단순화된 것이며, 실제 값은 시편 측정으로 확정해야 한다."""
import numpy as np, json, sys
rng = np.random.default_rng(2026)

R_OUT, R_IN = 18.5, 3.0          # mm, 각인 영역
PLANES, VOX = 60, 220            # 분 층: 60개 방사면 × 면당 각인점 수
PIX = 0.04                       # mm, 촬영 해상도(스마트폰 매크로 ~40µm/px 가정)
N = int(2*R_OUT/PIX)+1

def make_watch():
    r   = rng.uniform(R_IN, R_OUT, (PLANES, VOX))
    lat = rng.normal(0, 0.015, (PLANES, VOX))            # 면 두께 내 위치(15µm)
    b   = rng.lognormal(0, 0.6, (PLANES, VOX))            # 각인점 형태(산란 세기) 무작위성
    return dict(r=r, lat=lat, b=b)

def clone(w, pos_err_um, bright_err):
    """공격자: 진품을 측정해 각인점 위치·세기를 복제. 측정+재각인 오차를 가정."""
    c = {k: v.copy() for k, v in w.items()}
    c["r"]   = c["r"]   + rng.normal(0, pos_err_um/1000, c["r"].shape)
    c["lat"] = c["lat"] + rng.normal(0, pos_err_um/1000, c["lat"].shape)
    if bright_err is None:   c["b"] = rng.lognormal(0, 0.6, c["b"].shape)   # 세기 통제 불가
    else:                    c["b"] = c["b"]*rng.lognormal(0, bright_err, c["b"].shape)
    return c

# Gaussian blur kernel (phone optics), separable via FFT
yy = np.fft.fftfreq(N)
G = np.exp(-2*(np.pi*1.3)**2*(yy[:,None]**2+yy[None,:]**2))

def render(w, chal, shift=(0,0), rot_deg=0.0, noise=0.04):
    leds, amps = chal
    img = np.zeros((N, N))
    for p, a in zip(leds, amps):
        th = 2*np.pi*p/PLANES + np.deg2rad(rot_deg)
        r, lat, b = w["r"][p], w["lat"][p], w["b"][p]
        d = R_OUT - r
        sig = (0.10 + 2*d*0.025)/2.355                     # 빔 폭 성장 (budget.py와 동일)
        inten = a*b*np.exp(-0.5*(lat/sig)**2)*np.exp(-0.03*d)
        x = r*np.sin(th) + lat*np.cos(th) + shift[0]
        y = -r*np.cos(th) + lat*np.sin(th) + shift[1]
        ix = np.clip(((x+R_OUT)/PIX).astype(int), 0, N-1)
        iy = np.clip(((y+R_OUT)/PIX).astype(int), 0, N-1)
        np.add.at(img, (iy, ix), inten)
    img = np.real(np.fft.ifft2(np.fft.fft2(img)*G))
    img = img*(1+rng.normal(0, noise, img.shape)) + rng.normal(0, noise*img.mean(), img.shape)
    return img

RS = np.arange(R_IN+0.5, R_OUT-0.3, 0.08)          # 반경 방향 샘플 (80µm 간격)
def profiles(img, chal):
    """켜진 각 방사면을 따라 밝기 프로파일을 읽는다(공칭 위치 = 다이얼 기준마크로 정렬).
    고정 기하(선 모양)가 아니라 각인점의 무작위 분포·세기만 남긴다."""
    out = []
    for p in chal[0]:
        th = 2*np.pi*p/PLANES
        acc = 0
        for off in (-0.04, 0, 0.04):                   # 선 폭 방향 3픽셀 평균
            x = RS*np.sin(th) + off*np.cos(th); y = -RS*np.cos(th) + off*np.sin(th)
            ix = np.clip(((x+R_OUT)/PIX).round().astype(int), 0, N-1)
            iy = np.clip(((y+R_OUT)/PIX).round().astype(int), 0, N-1)
            acc = acc + img[iy, ix]
        out.append(acc)
    return np.array(out)

def bits(prof):
    k = 9; ker = np.ones(k)/k
    ma = np.array([np.convolve(np.pad(p, k//2, mode="edge"), ker, mode="valid") for p in prof])
    return (prof > ma).ravel()

def challenge():
    leds = rng.choice(PLANES, 12, replace=False)
    return leds, rng.choice([0.4, 0.7, 1.0], 12)

def hd(a, b, mask): return np.mean(a[mask] != b[mask])

def phone_capture(w, chal):
    return render(w, chal, shift=rng.normal(0, 0.012, 2), rot_deg=rng.normal(0, 0.05))

T = int(sys.argv[1]) if len(sys.argv) > 1 else 40
res = {"genuine": [], "other": []}
clones = {"위치 1µm · 세기 ±10%": (1, 0.10), "위치 3µm · 세기 ±30%": (3, 0.30),
          "위치 1µm · 세기 통제불가": (1, None), "위치 10µm · 세기 통제불가": (10, None)}
for k in clones: res[k] = []
for t in range(T):
    w = make_watch(); ch = challenge()
    rb = bits(profiles(render(w, ch, noise=0.01), ch))   # 공장 등록(고정 지그, 저노이즈)
    mask = np.ones_like(rb, dtype=bool)
    res["genuine"].append(hd(rb, bits(profiles(phone_capture(w, ch), ch)), mask))
    res["other"].append(hd(rb, bits(profiles(phone_capture(make_watch(), ch), ch)), mask))
    for k, (pe, be) in clones.items():
        res[k].append(hd(rb, bits(profiles(phone_capture(clone(w, pe, be), ch), ch)), mask))
    print(f"\r{t+1}/{T}", end="", file=sys.stderr)
print(file=sys.stderr)

thr = 0.15
summary = {}
for k, v in res.items():
    v = np.array(v)
    summary[k] = dict(mean=round(float(v.mean()),3), sd=round(float(v.std()),3),
                      min=round(float(v.min()),3), max=round(float(v.max()),3),
                      pass_rate=round(float(np.mean(v < thr)),3))
    print(f"{k:22s} HD 평균 {v.mean():.3f} ± {v.std():.3f}  [{v.min():.3f}–{v.max():.3f}]  통과율(HD<{thr}) {np.mean(v<thr)*100:5.1f}%")
# 정규 근사 오인식률 (진품 거부 / 위조 통과), 독립 챌린지 3회 연속 요구 시
from math import erf, sqrt
def tail(mu, sd, x, upper):
    z = (x-mu)/sd; p = 0.5*(1+erf(z/sqrt(2)))
    return 1-p if upper else p
g = summary["genuine"]
frr1 = tail(g["mean"], g["sd"], thr, True)
print(f"진품 거부율(1회) ≈ {frr1:.2e} → 3회 중 2회 통과 규칙 시 ≈ {3*frr1**2:.2e}")
for k in ["other"]+list(clones):
    s = summary[k]; far1 = tail(s["mean"], s["sd"], thr, False)
    summary[k]["far_1"] = far1; summary[k]["far_3"] = far1**3
    print(f"위조 통과율 {k:22s} 1회 ≈ {far1:.1e} · 3회 연속 ≈ {far1**3:.1e}")
json.dump(dict(threshold=thr, trials=T, summary=summary), open(__file__.replace("puf_sim.py","puf_result.json"),"w"), ensure_ascii=False, indent=1)
