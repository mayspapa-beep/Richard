# SIGNUM 검증 스크립트

| 파일 | 내용 |
|---|---|
| `budget.py` | 빔 폭 · 바늘 휘도 · 햇빛 대비 · 전력 예산 계산 |
| `puf_sim.py` | 광학 지문(PUF) 몬테카를로 시뮬레이션: 진품 재촬영 / 다른 개체 / 정밀 복제 4종 |
| `puf_result.json` | `python3 puf_sim.py 60` 실행 결과 (판정 기준 HD < 0.15) |

```
python3 budget.py
python3 puf_sim.py 60     # numpy 필요, 약 1분
```

모든 가정값은 각 스크립트 상단 상수에 있습니다. 물리 모델은 단순화된 것이므로
산란율·빔 폭·폰 기종별 재현성은 시편 실측(검증 계획 Gate 1–2)으로 확정해야 합니다.
