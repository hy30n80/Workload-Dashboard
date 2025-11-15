#!/usr/bin/env python3
"""
워크로드 JSON 파일명을 변경하는 스크립트
- "uniform" -> "uniform_rank"
- "zipf(random)" -> "zipf_random"
- "zipf(query_len)" -> "zipf_query_len"
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def find_workload_files(base_dir: str) -> List[Tuple[str, str]]:
    """
    워크로드 디렉토리에서 변경이 필요한 파일들을 찾습니다.
    Returns: [(old_path, new_path), ...]
    """
    files_to_rename = []
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print(f"❌ 디렉토리를 찾을 수 없습니다: {base_dir}")
        return files_to_rename
    
    # 파일명 매핑 규칙
    rename_rules = [
        # uniform -> uniform_rank
        (r'^uniform_(\d+[km]?)\.json$', r'uniform_rank_\1.json'),
        (r'^uniform\.json$', r'uniform_rank.json'),
        # zipf(random) -> zipf_random
        (r'^zipf\(random\)_(\d+[km]?)\.json$', r'zipf_random_\1.json'),
        (r'^zipf\(random\)\.json$', r'zipf_random.json'),
        # zipf(query_len) -> zipf_query_len
        (r'^zipf\(query_len\)_(\d+[km]?)\.json$', r'zipf_query_len_\1.json'),
        (r'^zipf\(query_len\)\.json$', r'zipf_query_len.json'),
    ]
    
    # 재귀적으로 모든 JSON 파일 찾기
    for json_file in base_path.rglob("*.json"):
        old_name = json_file.name
        
        # 각 규칙에 대해 매칭 시도
        for pattern, replacement in rename_rules:
            match = re.match(pattern, old_name)
            if match:
                new_name = re.sub(pattern, replacement, old_name)
                new_path = json_file.parent / new_name
                
                # 이미 변경된 파일이 아닌 경우만 추가
                if new_name != old_name:
                    files_to_rename.append((str(json_file), str(new_path)))
                break
    
    return files_to_rename

def rename_files(files_to_rename: List[Tuple[str, str]], dry_run: bool = True) -> None:
    """
    파일명을 변경합니다.
    
    Args:
        files_to_rename: [(old_path, new_path), ...]
        dry_run: True면 실제로 변경하지 않고 미리보기만 표시
    """
    if not files_to_rename:
        print("✅ 변경할 파일이 없습니다.")
        return
    
    print(f"\n📋 총 {len(files_to_rename)}개의 파일을 변경합니다.\n")
    
    for old_path, new_path in files_to_rename:
        old_name = Path(old_path).name
        new_name = Path(new_path).name
        
        if dry_run:
            print(f"  [DRY RUN] {old_name} -> {new_name}")
        else:
            try:
                os.rename(old_path, new_path)
                print(f"  ✅ {old_name} -> {new_name}")
            except Exception as e:
                print(f"  ❌ {old_name} 변경 실패: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='워크로드 JSON 파일명 변경')
    parser.add_argument(
        '--workloads-dir',
        type=str,
        default='data/workloads_v17_1k',
        help='워크로드 디렉토리 경로 (기본값: data/workloads_v17_1k)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='실제로 파일명을 변경합니다 (기본값: dry-run 모드)'
    )
    
    args = parser.parse_args()
    
    # 절대 경로로 변환
    base_dir = os.path.abspath(args.workloads_dir)
    if not os.path.isabs(args.workloads_dir):
        # 상대 경로인 경우 스크립트 위치 기준으로 계산
        script_dir = Path(__file__).parent.parent
        base_dir = script_dir / args.workloads_dir
    
    print(f"🔍 워크로드 디렉토리 검색 중: {base_dir}")
    
    files_to_rename = find_workload_files(str(base_dir))
    
    if args.execute:
        print("\n⚠️  실제로 파일명을 변경합니다!")
        response = input("계속하시겠습니까? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ 취소되었습니다.")
            return
        rename_files(files_to_rename, dry_run=False)
        print("\n✅ 모든 파일명 변경이 완료되었습니다!")
    else:
        print("\n📝 [DRY RUN 모드] 실제로 변경하지 않고 미리보기만 표시합니다.")
        print("   실제로 변경하려면 --execute 플래그를 추가하세요.\n")
        rename_files(files_to_rename, dry_run=True)
        print("\n💡 실제로 변경하려면: python rename_workload_files.py --execute")

if __name__ == "__main__":
    main()




