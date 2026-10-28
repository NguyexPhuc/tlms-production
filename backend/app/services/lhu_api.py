import httpx
import logging
from datetime import datetime, date
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class LhuApiService:
    def __init__(self):
        self.base_url = settings.LHU_API_BASE_URL
        self.api_endpoint = "/calen/auth/XemLich_LichSinhVien"
        self.request_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

    async def fetch_student_schedule(self, student_id: str, query_date: date) -> List[Dict[str, Any]]:
        """
        Fetch schedule from LHU API (tapi.lhu.edu.vn).
        Sends form-encoded POST, paginates via PageIndex/PageSize.
        """
        date_str = query_date.strftime("%Y-%m-%d")

        all_events = []
        page_index = 1
        page_size = 30

        async with httpx.AsyncClient() as client:
            while True:
                payload = {
                    "StudentID": student_id,
                    "Ngay": date_str,
                    "PageIndex": page_index,
                    "PageSize": page_size,
                }

                try:
                    response = await client.post(
                        f"{self.base_url}{self.api_endpoint}",
                        data=payload,
                        headers=self.request_headers,
                        timeout=15.0
                    )

                    if response.status_code != 200:
                        # Try to surface LHU's own error message if available
                        lhu_message = ""
                        try:
                            lhu_message = response.json().get("Message", "")
                        except Exception:
                            pass
                        error_detail = lhu_message or f"HTTP {response.status_code}"
                        logger.error(f"LHU API Error: {response.status_code} - {response.text[:200]}")
                        raise Exception(f"LHU: {error_detail}")

                    response_text = response.text.strip()
                    if not response_text:
                        logger.warning(f"LHU API returned empty response for student {student_id} on {date_str}")
                        raise Exception("LHU portal trả về dữ liệu rỗng. Vui lòng thử lại sau.")

                    try:
                        data = response.json()
                    except Exception:
                        logger.error(f"LHU API returned invalid JSON for student {student_id}: {response_text[:200]}")
                        raise Exception("LHU portal trả về dữ liệu không hợp lệ. Vui lòng thử lại sau.")

                    if "data" not in data or not isinstance(data["data"], list):
                        logger.warning(f"Unexpected LHU API response structure: {str(data)[:200]}")
                        raise Exception("LHU portal trả về cấu trúc dữ liệu không đúng. Vui lòng liên hệ admin.")

                    # data[2] is the schedule list; fewer than 3 elements means no events
                    if len(data["data"]) <= 2:
                        break

                    events = data["data"][2]
                    if not events:
                        break

                    all_events.extend(events)

                    # Pagination: data[1][0].TotalRecord
                    total_records = 0
                    if len(data["data"]) > 1 and data["data"][1]:
                        total_records = data["data"][1][0].get("TotalRecord", 0)

                    if len(all_events) >= total_records:
                        break

                    page_index += 1

                except Exception as e:
                    logger.error(f"Failed to fetch LHU schedule page {page_index}: {str(e)}")
                    raise

        return all_events

    def parse_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse raw events into standardized format
        """
        parsed_schedule = []
        for event in events:
            # Logic "Báo Nghỉ": TinhTrang == 1 or 2
            tinh_trang = event.get("TinhTrang")
            is_cancelled = str(tinh_trang) in ["1", "2"]

            # Time parsing
            try:
                start = datetime.fromisoformat(event.get("ThoiGianBD", ""))
                end = datetime.fromisoformat(event.get("ThoiGianKT", ""))
            except ValueError:
                continue

            parsed_schedule.append({
                "subject_name": event.get("TenMonHoc"),
                "room": event.get("TenPhong"),
                "start_datetime": start,
                "end_datetime": end,
                "is_cancelled": is_cancelled,
                "description": f"Giao vien: {event.get('GiaoVien')}"
            })
            
        return parsed_schedule

lhu_api_service = LhuApiService()
