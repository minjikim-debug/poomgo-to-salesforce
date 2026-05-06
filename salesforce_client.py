"""
Salesforce Service Cloud API 클라이언트
- simple-salesforce 라이브러리 사용
- 원주문정보(Original_Order__c) 객체에 upsert
- 외부 ID = 주문번호(쇼핑몰) → 중복 완전 차단
"""

import logging
from typing import Tuple

from simple_salesforce import Salesforce, SalesforceMalformedRequest

log = logging.getLogger(__name__)

# Salesforce Bulk API: 한 번에 처리할 최대 레코드 수
BULK_BATCH_SIZE = 200


class SalesforceClient:
    """Salesforce Service Cloud API 클라이언트"""

    def __init__(
        self,
        username: str,
        password: str,
        security_token: str,
        domain: str = "login",  # 운영환경: "login" | 샌드박스: "test"
    ):
        log.info(f"Salesforce 연결 중 (domain={domain})...")
        self.sf = Salesforce(
            username=username,
            password=password,
            security_token=security_token,
            domain=domain,
        )
        log.info("Salesforce 연결 성공!")

    def upsert_orders(
        self,
        records: list[dict],
        external_id_field: str,
        object_name: str,
    ) -> Tuple[int, int]:
        """
        주문 데이터를 Salesforce에 upsert합니다.
        
        - 외부 ID가 없으면 새로 생성(Insert)
        - 외부 ID가 이미 있으면 해당 레코드만 업데이트(Update) → 중복 차단
        
        Parameters
        ----------
        records          : 세일즈포스 필드명으로 변환된 레코드 리스트
        external_id_field: 중복 판단 기준 외부 ID 필드 API 이름
        object_name      : 세일즈포스 객체 API 이름 (예: Original_Order__c)
        
        Returns
        -------
        (성공 건수, 실패 건수)
        """
        if not records:
            return 0, 0

        sf_object = getattr(self.sf, object_name)
        success_count = 0
        error_count = 0

        # 배치 단위로 나눠서 처리 (Rate Limit 방지)
        for i in range(0, len(records), BULK_BATCH_SIZE):
            batch = records[i : i + BULK_BATCH_SIZE]
            log.info(
                f"[SF] upsert 배치 처리 중... "
                f"({i + 1}~{min(i + BULK_BATCH_SIZE, len(records))}/{len(records)}건)"
            )

            for record in batch:
                external_id_value = record.get(external_id_field)
                if not external_id_value:
                    log.warning(f"외부 ID 값 없음, 건너뜀: {record}")
                    error_count += 1
                    continue

                try:
                    result = sf_object.upsert(
                        record_or_dict=record,
                        ext_id_field=f"{external_id_field}/{external_id_value}",
                    )
                    # 201: 신규 생성 | 204: 업데이트
                    action = "신규" if result == 201 else "업데이트"
                    log.debug(f"[SF] {action} 완료: {external_id_value}")
                    success_count += 1

                except SalesforceMalformedRequest as e:
                    log.error(
                        f"[SF] upsert 실패 (주문번호: {external_id_value}): {e}"
                    )
                    error_count += 1

                except Exception as e:
                    log.error(
                        f"[SF] 예상치 못한 오류 (주문번호: {external_id_value}): {e}"
                    )
                    error_count += 1

        return success_count, error_count

    def get_existing_order_numbers(self, object_name: str, external_id_field: str) -> set:
        """
        세일즈포스에 이미 있는 주문번호 목록을 조회합니다.
        (수동으로 중복 체크가 필요할 때 사용, 보통은 upsert가 자동 처리)
        """
        query = f"SELECT {external_id_field} FROM {object_name} WHERE {external_id_field} != null"
        try:
            result = self.sf.query_all(query)
            return {
                record[external_id_field]
                for record in result.get("records", [])
            }
        except Exception as e:
            log.error(f"[SF] 기존 주문번호 조회 실패: {e}")
            return set()
