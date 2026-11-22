"""SIGNUM 설계 검증 계산 1: 광학 휘도 · 햇빛 대비 · 빔 폭 · 전력 예산.
모든 입력값은 아래 상수로 명시. 가정이 바뀌면 다시 실행."""
import math
# --- 빔 성형 (마이크로 LED + 원통형 마이크로렌즈) ---
src_w_mm = 0.10        # 마이크로 LED 발광부 폭
f_mm     = 2.0         # 렌즈 초점거리
path_mm  = 17.0        # 테두리 → 중심 허브(r=2mm)까지 경로
half_div = src_w_mm/(2*f_mm)               # rad
w_end    = src_w_mm + 2*path_mm*half_div
print(f"[빔] 반발산각 {math.degrees(half_div):.2f}° · 허브 도달 폭 {w_end:.2f} mm")
# --- 휘도 ---
P_led_mW   = 3.0      # 100µm 녹색 마이크로 LED 광출력 @10mA (보수적)
couple     = 0.5      # 렌즈 결합 효율
scatter    = 0.40     # 경로 상 각인점 산란 비율
up_frac    = 0.5      # 위쪽(관찰자 방향)으로 나가는 비율
hand_len, hand_w = 15e-3, 0.6e-3          # 보이는 바늘 면적 (평균 폭)
M = P_led_mW*1e-3*couple*scatter*up_frac/(hand_len*hand_w)   # W/m^2
L_rad = M/math.pi
for name,eff in [("녹색 520nm",0.71*683),("청록 500nm",0.323*683)]:
    print(f"[휘도] {name}: {L_rad*eff:,.0f} cd/m²")
L_hand = L_rad*0.71*683
# --- 햇빛 대비 ---
for lux,label in [(100000,"직사광선"),(10000,"흐린 야외"),(500,"실내")]:
    for rho,desc in [(0.07,"AR 없음"),(0.025,"AR+무광 흑색 세라믹")]:
        Lb = lux*rho/math.pi
        print(f"[대비] {label:6s} {desc:14s} 배경 {Lb:7.0f} cd/m² → 대비 {(L_hand+Lb)/Lb:5.1f}:1")
# --- 전력 예산 ---
V, I = 3.0, 0.010
led_equiv = 1 + 1.5     # 분 1개 + 시 3개(100%+25%+25%)
E_full = led_equiv*V*I*3.0       # 3초 점등, 최대 밝기
E_in   = E_full*0.10             # 실내 10% 밝기
glances, outdoor = 150, 0.20
E_day = glances*outdoor*E_full + glances*(1-outdoor)*E_in
mAh_led  = E_day/V/3.6
mAh_base = (2e-6+3e-6)*24*1000 + 0.05        # MCU RTC+가속도 상시, BLE 동기 1회
mAh_day = mAh_led+mAh_base
cap = 100
print(f"[전력] 글랜스 1회 최대 {E_full*1000:.0f} mJ · 하루 {mAh_day:.2f} mAh → {cap} mAh 셀 {cap/mAh_day:.0f}일")
