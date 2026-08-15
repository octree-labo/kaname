-- ============================================================
-- マイグレーション 0001: ユーザーに role / status を追加
-- 「アカウント申請」フローと「オーナー / 利用者」の権限分離に対応する。
-- schema.sql から新規構築する場合は不要（schema.sql 自体に反映済み）。
-- 既存DBに対しては、このファイルを1回だけ適用する。
-- ============================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
    CREATE TYPE user_role AS ENUM ('owner', 'member');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_status') THEN
    CREATE TYPE user_status AS ENUM ('pending', 'approved', 'rejected');
  END IF;
END $$;

ALTER TABLE users ADD COLUMN IF NOT EXISTS role   user_role   NOT NULL DEFAULT 'member';
ALTER TABLE users ADD COLUMN IF NOT EXISTS status user_status NOT NULL DEFAULT 'pending';

-- 既存の管理者アカウントをオーナー/承認済みへ移行
UPDATE users SET role = 'owner', status = 'approved' WHERE email = 'kasaubunts@gmail.com';
