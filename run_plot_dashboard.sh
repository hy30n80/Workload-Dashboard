#!/bin/bash

# Plot Dashboard 실행 스크립트 (네트워크 공유용)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Plot Dashboard를 시작합니다..."
echo ""

# 패키지 설치 확인
echo "📦 필요한 패키지 확인 중..."
python3 -c "import streamlit" 2>/dev/null || {
    echo "⚠️  streamlit이 설치되지 않았습니다. 설치 중..."
    pip install streamlit pillow
}

# 서버 IP 주소 확인
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ 대시보드 실행 중..."
echo "🌐 로컬 접속: http://localhost:8501"
echo "🌐 네트워크 접속: http://${SERVER_IP}:8501"
echo ""
echo "💡 다른 작업자가 접속하려면 위의 네트워크 주소를 사용하세요"
echo ""

# 대시보드 실행 (0.0.0.0으로 바인딩하여 네트워크 접근 허용)
streamlit run plot_dashboard.py \
    --server.address 0.0.0.0 \
    --server.port 8501

