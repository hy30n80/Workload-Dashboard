#!/usr/bin/env python3
"""
EHRSQL 데이터베이스에 SQL 쿼리를 실행하는 간단한 스크립트
eicu 또는 mimic_iii 데이터베이스에 쿼리를 실행할 수 있습니다.
"""

import sqlite3
import sys
import os
from typing import List, Any, Optional
from sqlglot import parse_one, exp
import pdb as pdb


# tabulate가 있으면 사용, 없으면 기본 출력 사용
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

# EHRSQL 데이터베이스 경로 설정
DB_CONFIGS = {
    "eicu": "/data/yhyunjun/HybridSQL-Benchmark/EHRSQL/EHRSQL/dataset/ehrsql/eicu/eicu.sqlite",
    "mimic_iii": "/data/yhyunjun/HybridSQL-Benchmark/EHRSQL/EHRSQL/dataset/ehrsql/mimic_iii/mimic_iii.sqlite"
}

# "select distinct t1.c1 from ( select lab.labresult, percent_rank() over ( order by lab.labresult ) as c1 from lab where lab.labname = '-monos' and lab.patientunitstayid in ( select patient.patientunitstayid from patient where patient.age = ( select patient.age from patient where patient.uniquepid = '027-136480' and patient.hospitaldischargetime is null ) ) ) as t1 where t1.labresult = 13.0"
def parser(sql: str) -> str:
    tree = parse_one(sql, dialect="sqlite")
    

    tables = tree.find_all(exp.Table)
    for table in tables:
        print(table.name)

    print("--------------------------------")
    columns = tree.find_all(exp.Column)
    for column in columns:
        print(column.name)

    print("--------------------------------")
    selects = tree.find_all(exp.Select)
    for select in selects:
        print(select.expressions)

    print("--------------------------------")
    where_conditions = tree.find_all(exp.Where)
    for where_condition in where_conditions:
        print(where_condition.find_all(exp.EQ, exp.GT, exp.LT, exp.GTE, exp.LTE, exp.NEQ))

    pdb.set_trace()

    return tables, columns


def execute_query(db_name: str, sql_query: str, limit: Optional[int] = None) -> List[Any]:
    """
    EHRSQL 데이터베이스에 SQL 쿼리를 실행합니다.
    
    Args:
        db_name: 데이터베이스 이름 ('eicu' 또는 'mimic_iii')
        sql_query: 실행할 SQL 쿼리
        limit: 결과 개수 제한 (선택사항)
    
    Returns:
        쿼리 결과 (튜플 리스트)
    """
    if db_name not in DB_CONFIGS:
        raise ValueError(f"지원하지 않는 데이터베이스: {db_name}. 'eicu' 또는 'mimic_iii'를 사용하세요.")
    
    db_path = DB_CONFIGS[db_name]
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
    
    # SQLite 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    import pdb;
    pdb.set_trace()

    try:
        # 쿼리 실행
        cursor.execute(sql_query)
        
        # 컬럼 이름 가져오기
        column_names = [description[0] for description in cursor.description]
        
        # 결과 가져오기
        if limit:
            results = cursor.fetchmany(limit)
        else:
            results = cursor.fetchall()
        
        return column_names, results
    
    except sqlite3.Error as e:
        raise Exception(f"쿼리 실행 중 오류 발생: {e}")
    
    finally:
        conn.close()

def print_results(column_names: List[str], results: List[Any]):
    """쿼리 결과를 보기 좋게 출력합니다."""
    if not results:
        print("결과가 없습니다.")
        return
    
    # 테이블 형식으로 출력
    print(f"\n총 {len(results)}개의 행이 반환되었습니다.\n")
    
    if HAS_TABULATE:
        print(tabulate(results, headers=column_names, tablefmt="grid"))
    else:
        # 기본 출력 (tabulate 없이)
        # 컬럼 이름 출력
        col_widths = [max(len(str(col)), max(len(str(row[i])) for row in results) if results else 0) 
                     for i, col in enumerate(column_names)]
        
        # 헤더 출력
        header = " | ".join(str(col).ljust(col_widths[i]) for i, col in enumerate(column_names))
        print(header)
        print("-" * len(header))
        
        # 데이터 출력
        for row in results:
            row_str = " | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row))
            print(row_str)


def main():
    """메인 함수: 명령줄 인자 또는 인터랙티브 모드로 쿼리 실행"""
    
    # 명령줄 모드: python ehrsql_db_execution.py <db_name> "<sql_query>" [limit]
    # 또는: python ehrsql_db_execution.py <db_name> sql query parts... [limit]
    db_name = sys.argv[1]
    
    # SQL 쿼리 구성: sys.argv[2]부터 시작
    # 마지막 인자가 숫자면 limit, 그렇지 않으면 SQL 쿼리의 일부
    parts = sys.argv[2:]
    limit = None
    sql_parts = []
    
    # 마지막 인자가 숫자인지 확인
    if len(parts) > 0:
        try:
            # 마지막 인자가 숫자면 limit으로 사용
            limit = int(parts[-1])
            sql_parts = parts[:-1]
        except ValueError:
            # 마지막 인자가 숫자가 아니면 모든 부분이 SQL 쿼리
            sql_parts = parts
    
    # SQL 쿼리 조합
    sql_query = " ".join(sql_parts)

    sql_query = "select distinct t1.c1 from ( select lab.labresult, percent_rank() over ( order by lab.labresult ) as c1 from lab where lab.labname = '-monos' and lab.patientunitstayid in ( select patient.patientunitstayid from patient where patient.age = ( select patient.age from patient where patient.uniquepid = '027-136480' and patient.hospitaldischargetime is null ) ) ) as t1 where t1.labresult = 13.0"
    # sql_query = """
    # SELECT DISTINCT
    #     lab.labresult AS m2_0,
    #     lab.labname   AS m2_1,
    #     patient.uniquepid AS m2_2
    # FROM lab
    # JOIN patient ON lab.patientunitstayid = patient.patientunitstayid
    # WHERE lab.labresult IS NOT NULL
    # AND lab.labname IS NOT NULL
    # AND patient.uniquepid IS NOT NULL;
    # """

    if not sql_query:
        print("오류: SQL 쿼리를 입력해주세요.", file=sys.stderr)
        print("사용법: python ehrsql_db_execution.py <db_name> <sql_query> [limit]", file=sys.stderr)
        sys.exit(1)
    
    try:
        parser(sql_query)
        column_names, results = execute_query(db_name, sql_query, limit)
        print_results(column_names, results)
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
