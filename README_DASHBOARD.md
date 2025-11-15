# Workload Analysis Dashboard

Streamlit을 사용한 Workload 분석 대시보드입니다.

## 기능

3종류의 plot을 한 화면에서 비교하여 볼 수 있습니다:

1. **Distribution Comparison**: Initial distribution과 Generated distribution 비교
2. **Literal Distribution**: Masking count별 literal 분포 비교
3. **Sampling Method Distribution**: Masking count별 sampling method 분포

## 실행 방법

```bash
cd /data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/tools
streamlit run plot_dashboard.py
```

또는 포트를 지정하여 실행:

```bash
streamlit run plot_dashboard.py --server.port 8501
```

## 사용 방법

1. **사이드바에서 선택:**
   - **버전**: v16, v15 등 사용 가능한 버전 선택
   - **Split**: Dev 또는 Train 선택
   - **Distribution**: uniform, zipf_random, zipf_query_len 중 선택

2. **메인 영역에서 선택:**
   - **Benchmark**: BIRD, EHRSQL, ScienceBenchmark 중 선택
   - **DB**: 선택한 Benchmark에 해당하는 DB 선택

3. **3종류의 plot이 자동으로 표시됩니다:**
   - 왼쪽: Distribution Comparison
   - 가운데: Literal Distribution
   - 오른쪽: Sampling Method Distribution

## 디렉토리 구조

대시보드는 다음 디렉토리에서 plot을 찾습니다:

- `tools/distribution/{version}/{distribution}/` - Distribution comparison plots
- `tools/literal_distribution_plots/{version}/{split}/{distribution}/` - Literal distribution plots
- `tools/sampling_method_distribution_plots/{version}/{split}/{distribution}/` - Sampling method distribution plots

## 요구사항

```bash
pip install streamlit
```




