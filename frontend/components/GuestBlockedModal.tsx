export function GuestBlockedModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-semibold text-slate-900">保存できません</h2>
        <p className="mt-2 text-sm text-slate-600">
          ゲストモードのため保存できません。閲覧のみご利用いただけます。
        </p>
        <button
          onClick={onClose}
          className="mt-5 w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          閉じる
        </button>
      </div>
    </div>
  );
}
