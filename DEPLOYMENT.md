# Streamlit Cloud 배포 가이드

이 문서는 Workload Analysis Dashboard를 Streamlit Cloud에 배포하는 방법을 설명합니다.

## 필요한 파일 목록

GitHub에 다음 파일들을 푸시해야 합니다:

### 필수 파일
- `plot_dashboard.py` - 메인 Streamlit 앱 파일
- `requirements.txt` - Python 패키지 의존성
- `distribution_plots/` - Distribution plot 이미지 폴더 (전체)
- `sampling_method_distribution_plots/` - Sampling method plot 이미지 폴더 (전체)

### 선택 파일
- `README.md` - 프로젝트 설명 (선택사항)
- `.gitignore` - Git 무시 파일 (선택사항)

## GitHub에 푸시하는 방법

### 1. Git 저장소 초기화 (아직 안 했다면)

```bash
cd /data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/tools

# Git 저장소가 없다면 초기화
git init

# 원격 저장소 추가 (GitHub 저장소 URL로 변경)
git remote add origin https://github.com/[사용자명]/[저장소명].git
```

### 2. 필요한 파일만 추가

```bash
# 필수 파일들 추가
git add plot_dashboard.py
git add requirements.txt
git add distribution_plots/
git add sampling_method_distribution_plots/

# .gitignore 파일 생성 (선택사항, 큰 파일 제외용)
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo ".streamlit/" >> .gitignore
git add .gitignore
```

### 3. 커밋 및 푸시

```bash
git commit -m "Add Streamlit dashboard for workload analysis"
git push -u origin main
# 또는 master 브랜치를 사용한다면
# git push -u origin master
```

## Streamlit Cloud에 배포하기

### 1. Streamlit Cloud 접속
- https://streamlit.io/cloud 에 접속
- GitHub 계정으로 로그인

### 2. 새 앱 배포
1. "New app" 버튼 클릭
2. GitHub 저장소 선택
3. Branch 선택 (보통 `main` 또는 `master`)
4. Main file path: `tools/plot_dashboard.py` 입력
5. "Deploy!" 클릭

### 3. 배포 완료
- 배포가 완료되면 공개 URL이 생성됩니다
- 이 URL을 공유하면 누구나 대시보드를 볼 수 있습니다

## 주의사항

1. **파일 크기**: 
   - `distribution_plots/`와 `sampling_method_distribution_plots/` 폴더가 약 36MB입니다
   - GitHub의 무료 계정은 파일 크기 제한이 있으므로 확인이 필요합니다
   - 필요하다면 Git LFS를 사용하거나, 일부 버전만 포함할 수 있습니다

2. **경로 설정**:
   - 코드는 이미 상대 경로로 수정되어 있습니다
   - `plot_dashboard.py`는 `tools/` 폴더에 있어야 합니다

3. **의존성**:
   - `requirements.txt`에 필요한 패키지가 모두 포함되어 있습니다
   - Streamlit Cloud가 자동으로 설치합니다

## 문제 해결

### 배포 실패 시
- `requirements.txt` 파일이 올바른지 확인
- `plot_dashboard.py`의 경로가 올바른지 확인
- GitHub 저장소에 파일이 제대로 푸시되었는지 확인

### 이미지가 표시되지 않을 때
- `distribution_plots/`와 `sampling_method_distribution_plots/` 폴더가 GitHub에 포함되었는지 확인
- 폴더 구조가 올바른지 확인



