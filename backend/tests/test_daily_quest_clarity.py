from app.services.quest import DailyQuestService


def test_structured_quest_is_rendered_as_actionable_description():
    service = DailyQuestService()

    description = service._build_clear_description(
        {
            "objective": "Tạo một truy vấn lấy danh sách thành viên đang hoạt động.",
            "steps": [
                "Xác định bảng và các cột cần lấy.",
                "Viết câu SELECT có điều kiện trạng thái.",
                "Chạy thử và kiểm tra kết quả.",
            ],
            "evidence": "Nộp câu SQL và ảnh kết quả truy vấn.",
            "completion_criteria": "Câu SQL chạy được và chỉ trả thành viên đang hoạt động.",
        }
    )

    assert "Mục tiêu:" in description
    assert "1. Xác định bảng" in description
    assert "Minh chứng cần nộp:" in description
    assert "Tiêu chí hoàn thành:" in description


def test_legacy_quest_gets_clear_submission_guidance():
    service = DailyQuestService()

    description = service._build_clear_description(
        {"description": "Tóm tắt 3 ý chính đã học về kiểm thử phần mềm."}
    )

    assert description.startswith("Mục tiêu:")
    assert "Các bước thực hiện:" in description
    assert "Viết 2-3 câu" in description
