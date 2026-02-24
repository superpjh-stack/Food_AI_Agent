# Archive Index — 2026-02

## Archived Features

| Feature | Archived At | Match Rate | Iterations | Archive Path |
|---------|------------|:----------:|:----------:|--------------|
| food-ai-agent | 2026-02-23 | 96% | 1 | [food-ai-agent/](./food-ai-agent/) |
| mvp2-purchase | 2026-02-24 | 100% | 1 | [mvp2-purchase/](./mvp2-purchase/) |
| mvp3-demand | 2026-02-24 | 100% | 1 | [mvp3-demand/](./mvp3-demand/) |

## mvp3-demand

- **제품명**: MVP 3 수요예측/원가최적화/클레임 관리
- **PDCA 기간**: 2026-02-24 (단일 세션)
- **개발 방식**: bkit PDCA (pdca-iterator + gap-detector + report-generator)
- **최종 Match Rate**: 100% (116/116 items)
- **이터레이션**: Act-1 단 1회
- **신규 파일**: ~130개 (ORM 4 + Service 1 + Tools 1 + API 4 + Schemas 4 + Frontend 56 + Tests 6)

### 문서 목록

| 문서 | 경로 |
|------|------|
| Plan | [mvp3-demand.plan.md](./mvp3-demand/mvp3-demand.plan.md) |
| Design | [mvp3-demand.design.md](./mvp3-demand/mvp3-demand.design.md) |
| Analysis | [mvp3-demand.analysis.md](./mvp3-demand/mvp3-demand.analysis.md) |
| Report | [mvp3-demand.report.md](./mvp3-demand/mvp3-demand.report.md) |

## mvp2-purchase

- **제품명**: MVP 2 구매/발주/BOM 자동화
- **PDCA 기간**: 2026-02-23 ~ 2026-02-24
- **개발 방식**: bkit PDCA (gap-detector + pdca-iterator + report-generator)
- **최종 Match Rate**: 100% (120/120 items)
- **이터레이션**: Act-1 단 1회
- **신규 파일**: ~120개 (ORM 2 + API 4 + Tools 1 + Frontend 30+ + Tests 6)
- **배포 아키텍처**: GCloud (Cloud Run + Cloud SQL PG16 + Vercel)

### 문서 목록

| 문서 | 경로 |
|------|------|
| Plan | [mvp2-purchase.plan.md](./mvp2-purchase/mvp2-purchase.plan.md) |
| Design | [mvp2-purchase.design.md](./mvp2-purchase/mvp2-purchase.design.md) |
| Analysis | [mvp2-purchase.analysis.md](./mvp2-purchase/mvp2-purchase.analysis.md) |
| Report | [mvp2-purchase.report.md](./mvp2-purchase/mvp2-purchase.report.md) |

## food-ai-agent

- **제품명**: Food AI Agent (위탁급식 AI 자동화 시스템)
- **PDCA 기간**: 2026-02-23 (단일 세션)
- **개발 방식**: bkit CTO Team Mode (claude-opus-4-6)
- **최종 Match Rate**: 96%
- **통합 테스트**: 52개

### 문서 목록

| 문서 | 경로 |
|------|------|
| Plan | [food-ai-agent.plan.md](./food-ai-agent/food-ai-agent.plan.md) |
| Design | [food-ai-agent.design.md](./food-ai-agent/food-ai-agent.design.md) |
| Analysis | [food-ai-agent.analysis.md](./food-ai-agent/food-ai-agent.analysis.md) |
| Report | [food-ai-agent.report.md](./food-ai-agent/food-ai-agent.report.md) |
