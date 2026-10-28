'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function GuidePage() {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const isMentorOrAdmin = user.roles?.includes('mentor') || user.roles?.includes('admin');

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto bg-white shadow rounded-lg p-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">
            HƯỚNG DẪN SỬ DỤNG HỆ THỐNG TLMS
          </h1>
          <button
            onClick={() => router.back()}
            className="text-gray-500 hover:text-gray-700 font-medium"
          >
            Quay lại
          </button>
        </div>
        
        <p className="text-gray-500 italic mb-8 border-b pb-4">
          {isMentorOrAdmin ? 'Dành cho Mentor' : 'Dành cho Thành viên'}
        </p>

        {isMentorOrAdmin ? <MentorGuide /> : <MemberGuide />}
      </div>
    </div>
  );
}

function MentorGuide() {
  return (
    <div className="space-y-8 text-gray-800">
      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-3 border-l-4 border-[#1E90FF] pl-3">1. Tổng quan Dashboard</h2>
        <p className="mb-2">Sau khi đăng nhập, truy cập menu Mentor để xem:</p>
        <ul className="list-disc pl-5 space-y-1 text-gray-700">
          <li><strong>Pending Reviews:</strong> Danh sách task chờ duyệt</li>
          <li><strong>Thống kê:</strong> Số lượng task đã xử lý và đang chờ</li>
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-3 border-l-4 border-[#1E90FF] pl-3">2. Quy trình Review Task</h2>
        <h3 className="font-semibold text-lg mb-2">Các bước thực hiện</h3>
        <ol className="list-decimal pl-5 space-y-1 text-gray-700 mb-4">
          <li>Tại Mentor Dashboard, chọn task từ danh sách <strong>Pending Reviews</strong></li>
          <li>Click vào <strong>Proof Link</strong> để xem kết quả của Mentee</li>
          <li>Đọc ghi chú và đánh giá chất lượng công việc</li>
          <li>Ra quyết định: <strong>Approve</strong> hoặc <strong>Reject</strong></li>
        </ol>

        <h3 className="font-semibold text-lg mb-2">Quyết định</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 border">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Hành động</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Chi tiết</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              <tr>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-green-600">✅ Approve</td>
                <td className="px-6 py-4">
                  Chọn Approve, có thể thêm lời khen.<br/>
                  <span className="text-gray-500 text-sm">→ Mentee nhận XP, task đóng</span>
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-red-600">❌ Reject</td>
                <td className="px-6 py-4">
                  Chọn Reject, <strong>BẮT BUỘC</strong> nhập lý do vào Comment.<br/>
                  <span className="text-sm italic text-gray-500">Ví dụ: "Code chưa format", "Thiếu chức năng X"</span><br/>
                  <span className="text-gray-500 text-sm">→ Task quay lại In Progress để làm lại</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-3 border-l-4 border-[#1E90FF] pl-3">3. Tạo Nhiệm vụ Mới</h2>
        <h3 className="font-semibold text-lg mb-2">Quy trình tạo Task</h3>
        <ol className="list-decimal pl-5 space-y-1 text-gray-700 mb-4" start={5}>
          <li>Nhấn nút <strong>+ Create Task</strong> tại Mentor Dashboard</li>
          <li>Điền tiêu đề và mô tả rõ ràng, ngắn gọn</li>
          <li>Chọn loại task, phạm vi, độ khó và phần thưởng</li>
          <li>Nhập kỹ năng (Tags) và hướng dẫn chi tiết</li>
        </ol>

        <h3 className="font-semibold text-lg mb-2">Các tùy chọn</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-bold mb-2">Loại (Type)</h4>
            <ul className="list-disc pl-4 text-sm space-y-1">
              <li><strong>Core:</strong> Task bắt buộc (Onboarding, Quy trình)</li>
              <li><strong>Bounty:</strong> Task thử thách/Dự án</li>
            </ul>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-bold mb-2">Phạm vi (Scope)</h4>
            <ul className="list-disc pl-4 text-sm space-y-1">
              <li><strong>Mandatory:</strong> Giao cho toàn bộ thành viên phù hợp</li>
              <li><strong>Opt-in:</strong> Thành viên tự đăng ký (có giới hạn)</li>
              <li><strong>Private:</strong> Chỉ định đích danh cho thành viên cụ thể</li>
            </ul>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-bold mb-2">Độ khó & Phần thưởng</h4>
            <ul className="list-disc pl-4 text-sm space-y-1">
              <li>Chọn: <strong>Easy / Medium / Hard</strong></li>
              <li>Nhập XP Reward (ví dụ: 100 XP)</li>
            </ul>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-3 border-l-4 border-[#1E90FF] pl-3">4. Quản lý & Theo dõi Mentee</h2>
        <h3 className="font-semibold text-lg mb-2">Xem Profile</h3>
        <ul className="list-disc pl-5 space-y-1 text-gray-700 mb-4">
            <li>Click vào tên Member để xem Profile</li>
            <li>Theo dõi tiến độ Core Task, Level và XP</li>
            <li>Xem danh sách Minh chứng đã upload</li>
        </ul>

        <h3 className="font-semibold text-lg mb-2">Xác thực Minh chứng</h3>
        <ol className="list-decimal pl-5 space-y-1 text-gray-700" start={9}>
            <li>Truy cập Profile hoặc trang quản lý Evidence</li>
            <li>Xem các mục có trạng thái <strong>Pending</strong></li>
            <li>Kiểm tra link minh chứng</li>
            <li>Nhấn <strong>Verify</strong> để xác thực hoặc <strong>Reject</strong> nếu không hợp lệ</li>
        </ol>
      </section>
    </div>
  );
}

function MemberGuide() {
  return (
    <div className="space-y-8 text-gray-800">
      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-3 border-l-4 border-green-500 pl-3">1. Đăng nhập hệ thống</h2>
        <p>Truy cập Web Portal của Lab và nhấn nút <strong>Login</strong> (hoặc Login with S4H). Hệ thống sẽ tự động xác thực và chuyển bạn vào Dashboard.</p>
      </section>

      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-3 border-l-4 border-green-500 pl-3">2. Quản lý Lịch làm việc</h2>
        <h3 className="font-semibold text-lg mb-2">Đăng ký lịch</h3>
        <ul className="list-disc pl-5 space-y-1 text-gray-700 mb-4">
          <li>Chọn <strong>Lịch trình (Schedule)</strong> trên menu bên trái (hoặc dashboard)</li>
          <li>Bấm vào các ô trống (Sáng/Chiều/Tối) để đăng ký làm việc</li>
          <li>Sử dụng nút <strong>Sync Schedule</strong> để đồng bộ lịch học (nếu đã cập nhật Student ID)</li>
        </ul>

        <h3 className="font-semibold text-lg mb-2">Theo dõi điểm chuyên cần</h3>
        <p className="mb-2">Tại trang Schedule, bạn sẽ thấy bảng thống kê giờ làm việc và điểm kỷ luật. Trạng thái hiển thị theo màu:</p>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 border">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trạng thái</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ý nghĩa</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              <tr>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-green-600">🟢 Present</td>
                <td className="px-6 py-4">Đi đúng lịch</td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-red-600">🔴 Absent</td>
                <td className="px-6 py-4">Vắng mặt (không check-in)</td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-yellow-600">🟡 Late</td>
                <td className="px-6 py-4">Đi muộn</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-3 border-l-4 border-green-500 pl-3">3. Thực hiện Nhiệm vụ</h2>
        <h3 className="font-semibold text-lg mb-2">Nhận Task</h3>
        <ul className="list-disc pl-5 space-y-1 text-gray-700 mb-4">
          <li>Chọn menu <strong>Nhiệm vụ (Tasks)</strong> để xem danh sách</li>
          <li><strong>Core Tasks:</strong> Nhiệm vụ bắt buộc (ưu tiên làm trước)</li>
          <li><strong>Bounty Tasks:</strong> Nhiệm vụ thử thách kiếm XP</li>
        </ul>

        <h3 className="font-semibold text-lg mb-2">Nộp bài</h3>
        <ul className="list-disc pl-5 space-y-1 text-gray-700 mb-4">
          <li>Nhấn nút <strong>Submit</strong> khi hoàn thành</li>
          <li>Điền link minh chứng (Github, Google Drive, Docs...)</li>
          <li>Thêm ghi chú mô tả công việc đã làm</li>
          <li>Chờ Mentor duyệt (trạng thái: <strong>Submitted</strong>)</li>
        </ul>
        
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
            <h4 className="font-bold mb-2">Kết quả Review:</h4>
            <ul className="list-disc pl-4 text-sm space-y-1">
                <li>✅ <strong>Approve:</strong> Nhận XP, task hoàn thành</li>
                <li>❌ <strong>Reject:</strong> Xem comment của Mentor, sửa và nộp lại</li>
            </ul>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-3 border-l-4 border-green-500 pl-3">4. Quản lý Hồ sơ</h2>
        <ul className="list-disc pl-5 space-y-1 text-gray-700">
          <li>Truy cập menu <strong>Hồ sơ (Profile)</strong> để xem Level, XP và tiến độ thăng cấp</li>
          <li>Thêm Minh chứng: Chứng chỉ, Seminar, Blog ngoài hệ thống</li>
          <li>Nhập tiêu đề, link, mô tả và tags kỹ năng</li>
          <li>Trạng thái <strong>Pending</strong> - chờ Mentor xác nhận</li>
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-3 border-l-4 border-green-500 pl-3">5. Bảng xếp hạng</h2>
        <p>Truy cập menu Leaderboard để xem thứ hạng của bạn so với các thành viên khác dựa trên tổng XP kiếm được.</p>
      </section>
    </div>
  );
}
