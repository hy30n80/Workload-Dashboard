#!/usr/bin/env python3
"""
distribution_plots의 v16 구조를 v10 구조로 재구성하는 스크립트
v10 구조: v10/Dev/uniform/, v10/Train/uniform/ 등
v16 구조: v16/uniform/ (Dev와 Train이 같은 폴더에)
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple

def reorganize_v16_to_v10_structure(base_dir: str, dry_run: bool = True) -> None:
    """
    v16 구조를 v10 구조로 재구성합니다.
    
    Args:
        base_dir: distribution_plots 디렉토리 경로
        dry_run: True면 실제로 이동하지 않고 미리보기만 표시
    """
    base_path = Path(base_dir)
    v16_path = base_path / "v16"
    
    if not v16_path.exists():
        print(f"❌ v16 디렉토리를 찾을 수 없습니다: {v16_path}")
        return
    
    # 이동할 파일 목록
    files_to_move: List[Tuple[Path, Path]] = []
    
    # distribution 타입별로 처리
    for dist_type in ["uniform", "zipf_query_len", "zipf_random"]:
        dist_dir = v16_path / dist_type
        
        if not dist_dir.exists():
            continue
        
        # 파일명에서 Split 추출 (Dev_ 또는 Train_로 시작)
        for file_path in dist_dir.glob("*.png"):
            filename = file_path.name
            
            if filename.startswith("Dev_"):
                split = "Dev"
            elif filename.startswith("Train_"):
                split = "Train"
            else:
                print(f"⚠️  파일명 형식을 알 수 없습니다: {filename}")
                continue
            
            # 새로운 경로: v16/Dev/uniform/ 또는 v16/Train/uniform/
            new_dir = v16_path / split / dist_type
            new_path = new_dir / filename
            
            files_to_move.append((file_path, new_path))
    
    if not files_to_move:
        print("✅ 재구성할 파일이 없습니다.")
        return
    
    print(f"\n📋 총 {len(files_to_move)}개의 파일을 재구성합니다.\n")
    
    # 디렉토리 생성 및 파일 이동
    moved_count = 0
    for old_path, new_path in files_to_move:
        if dry_run:
            print(f"  [DRY RUN] {old_path.relative_to(v16_path)} -> {new_path.relative_to(v16_path)}")
        else:
            try:
                # 새 디렉토리 생성
                new_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 파일 이동
                shutil.move(str(old_path), str(new_path))
                print(f"  ✅ {old_path.name} -> {new_path.parent.name}/{new_path.name}")
                moved_count += 1
            except Exception as e:
                print(f"  ❌ {old_path.name} 이동 실패: {e}")
    
    # 빈 디렉토리 정리
    if not dry_run:
        print("\n🧹 빈 디렉토리 정리 중...")
        for dist_type in ["uniform", "zipf_query_len", "zipf_random"]:
            dist_dir = v16_path / dist_type
            if dist_dir.exists():
                try:
                    # 디렉토리가 비어있으면 삭제
                    if not any(dist_dir.iterdir()):
                        dist_dir.rmdir()
                        print(f"  ✅ 빈 디렉토리 삭제: {dist_dir.name}")
                except Exception as e:
                    print(f"  ⚠️  디렉토리 삭제 실패: {e}")
        
        print(f"\n✅ {moved_count}개의 파일 재구성 완료!")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='distribution_plots v16 구조를 v10 구조로 재구성')
    parser.add_argument(
        '--plots-dir',
        type=str,
        default='tools/distribution_plots',
        help='distribution_plots 디렉토리 경로 (기본값: tools/distribution_plots)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='실제로 파일을 재구성합니다 (기본값: dry-run 모드)'
    )
    
    args = parser.parse_args()
    
    # 절대 경로로 변환
    base_dir = os.path.abspath(args.plots_dir)
    if not os.path.isabs(args.plots_dir):
        # 상대 경로인 경우 스크립트 위치 기준으로 계산
        script_dir = Path(__file__).parent.parent
        base_dir = script_dir / args.plots_dir
    
    print(f"🔍 distribution_plots 디렉토리: {base_dir}")
    
    if args.execute:
        print("\n⚠️  실제로 파일을 재구성합니다!")
        response = input("계속하시겠습니까? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ 취소되었습니다.")
            return
        reorganize_v16_to_v10_structure(str(base_dir), dry_run=False)
        print("\n✅ 재구성 완료!")
    else:
        print("\n📝 [DRY RUN 모드] 실제로 재구성하지 않고 미리보기만 표시합니다.")
        print("   실제로 재구성하려면 --execute 플래그를 추가하세요.\n")
        reorganize_v16_to_v10_structure(str(base_dir), dry_run=True)
        print("\n💡 실제로 재구성하려면: python reorganize_distribution_plots.py --execute")

if __name__ == "__main__":
    main()




