import { useState } from "react";
import { useCurrentUser } from "@/lib/useCurrentUser";

/**
 * 保存など書き込み操作の直前に呼ぶガード。ゲストの場合はAPI呼び出しをせずに
 * モーダル表示用のフラグを立てて true（ブロックした）を返す。
 * 呼び出し側は `if (guard()) return;` の形で使う。
 */
export function useGuestGuard() {
  const { isGuest } = useCurrentUser();
  const [blocked, setBlocked] = useState(false);

  function guard(): boolean {
    if (isGuest) {
      setBlocked(true);
      return true;
    }
    return false;
  }

  return { isGuest, blocked, setBlocked, guard };
}
