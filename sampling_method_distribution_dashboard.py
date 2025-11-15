import streamlit as st
import os
from pathlib import Path
from PIL import Image
import re

# 페이지 설정
st.set_page_config(
    page_title="Sampling Method Distribution Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 제목 및 설명
st.title("📊 Sampling Method Distribution Dashboard")
st.markdown("""
이 대시보드는 다양한 벤치마크와 데이터베이스에 대한 Sampling Method 분포를 시각화합니다.
왼쪽 사이드바에서 벤치마크 타입과 데이터베이스를 선택하여 필터링할 수 있습니다.
""")

# 이미지 디렉토리 경로
IMAGE_DIR = Path("/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/tools/sampling_method_distribution_plots/v15")

@st.cache_data
def load_image_files():
    """이미지 파일 목록을 로드하고 파싱합니다."""
    if not IMAGE_DIR.exists():
        return []
    
    images = []
    pattern = re.compile(r'^(.+?)_(.+?)_sampling_method_distribution\.png$')
    
    for file_path in sorted(IMAGE_DIR.glob("*.png")):
        match = pattern.match(file_path.name)
        if match:
            benchmark_type = match.group(1)
            db_name = match.group(2)
            images.append({
                'file_path': file_path,
                'benchmark_type': benchmark_type,
                'db_name': db_name,
                'filename': file_path.name
            })
        else:
            # 패턴이 맞지 않는 경우도 포함 (fallback)
            images.append({
                'file_path': file_path,
                'benchmark_type': 'Unknown',
                'db_name': file_path.stem,
                'filename': file_path.name
            })
    
    return images

# 이미지 파일 로드
all_images = load_image_files()

if not all_images:
    st.error(f"❌ 이미지 파일을 찾을 수 없습니다. 경로를 확인해주세요: {IMAGE_DIR}")
    st.stop()

# 사이드바 필터
st.sidebar.header("🔍 필터 옵션")

# 벤치마크 타입 필터
benchmark_types = sorted(set(img['benchmark_type'] for img in all_images))
selected_benchmarks = st.sidebar.multiselect(
    "벤치마크 타입 선택",
    options=benchmark_types,
    default=benchmark_types,
    help="하나 이상의 벤치마크 타입을 선택하세요"
)

# 데이터베이스 필터
db_names = sorted(set(img['db_name'] for img in all_images))
selected_dbs = st.sidebar.multiselect(
    "데이터베이스 선택",
    options=db_names,
    default=db_names,
    help="하나 이상의 데이터베이스를 선택하세요"
)

# 선택된 항목이 없으면 전체를 사용
if not selected_benchmarks:
    selected_benchmarks = benchmark_types
if not selected_dbs:
    selected_dbs = db_names

# 필터링된 이미지
filtered_images = [
    img for img in all_images
    if img['benchmark_type'] in selected_benchmarks
    and img['db_name'] in selected_dbs
]

# 통계 정보 표시
st.sidebar.markdown("---")
st.sidebar.metric("총 이미지 수", len(all_images))
st.sidebar.metric("필터링된 이미지 수", len(filtered_images))

# 필터링된 이미지가 없는 경우
if not filtered_images:
    st.warning("⚠️ 선택한 필터 조건에 맞는 이미지가 없습니다. 필터를 조정해주세요.")
    st.stop()

# 이미지 표시 옵션
st.sidebar.markdown("---")
st.sidebar.header("⚙️ 표시 옵션")
images_per_row = st.sidebar.selectbox(
    "한 행에 표시할 이미지 수",
    options=[1, 2, 3],
    index=1,
    help="화면 크기에 따라 조정하세요"
)

# 이미지 표시 모드
display_mode = st.sidebar.radio(
    "표시 모드",
    options=["그리드 뷰", "리스트 뷰"],
    index=0,
    help="이미지를 그리드 형태로 보거나 리스트 형태로 볼 수 있습니다"
)

# 메인 컨텐츠 영역
if display_mode == "그리드 뷰":
    # 그리드 레이아웃으로 이미지 표시
    num_cols = images_per_row
    
    for i in range(0, len(filtered_images), num_cols):
        cols = st.columns(num_cols)
        
        for j, col in enumerate(cols):
            if i + j < len(filtered_images):
                img_data = filtered_images[i + j]
                
                with col:
                    # 이미지 로드 및 표시
                    try:
                        image = Image.open(img_data['file_path'])
                        st.image(
                            image,
                            caption=f"{img_data['benchmark_type']} - {img_data['db_name']}",
                            use_container_width=True
                        )
                        
                        # 다운로드 버튼
                        with open(img_data['file_path'], "rb") as file:
                            st.download_button(
                                label="📥 다운로드",
                                data=file,
                                file_name=img_data['filename'],
                                mime="image/png",
                                key=f"download_{i+j}",
                                use_container_width=True
                            )
                    except Exception as e:
                        st.error(f"이미지 로드 오류: {e}")
                        st.text(img_data['filename'])

else:
    # 리스트 뷰로 이미지 표시
    for img_data in filtered_images:
        st.markdown("---")
        st.subheader(f"{img_data['benchmark_type']} - {img_data['db_name']}")
        
        try:
            image = Image.open(img_data['file_path'])
            st.image(image, use_container_width=True)
            
            # 다운로드 버튼
            with open(img_data['file_path'], "rb") as file:
                st.download_button(
                    label=f"📥 {img_data['filename']} 다운로드",
                    data=file,
                    file_name=img_data['filename'],
                    mime="image/png",
                    key=f"download_list_{img_data['filename']}"
                )
        except Exception as e:
            st.error(f"이미지 로드 오류: {e}")
            st.text(img_data['filename'])

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Sampling Method Distribution Dashboard | HybridSQL-Benchmark</p>
</div>
""", unsafe_allow_html=True)



