-- Миграция для добавления полей password_hash и is_ldap_user в таблицу users
-- Выполните этот скрипт, если у вас уже есть база данных

-- Добавляем поле password_hash если его нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'password_hash'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);
        RAISE NOTICE 'Добавлено поле password_hash';
    ELSE
        RAISE NOTICE 'Поле password_hash уже существует';
    END IF;
END $$;

-- Добавляем поле is_ldap_user если его нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'is_ldap_user'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE users ADD COLUMN is_ldap_user BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Добавлено поле is_ldap_user';
    ELSE
        RAISE NOTICE 'Поле is_ldap_user уже существует';
    END IF;
END $$;

-- Обновляем существующих пользователей admin как локальных
UPDATE users 
SET is_ldap_user = FALSE 
WHERE username = 'admin' AND is_ldap_user IS NULL;

-- Проверяем результат
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'users' 
AND table_schema = 'public'
ORDER BY ordinal_position;
