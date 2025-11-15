# Sampling Method Distribution Dashboard

이 대시보드는 Sampling Method 분포 플롯을 시각화하고 탐색할 수 있는 Streamlit 기반 웹 애플리케이션입니다.

## 설치 방법

### 1. 필요한 패키지 설치

```bash
pip install streamlit pillow
```

또는 requirements 파일을 사용:

```bash
pip install -r requirements_dashboard.txt
```

### 2. 대시보드 실행

```bash
cd /data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/tools
streamlit run sampling_method_distribution_dashboard.py
```

브라우저가 자동으로 열리며, 기본적으로 `http://localhost:8501`에서 대시보드에 접근할 수 있습니다.

## 사용 방법

### 기본 기능

1. **필터링**: 왼쪽 사이드바에서 벤치마크 타입과 데이터베이스를 선택하여 필터링할 수 있습니다.
2. **표시 모드**: 
   - **그리드 뷰**: 여러 이미지를 한 번에 볼 수 있습니다 (1, 2, 3열 선택 가능)
   - **리스트 뷰**: 각 이미지를 크게 하나씩 볼 수 있습니다
3. **다운로드**: 각 이미지 아래의 다운로드 버튼을 클릭하여 이미지를 저장할 수 있습니다

### 연구자와 공유하기

#### 로컬 네트워크에서 공유

같은 네트워크에 있는 다른 컴퓨터에서 접근하려면:

```bash
streamlit run sampling_method_distribution_dashboard.py --server.address 0.0.0.0
```

그 후 다른 컴퓨터에서 `http://[서버IP]:8501`로 접근할 수 있습니다.

#### 원격 서버에서 실행

SSH 터널링을 사용하여 원격 서버에서 실행 중인 대시보드를 로컬에서 접근:

```bash
# 터미널 1: 서버에서 대시보드 실행
streamlit run sampling_method_distribution_dashboard.py

# 터미널 2: 로컬에서 SSH 터널 생성
ssh -L 8501:localhost:8501 [사용자명]@[서버주소]
```

그 후 로컬 브라우저에서 `http://localhost:8501`로 접근할 수 있습니다.

#### Streamlit Cloud에 배포 (선택사항)

1. GitHub에 코드를 푸시
2. [Streamlit Cloud](https://streamlit.io/cloud)에 가입
3. GitHub 저장소를 연결하여 배포

## 파일 구조

```
tools/
├── sampling_method_distribution_dashboard.py  # 대시보드 메인 파일
├── sampling_method_distribution_plots/
│   └── v15/
│       ├── BIRD_*.png
│       ├── EHRSQL_*.png
│       └── ScienceBenchmark_*.png
└── README_dashboard.md  # 이 파일
```

## 문제 해결

### 이미지가 표시되지 않는 경우

- 이미지 파일 경로가 올바른지 확인하세요
- 파일 권한을 확인하세요: `ls -l /data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/tools/sampling_method_distribution_plots/v15/`

### 포트가 이미 사용 중인 경우

다른 포트를 사용하려면:

```bash
streamlit run sampling_method_distribution_dashboard.py --server.port 8502
```

## 추가 기능 제안

필요한 경우 다음 기능을 추가할 수 있습니다:
- 이미지 확대/축소 기능
- 통계 요약 표시
- CSV/JSON 데이터 내보내기
- 비교 모드 (여러 이미지 나란히 비교)



