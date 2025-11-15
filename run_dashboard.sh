#!/bin/bash

# Sampling Method Distribution Dashboard 실행 스크립트

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Sampling Method Distribution Dashboard를 시작합니다..."
echo ""

# 패키지 설치 확인
echo "📦 필요한 패키지 확인 중..."
python3 -c "import streamlit" 2>/dev/null || {
    echo "⚠️  streamlit이 설치되지 않았습니다. 설치 중..."
    pip install streamlit pillow
}

echo ""
echo "✅ 대시보드 실행 중..."
echo "🌐 브라우저에서 http://localhost:8501 로 접속하세요"
echo ""

# 대시보드 실행
streamlit run sampling_method_distribution_dashboard.py



