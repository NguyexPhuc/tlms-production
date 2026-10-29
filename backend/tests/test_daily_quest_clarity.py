from types import SimpleNamespace

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


def test_vague_ai_quest_is_rejected():
    service = DailyQuestService()

    items = service._normalize_items(
        [
            {
                "format": "short_answer",
                "topic": "test",
                "title": "Ôn lại test",
                "objective": "Hãy ôn lại test và trình bày những gì bạn đã học để củng cố kỹ năng hôm nay.",
                "steps": ["Đọc lại bài.", "Tóm tắt bài.", "Nộp câu trả lời."],
                "evidence": "Nộp phần tóm tắt.",
                "completion_criteria": "Trả lời đầy đủ.",
                "difficulty": "easy",
                "xp_reward": 10,
            }
        ],
        user_level=1,
    )

    assert items == []


def test_multiple_choice_accepts_parenthesized_options():
    service = DailyQuestService()
    item = {
        "format": "multiple_choice",
        "topic": "backend concurrency",
        "title": "Backend: chọn cách chống đặt trùng ghế",
        "objective": (
            "Hai request API cùng đặt ghế A10 trong một suất chiếu. Backend nên dùng cách nào?\n"
            "A) Chỉ kiểm tra trên frontend.\n"
            "B) Dùng transaction và UNIQUE constraint.\n"
            "C) Chờ 500 ms trước khi INSERT.\n"
            "D) Ghi cả hai booking rồi sửa thủ công."
        ),
        "steps": ["Chọn một đáp án.", "Giải thích lựa chọn.", "Nêu một rủi ro."],
        "evidence": "Nộp đáp án A-D và giải thích ngắn về database.",
        "completion_criteria": "Chọn giải pháp ngăn được race condition và giải thích hợp lý.",
        "difficulty": "medium",
        "xp_reward": 20,
    }

    normalized = service._normalize_items([item], user_level=3)

    assert len(normalized) == 1
    assert normalized[0]["format"] == "multiple_choice"


def test_beginner_fallback_contains_five_concrete_question_formats():
    service = DailyQuestService()
    user = SimpleNamespace(level=2)

    items = service._fallback_items(user, {}, 5)

    assert len(items) == 5
    assert len({item["title"] for item in items}) == 5
    assert [item["format"] for item in items] == [
        "scenario",
        "scenario",
        "multiple_choice",
        "coding",
        "short_answer",
    ]
    assert "hai người đặt cùng ghế" in items[0]["title"].lower()
    assert all(f"{option}." in items[2]["description"] for option in "ABCD")
    assert "Input:" in items[3]["description"]
    assert "Output:" in items[3]["description"]
    assert "Ví dụ:" in items[3]["description"]


def test_fallback_difficulty_changes_with_member_level():
    service = DailyQuestService()

    intermediate = service._fallback_items(SimpleNamespace(level=5), {}, 5)
    advanced = service._fallback_items(SimpleNamespace(level=8), {}, 5)

    assert intermediate[0]["title"] == "Backend: xử lý webhook thanh toán gửi lặp"
    assert advanced[0]["title"] == "Backend: giữ một ghế trên ba API instance"
    assert intermediate[3]["title"].startswith("Code:")
    assert advanced[3]["title"] == "Code: cài đặt LRU Cache O(1)"
